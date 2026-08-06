import json
import logging
import time
from threading import Lock

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from .lark_client import LarkClient
from .openai_service import OpenAIService
from .settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lark_openai_bot")

settings = get_settings()
lark = LarkClient(settings)
openai_service = OpenAIService(settings)
app = FastAPI(title="Lark OpenAI Bot", version="0.1.0")

_seen_events: dict[str, float] = {}
_seen_events_lock = Lock()
EVENT_TTL_SECONDS = 600


def _is_duplicate(event_id: str) -> bool:
    if not event_id:
        return False

    now = time.time()
    with _seen_events_lock:
        expired = [
            key for key, timestamp in _seen_events.items()
            if now - timestamp > EVENT_TTL_SECONDS
        ]
        for key in expired:
            _seen_events.pop(key, None)

        if event_id in _seen_events:
            return True

        _seen_events[event_id] = now
        return False


def _verify_token(payload: dict) -> None:
    received_token = payload.get("token") or payload.get("header", {}).get("token")
    if received_token != settings.lark_verification_token:
        raise HTTPException(status_code=403, detail="Invalid Lark verification token")


def _extract_text(message: dict) -> str:
    try:
        content = json.loads(message.get("content", "{}"))
    except json.JSONDecodeError:
        return ""

    text = str(content.get("text", ""))
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
            lark.reply_text(message_id, "对话上下文已重置。")
            return

        answer = openai_service.reply(session_key, text)
        lark.reply_text(message_id, answer)
    except Exception:
        logger.exception("Failed to process Lark message %s", message_id)
        try:
            lark.reply_text(
                message_id,
                "处理消息时出现错误。请检查服务日志、Lark权限和OpenAI API配置。",
            )
        except Exception:
            logger.exception("Failed to send error message to Lark")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "bot": settings.bot_name}


@app.post("/lark/events")
async def lark_events(request: Request, background_tasks: BackgroundTasks) -> dict:
    payload = await request.json()
    _verify_token(payload)

    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}

    header = payload.get("header", {})
    if header.get("event_type") != "im.message.receive_v1":
        return {"code": 0}

    event_id = header.get("event_id", "")
    if _is_duplicate(event_id):
        return {"code": 0}

    event = payload.get("event", {})
    sender = event.get("sender", {})
    if sender.get("sender_type") != "user":
        return {"code": 0}

    sender_open_id = sender.get("sender_id", {}).get("open_id", "")
    if settings.allowed_sender_ids and sender_open_id not in settings.allowed_sender_ids:
        return {"code": 0}

    message = event.get("message", {})
    if message.get("message_type") != "text":
        return {"code": 0}

    chat_type = message.get("chat_type", "")
    text_starts_with_command = _extract_text(message).lower().startswith("/ai")
    has_mentions = bool(message.get("mentions"))
    if (
        chat_type == "group"
        and settings.require_mention_in_group
        and not has_mentions
        and not text_starts_with_command
    ):
        return {"code": 0}

    text = _extract_text(message)
    if not text:
        return {"code": 0}

    message_id = message.get("message_id", "")
    chat_id = message.get("chat_id", "")
    if not message_id or not chat_id:
        return {"code": 0}

    session_key = f"{chat_id}:{sender_open_id}"
    background_tasks.add_task(_process_message, message_id, session_key, text)
    return {"code": 0}
