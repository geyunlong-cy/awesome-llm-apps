import json
import logging
import time
from threading import Lock, Thread
from typing import Any

import lark_oapi as lark

from .lark_client import LarkClient
from .openai_service import OpenAIService
from .settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lark_openai_bot.ws")

settings = get_settings()
lark_api = LarkClient(settings)
openai_service = OpenAIService(settings)

_seen_events: dict[str, float] = {}
_seen_events_lock = Lock()
EVENT_TTL_SECONDS = 600


def _is_duplicate(event_id: str) -> bool:
    if not event_id:
        return False

    now = time.time()
    with _seen_events_lock:
        expired = [
            key
            for key, timestamp in _seen_events.items()
            if now - timestamp > EVENT_TTL_SECONDS
        ]
        for key in expired:
            _seen_events.pop(key, None)

        if event_id in _seen_events:
            return True

        _seen_events[event_id] = now
        return False


def _as_dict(data: Any) -> dict:
    raw = lark.JSON.marshal(data)
    payload = json.loads(raw)
    return payload if isinstance(payload, dict) else {}


def _raw_text(message: dict) -> str:
    try:
        content = json.loads(message.get("content", "{}"))
    except (TypeError, json.JSONDecodeError):
        return ""
    return str(content.get("text", "")).strip()


def _clean_text(message: dict) -> str:
    text = _raw_text(message)

    for mention in message.get("mentions") or []:
        key = mention.get("key")
        if key:
            text = text.replace(key, "")

    text = text.strip()
    if text.lower().startswith("/ai"):
        text = text[3:].strip()
    return text


def _process_message(message_id: str, session_key: str, text: str) -> None:
    try:
        if text.lower() in {"/reset", "重置对话", "清空对话"}:
            openai_service.reset(session_key)
            lark_api.reply_text(message_id, "对话上下文已重置。")
            return

        answer = openai_service.reply(session_key, text)
        lark_api.reply_text(message_id, answer)
    except Exception:
        logger.exception("Failed to process Lark message %s", message_id)
        try:
            lark_api.reply_text(
                message_id,
                "处理消息时出现错误。请检查终端日志、Lark权限和OpenAI API配置。",
            )
        except Exception:
            logger.exception("Failed to send error message to Lark")


def _handle_message(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
    payload = _as_dict(data)
    header = payload.get("header", {})
    event_id = str(header.get("event_id", ""))

    if _is_duplicate(event_id):
        return

    event = payload.get("event", {})
    sender = event.get("sender", {})
    if sender.get("sender_type") != "user":
        return

    sender_open_id = str(sender.get("sender_id", {}).get("open_id", ""))
    if settings.allowed_sender_ids and sender_open_id not in settings.allowed_sender_ids:
        return

    message = event.get("message", {})
    if message.get("message_type") != "text":
        return

    raw_text = _raw_text(message)
    has_mentions = bool(message.get("mentions"))
    is_command = raw_text.lower().startswith("/ai")
    if (
        message.get("chat_type") == "group"
        and settings.require_mention_in_group
        and not has_mentions
        and not is_command
    ):
        return

    text = _clean_text(message)
    if not text:
        return

    message_id = str(message.get("message_id", ""))
    chat_id = str(message.get("chat_id", ""))
    if not message_id or not chat_id:
        return

    session_key = f"{chat_id}:{sender_open_id}"
    Thread(
        target=_process_message,
        args=(message_id, session_key, text),
        daemon=True,
    ).start()


event_handler = (
    lark.EventDispatcherHandler.builder(
        settings.lark_encrypt_key,
        settings.lark_verification_token,
    )
    .register_p2_im_message_receive_v1(_handle_message)
    .build()
)


def main() -> None:
    logger.info("Starting %s with Lark WebSocket long connection", settings.bot_name)
    client = lark.ws.Client(
        settings.lark_app_id,
        settings.lark_app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
        domain=lark.LARK_DOMAIN,
    )
    client.start()


if __name__ == "__main__":
    main()
