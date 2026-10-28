"""kintone REST API の小さなクライアント（レコード一括操作だけ）。

押さえどころ:
  - 一括登録・更新は100件ずつ、取得は500件ずつに分割する
  - 一時的な失敗（通信エラー、429、5xx）は待ってからリトライする
  - 認証は APIトークン（X-Cybozu-API-Token ヘッダー）
"""

import logging
import time
from collections.abc import Iterator, Sequence
from typing import TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")
MAX_WRITE = 100
MAX_READ = 500
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class KintoneError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(f"{status_code} {code}: {message}")
        self.status_code = status_code
        self.code = code


def chunked(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


class KintoneClient:
    def __init__(
        self,
        base_url: str,
        app_id: int,
        api_token: str,
        timeout: float = 10.0,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
        http: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.app_id = app_id
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.http = http or httpx.Client(timeout=timeout)
        self.headers = {"X-Cybozu-API-Token": api_token}

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}/k/v1/{path}"
        for attempt in range(1, self.max_attempts + 1):
            try:
                res = self.http.request(method, url, headers=self.headers, **kwargs)
            except httpx.TransportError as e:
                logger.warning("kintone %s %s failed attempt=%d error=%s", method, path, attempt, type(e).__name__)
            else:
                if res.status_code < 400:
                    return res.json()
                body = _safe_json(res)
                if res.status_code not in RETRYABLE_STATUS:
                    raise KintoneError(res.status_code, body.get("code", ""), body.get("message", ""))
                logger.warning("kintone %s %s returned %d attempt=%d", method, path, res.status_code, attempt)

            if attempt < self.max_attempts:
                time.sleep(self.backoff_seconds * 2 ** (attempt - 1))
        raise KintoneError(503, "RETRY_EXHAUSTED", f"{method} {path} failed after {self.max_attempts} attempts")

    def find_ids_by_application(self, application_ids: Sequence[str]) -> dict[str, str]:
        """申込ID -> kintone のレコードID。前回の途中失敗で登録済みのものを見つけるのに使う。"""
        found: dict[str, str] = {}
        for chunk in chunked(application_ids, MAX_WRITE):  # クエリ文字列が長くなりすぎないよう100件ずつ
            values = ", ".join(f'"{a}"' for a in chunk)
            data = self._request(
                "GET",
                "records.json",
                params={"app": self.app_id, "query": f"申込ID in ({values}) limit {MAX_READ}"},
            )
            for record in data["records"]:
                found[record["申込ID"]["value"]] = record["$id"]["value"]
        return found

    def add_records(self, records: Sequence[dict]) -> list[str]:
        ids: list[str] = []
        for chunk in chunked(records, MAX_WRITE):
            data = self._request("POST", "records.json", json={"app": self.app_id, "records": list(chunk)})
            ids.extend(data["ids"])
        return ids

    def update_records(self, updates: Sequence[tuple[str, dict]]) -> None:
        for chunk in chunked(updates, MAX_WRITE):
            self._request(
                "PUT",
                "records.json",
                json={"app": self.app_id, "records": [{"id": rid, "record": rec} for rid, rec in chunk]},
            )


def _safe_json(res: httpx.Response) -> dict:
    try:
        return res.json()
    except ValueError:
        return {}
