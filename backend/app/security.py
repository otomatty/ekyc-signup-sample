"""署名まわり。

1. 申込ID受け渡しトークン
   申込フォーム（本番ではフォーム SaaS など）から eKYC 画面へ申込IDを渡すとき、
   URL に生のIDを載せると、他人のIDに書き換えられるおそれがある。
   そこで「申込ID＋有効期限」に HMAC 署名を付けたトークンを渡す。

2. Webhook（コールバック）署名
   ベンダーからのコールバックが本物で、改ざんされていないことを確かめる。
   タイムスタンプも署名に含め、古いリクエストの再送（リプレイ）を防ぐ。
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime


class InvalidToken(Exception):
    pass


class InvalidSignature(Exception):
    pass


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _hmac(secret: str, message: bytes) -> bytes:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


# ---- 1. 申込ID受け渡しトークン ----


def issue_handoff_token(
    application_id: str, secret: str, ttl_seconds: int, now: float | None = None
) -> tuple[str, datetime]:
    issued = now if now is not None else time.time()
    exp = int(issued + ttl_seconds)
    payload = _b64e(json.dumps({"aid": application_id, "exp": exp}, separators=(",", ":")).encode())
    signature = _b64e(_hmac(secret, payload.encode("ascii")))
    return f"{payload}.{signature}", datetime.fromtimestamp(exp, UTC)


def verify_handoff_token(token: str, secret: str, now: float | None = None) -> str:
    """正しければ申込IDを返す。不正・期限切れなら InvalidToken。"""
    try:
        payload, signature = token.split(".")
    except ValueError as e:
        raise InvalidToken("形式が不正です") from e

    expected = _b64e(_hmac(secret, payload.encode("ascii")))
    # 文字列比較の時間差から推測されないよう、定数時間で比較する
    if not hmac.compare_digest(signature, expected):
        raise InvalidToken("署名が一致しません")

    try:
        data = json.loads(_b64d(payload))
    except (ValueError, json.JSONDecodeError) as e:
        raise InvalidToken("内容を読み取れません") from e

    current = now if now is not None else time.time()
    if current > data.get("exp", 0):
        raise InvalidToken("有効期限が切れています")
    return str(data["aid"])


# ---- 2. Webhook 署名 ----


def sign_webhook(body: bytes, secret: str, timestamp: int) -> str:
    return "sha256=" + _hmac(secret, f"{timestamp}.".encode() + body).hex()


def verify_webhook(
    body: bytes,
    secret: str,
    signature_header: str | None,
    timestamp_header: str | None,
    tolerance_seconds: int,
    now: float | None = None,
) -> None:
    if not signature_header or not timestamp_header:
        raise InvalidSignature("署名ヘッダーがありません")
    try:
        timestamp = int(timestamp_header)
    except ValueError as e:
        raise InvalidSignature("タイムスタンプが不正です") from e

    current = now if now is not None else time.time()
    if abs(current - timestamp) > tolerance_seconds:
        raise InvalidSignature("タイムスタンプが許容範囲外です")

    expected = sign_webhook(body, secret, timestamp)
    if not hmac.compare_digest(signature_header, expected):
        raise InvalidSignature("署名が一致しません")
