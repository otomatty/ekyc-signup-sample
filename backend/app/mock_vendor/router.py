"""モックの eKYC ベンダー。

実際の JPKI 連携では、スマホアプリ（または SDK）がマイナンバーカードを NFC で読み取り、
署名用パスワードで電子署名し、ベンダー（PF事業者）が検証して結果を返す。
このモックはその流れを、ブラウザ上の1画面と Webhook で再現する。

  POST /mock-vendor/v1/sessions          セッション作成（APIキー必須）
  GET  /mock-vendor/verify/{session_id}  利用者が操作する画面
  POST /mock-vendor/verify/{session_id}  結果を確定 -> コールバック送信 -> 戻り先へリダイレクト
"""

import asyncio
import html
import json
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, BackgroundTasks, Form, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.security import sign_webhook

from .personas import PERSONAS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mock-vendor", tags=["mock-vendor"])


class SessionRequest(BaseModel):
    reference_id: str
    callback_url: str
    return_url: str


@dataclass
class MockSession:
    session_id: str
    reference_id: str
    callback_url: str
    return_url: str
    used: bool = False


def _sessions(request: Request) -> dict[str, MockSession]:
    return request.app.state.mock_vendor_sessions


@router.post("/v1/sessions")
def create_session(body: SessionRequest, request: Request, authorization: str | None = Header(default=None)) -> dict:
    settings = request.app.state.settings
    if authorization != f"Bearer {settings.vendor_api_key}":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid api key")
    session_id = "ses_" + uuid.uuid4().hex
    _sessions(request)[session_id] = MockSession(session_id, body.reference_id, body.callback_url, body.return_url)
    return {"session_id": session_id, "verify_url": f"{settings.vendor_base_url.rstrip('/')}/verify/{session_id}"}


@router.get("/verify/{session_id}", response_class=HTMLResponse)
def verify_page(session_id: str, request: Request) -> HTMLResponse:
    session = _sessions(request).get(session_id)
    if session is None:
        return HTMLResponse(_render_message("セッションが見つかりません", "有効期限が切れたか、URLが正しくありません。"), 404)
    if session.used:
        return HTMLResponse(_render_message("この本人確認は完了しています", "申込画面に戻ってください。"), 410)
    return HTMLResponse(_render_form(session_id))


@router.post("/verify/{session_id}")
async def submit(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    persona: str = Form(default=""),
    password: str = Form(default=""),
    action: str = Form(default="submit"),
):
    settings = request.app.state.settings
    session = _sessions(request).get(session_id)
    if session is None or session.used:
        return HTMLResponse(_render_message("この本人確認は使用できません", "申込画面からやり直してください。"), 410)

    if action == "cancel":
        payload = _failed_payload(session, "CANCELLED")
    else:
        selected = PERSONAS.get(persona)
        if selected is None:
            return HTMLResponse(_render_form(session_id, "テスト用カードを選んでください。"), 400)
        if not re.fullmatch(r"[A-Za-z0-9]{6,16}", password):
            return HTMLResponse(_render_form(session_id, "署名用パスワードは英数字6〜16文字です。", persona), 400)
        if selected.identity is not None:
            payload = _success_payload(session, selected.identity)
        else:
            payload = _failed_payload(session, selected.failure_reason or "UNKNOWN")

    session.used = True
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    times = 2 if settings.mock_vendor_duplicate_callback else 1
    # 画面の応答を先に返し、コールバックはその後で送る（実際のベンダーも非同期で送ってくる）
    background_tasks.add_task(deliver_callback, session.callback_url, body, settings.vendor_webhook_secret, times)
    return RedirectResponse(session.return_url, status_code=status.HTTP_303_SEE_OTHER)


# ---- コールバック送信 ----


async def callback_sender(url: str, body: bytes, headers: dict[str, str]) -> int:
    """実際に HTTP で送る部分。テストではこの関数を差し替える。"""
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(url, content=body, headers=headers)
        return res.status_code


async def deliver_callback(url: str, body: bytes, secret: str, times: int = 1, attempts: int = 3) -> None:
    for _ in range(times):
        for attempt in range(1, attempts + 1):
            timestamp = int(time.time())
            headers = {
                "Content-Type": "application/json",
                "X-Vendor-Timestamp": str(timestamp),
                "X-Vendor-Signature": sign_webhook(body, secret, timestamp),
            }
            try:
                code = await callback_sender(url, body, headers)
                if code < 500:
                    logger.info("mock vendor callback delivered status=%d", code)
                    break
                logger.warning("mock vendor callback got %d attempt=%d", code, attempt)
            except httpx.TransportError as e:
                logger.warning("mock vendor callback failed attempt=%d error=%s", attempt, type(e).__name__)
            await asyncio.sleep(attempt)


