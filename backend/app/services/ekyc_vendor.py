"""eKYC ベンダー API のクライアント。

外部 API を呼ぶときの基本形:
  - タイムアウトを必ず指定する
  - 一時的な失敗（通信エラー、5xx、429）だけリトライする
  - 4xx（こちらの誤り）はリトライしない
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class VendorError(Exception):
    pass


@dataclass(frozen=True)
class VendorSession:
    session_id: str
    verify_url: str


class EkycVendorClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 5.0,
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.transport = transport

    async def create_session(self, reference_id: str, callback_url: str, return_url: str) -> VendorSession:
        body = {"reference_id": reference_id, "callback_url": callback_url, "return_url": return_url}
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    res = await client.post(f"{self.base_url}/v1/sessions", json=body, headers=headers)
                except httpx.TransportError as e:
                    logger.warning("vendor request failed attempt=%d error=%s", attempt, type(e).__name__)
                else:
                    if res.status_code < 400:
                        data = res.json()
                        return VendorSession(session_id=data["session_id"], verify_url=data["verify_url"])
                    if res.status_code not in RETRYABLE_STATUS:
                        raise VendorError(f"vendor returned {res.status_code}")
                    logger.warning("vendor returned %d attempt=%d", res.status_code, attempt)

                if attempt < self.max_attempts:
                    await asyncio.sleep(self.backoff_seconds * 2 ** (attempt - 1))

        raise VendorError("vendor unavailable after retries")
