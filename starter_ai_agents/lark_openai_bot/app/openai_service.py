from threading import Lock

from openai import OpenAI

from .settings import Settings


SYSTEM_INSTRUCTIONS = """
You are Leo AI, a practical business assistant working inside Lark.

Rules:
- Reply in the user's language unless they explicitly request translation.
- Support Chinese, English, and Indonesian naturally.
- Be concise, accurate, and action-oriented.
- For business requests, prefer checklists, decisions, and next actions.
- Never claim that an external action was completed unless a connected tool actually completed it.
- When information is missing, make a reasonable assumption and label it clearly.
""".strip()


class OpenAIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key)
        self._previous_response_ids: dict[str, str] = {}
        self._session_lock = Lock()

    def reply(self, session_key: str, user_text: str) -> str:
        with self._session_lock:
            previous_response_id = self._previous_response_ids.get(session_key)

        request: dict = {
            "model": self.settings.openai_model,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": user_text,
            "store": True,
            "reasoning": {"effort": "low"},
            "max_output_tokens": self.settings.max_output_tokens,
        }
        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = self.client.responses.create(**request)
        text = (response.output_text or "").strip()
        if not text:
            text = "抱歉，我暂时没有生成有效回复，请再发送一次。"

        with self._session_lock:
            self._previous_response_ids[session_key] = response.id

        return text

    def reset(self, session_key: str) -> None:
        with self._session_lock:
            self._previous_response_ids.pop(session_key, None)