def _base_payload(session: MockSession) -> dict:
    return {
        "event_id": "evt_" + uuid.uuid4().hex,
        "session_id": session.session_id,
        "reference_id": session.reference_id,
        "verified_at": datetime.now(UTC).isoformat(),
    }


def _success_payload(session: MockSession, identity) -> dict:
    return {
        **_base_payload(session),
        "result": "SUCCESS",
        "failure_reason": None,
        "identity": {
            "name": identity.name,
            "birth_date": identity.birth_date,
            "gender": identity.gender,
            "address": identity.address,
        },
    }


def _failed_payload(session: MockSession, reason: str) -> dict:
    return {**_base_payload(session), "result": "FAILED", "failure_reason": reason, "identity": None}


# ---- 画面（モックなのでテンプレートエンジンを使わず文字列で組み立てる） ----

_STYLE = """
body{font-family:system-ui,"Hiragino Sans","Noto Sans JP",sans-serif;background:#eef2f7;margin:0;color:#1f2937}
.wrap{max-width:520px;margin:0 auto;padding:24px 16px}
.badge{display:inline-block;background:#fde68a;color:#78350f;font-size:12px;font-weight:700;padding:2px 10px;border-radius:99px}
.card{background:#fff;border-radius:14px;padding:20px;margin-top:14px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
h1{font-size:20px;margin:10px 0 4px}p{line-height:1.7;margin:6px 0}
label.p{display:flex;gap:10px;padding:10px;border:1px solid #e5e7eb;border-radius:10px;margin:8px 0;cursor:pointer}
label.p:has(input:checked){border-color:#2563eb;background:#eff6ff}
.p small{display:block;color:#6b7280}
input[type=password]{width:100%;font-size:16px;padding:10px;border:1px solid #d1d5db;border-radius:8px;box-sizing:border-box}
.row{display:flex;gap:10px;margin-top:16px}
button{flex:1;font-size:16px;padding:12px;border-radius:10px;border:0;cursor:pointer}
.primary{background:#2563eb;color:#fff}.ghost{background:#e5e7eb;color:#111827}
.err{background:#fee2e2;color:#991b1b;padding:10px;border-radius:8px;margin-top:10px}
.note{font-size:13px;color:#6b7280}
"""


def _page(body: str) -> str:
    return (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>モック本人確認</title><style>{_STYLE}</style></head>"
        f'<body><div class="wrap"><span class="badge">MOCK eKYC VENDOR</span>{body}</div></body></html>'
    )


def _render_form(session_id: str, error: str | None = None, selected: str = "") -> str:
    options = "".join(
        f'<label class="p"><input type="radio" name="persona" value="{p.key}"'
        f'{" checked" if p.key == selected else ""}>'
        f"<span>{html.escape(p.label)}<small>{html.escape(p.description)}</small></span></label>"
        for p in PERSONAS.values()
    )
    err = f'<div class="err">{html.escape(error)}</div>' if error else ""
    return _page(
        f"""
        <h1>マイナンバーカードで本人確認</h1>
        <p class="note">本物では、ここでスマホにカードをかざして読み取ります。このモックでは、読み取るカードを選びます。</p>
        <form method="post" action="/mock-vendor/verify/{html.escape(session_id)}">
          <div class="card">
            <p><b>1. 読み取るテスト用カード</b></p>{options}
          </div>
          <div class="card">
            <p><b>2. 署名用パスワード</b>（英数字6〜16文字。モックなので何でも可）</p>
            <input type="password" name="password" autocomplete="off" minlength="6" maxlength="16">
            {err}
          </div>
          <div class="row">
            <button class="ghost" name="action" value="cancel" formnovalidate>中断する</button>
            <button class="primary" name="action" value="submit">読み取って送信</button>
          </div>
        </form>
        """
    )


def _render_message(title: str, message: str) -> str:
    return _page(f'<div class="card"><h1>{html.escape(title)}</h1><p>{html.escape(message)}</p></div>')
