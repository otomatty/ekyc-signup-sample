"""モックの kintone REST API（レコード一括操作だけ）。

本物の kintone の形式（{"フィールドコード": {"value": ...}}）と主な制限をまねている。
  - APIトークンは X-Cybozu-API-Token ヘッダー
  - 一括登録・更新は1回100件まで、取得は1回500件まで
  - 「申込ID」フィールドは重複禁止（kintone の「値の重複を禁止する」設定に相当）
エラーコードはこのモック独自のもので、本物の kintone のコードとは異なる。

  GET  /mock-kintone/k/v1/records.json   レコード取得（query は「申込ID in (...)」と limit だけ対応）
  POST /mock-kintone/k/v1/records.json   一括登録
  PUT  /mock-kintone/k/v1/records.json   一括更新
  GET  /mock-kintone/debug/records       登録内容の確認用（モック独自）
"""

import re
from dataclasses import dataclass, field

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/mock-kintone", tags=["mock-kintone"])

MAX_WRITE = 100
MAX_READ = 500
UNIQUE_FIELD = "申込ID"


@dataclass
class MockKintoneStore:
    records: dict[str, dict] = field(default_factory=dict)  # レコードID -> レコード
    next_id: int = 1
    fail_remaining: int = 0  # 書き込みを何回 503 で失敗させるか（リトライ確認用）


def _store(request: Request) -> MockKintoneStore:
    return request.app.state.mock_kintone


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status_code)


def _check(request: Request, token: str | None, app_id: object) -> JSONResponse | None:
    settings = request.app.state.settings
    if token != settings.kintone_api_token:
        return _error(401, "MOCK_UNAUTHORIZED", "APIトークンが不正です")
    if str(app_id) != str(settings.kintone_app_id):
        return _error(400, "MOCK_BAD_APP", "アプリIDが不正です")
    return None


def _maybe_fail(store: MockKintoneStore) -> JSONResponse | None:
    if store.fail_remaining > 0:
        store.fail_remaining -= 1
        return _error(503, "MOCK_UNAVAILABLE", "一時的に利用できません")
    return None


@router.get("/k/v1/records.json")
def get_records(
    request: Request,
    app: int,
    query: str = "",
    x_cybozu_api_token: str | None = Header(default=None),
):
    if err := _check(request, x_cybozu_api_token, app):
        return err
    limit_match = re.search(r"limit\s+(\d+)", query)
    limit = int(limit_match.group(1)) if limit_match else 100
    if limit > MAX_READ:
        return _error(400, "MOCK_LIMIT", f"一度に取得できるレコードは{MAX_READ}件までです")

    ids: set[str] | None = None
    in_match = re.search(rf"{UNIQUE_FIELD}\s+in\s+\(([^)]*)\)", query)
    if in_match:
        ids = set(re.findall(r'"([^"]*)"', in_match.group(1)))

    records = [
        r for r in _store(request).records.values() if ids is None or r[UNIQUE_FIELD]["value"] in ids
    ][:limit]
    return {"records": records, "totalCount": None}


@router.post("/k/v1/records.json")
async def add_records(request: Request, x_cybozu_api_token: str | None = Header(default=None)):
    body = await request.json()
    if err := _check(request, x_cybozu_api_token, body.get("app")):
        return err
    records: list[dict] = body.get("records", [])
    if len(records) > MAX_WRITE:
        return _error(400, "MOCK_LIMIT", f"一度に登録できるレコードは{MAX_WRITE}件までです")
    store = _store(request)
    if err := _maybe_fail(store):
        return err

    existing = {r[UNIQUE_FIELD]["value"] for r in store.records.values()}
    incoming = [r.get(UNIQUE_FIELD, {}).get("value") for r in records]
    if any(v in existing for v in incoming) or len(set(incoming)) != len(incoming):
        return _error(400, "MOCK_DUPLICATE", f"「{UNIQUE_FIELD}」の値が重複しています")

    ids, revisions = [], []
    for record in records:
        record_id = str(store.next_id)
        store.next_id += 1
        store.records[record_id] = {
            **record,
            "$id": {"type": "__ID__", "value": record_id},
            "$revision": {"type": "__REVISION__", "value": "1"},
        }
        ids.append(record_id)
        revisions.append("1")
    return {"ids": ids, "revisions": revisions}


@router.put("/k/v1/records.json")
async def update_records(request: Request, x_cybozu_api_token: str | None = Header(default=None)):
    body = await request.json()
    if err := _check(request, x_cybozu_api_token, body.get("app")):
        return err
    updates: list[dict] = body.get("records", [])
    if len(updates) > MAX_WRITE:
        return _error(400, "MOCK_LIMIT", f"一度に更新できるレコードは{MAX_WRITE}件までです")
    store = _store(request)
    if err := _maybe_fail(store):
        return err
    if missing := [u["id"] for u in updates if str(u.get("id")) not in store.records]:
        return _error(404, "MOCK_NOT_FOUND", f"レコードが見つかりません: {missing}")

    result = []
    for update in updates:
        current = store.records[str(update["id"])]
        current.update(update.get("record", {}))
        revision = str(int(current["$revision"]["value"]) + 1)
        current["$revision"]["value"] = revision
        result.append({"id": str(update["id"]), "revision": revision})
    return {"records": result}


@router.get("/debug/records")
def debug_records(request: Request) -> list[dict]:
    """登録内容を見やすい形で返す（モック独自。本物の kintone にはない）。"""
    return [{k: v.get("value") for k, v in r.items()} for r in _store(request).records.values()]
