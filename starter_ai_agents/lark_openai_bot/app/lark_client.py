import json
import time
from threading import Lock

import httpx

from .settings import Settings


class LarkAPIError(RuntimeError):
    pass


class LarkClient:
    BASE_URL = "https://open.larksuite.com/open-apis"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._token_lock = Lock()

    def _get_tenant_access_token(self) -> str:
        now = time.time()
        if self._access_token and now < self._expires_at:
            return self._access_token

        with self._token_lock:
            now = time.time()
            if self._access_token and now < self._expires_at:
                return self._access_token

            response = httpx.post(
                f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.settings.lark_app_id,
                    "app_secret": self.settings.lark_app_secret,
                },
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code", 0) != 0:
                raise LarkAPIError(
                    f"Failed to get tenant access token: {payload.get('msg', payload)}"
                )

            token = payload.get("tenant_access_token")
            if not token:
                raise LarkAPIError("Lark did not return tenant_access_token")

            expire_seconds = int(payload.get("expire", 7200))
            self._access_token = token
            self._expires_at = now + max(expire_seconds - 120, 60)
            return token

    def reply_text(self, message_id: str, text: str) -> None:
        token = self._get_tenant_access_token()
        response = httpx.post(
            f"{self.BASE_URL}/im/v1/messages/{message_id}/reply",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            json={
                "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code", 0) != 0:
            raise LarkAPIError(
                f"Failed to reply to Lark message: {payload.get('msg', payload)}"
            )
