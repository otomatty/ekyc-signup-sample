import pytest

from app.masking import mask_address, mask_birth_date, mask_email, mask_name, mask_phone
from app.security import (
    InvalidSignature,
    InvalidToken,
    issue_handoff_token,
    sign_webhook,
    verify_handoff_token,
    verify_webhook,
)

SECRET = "test-secret"


def test_handoff_token_roundtrip():
    token, _ = issue_handoff_token("app-1", SECRET, 60, now=1000)
    assert verify_handoff_token(token, SECRET, now=1030) == "app-1"


def test_handoff_token_expired():
    token, _ = issue_handoff_token("app-1", SECRET, 60, now=1000)
    with pytest.raises(InvalidToken):
        verify_handoff_token(token, SECRET, now=1061)


def test_handoff_token_tampered():
    token, _ = issue_handoff_token("app-1", SECRET, 60, now=1000)
    other, _ = issue_handoff_token("app-2", SECRET, 60, now=1000)
    # 他人の申込IDの中身に、自分の署名をくっつけても通らない
    forged = other.split(".")[0] + "." + token.split(".")[1]
    with pytest.raises(InvalidToken):
        verify_handoff_token(forged, SECRET, now=1000)
    with pytest.raises(InvalidToken):
        verify_handoff_token(token, "another-secret", now=1000)


def test_webhook_signature():
    body = b'{"a":1}'
    signature = sign_webhook(body, SECRET, 2000)
    verify_webhook(body, SECRET, signature, "2000", 300, now=2100)

    with pytest.raises(InvalidSignature):
        verify_webhook(b'{"a":2}', SECRET, signature, "2000", 300, now=2100)  # 本文の改ざん
    with pytest.raises(InvalidSignature):
        verify_webhook(body, SECRET, signature, "2000", 300, now=2400)  # 古すぎる（リプレイ）
    with pytest.raises(InvalidSignature):
        verify_webhook(body, SECRET, None, "2000", 300, now=2100)  # ヘッダーなし


def test_masking():
    assert mask_name("山田 太郎") == "山田 ＊＊"
    assert mask_name("山田太郎") == "山＊＊＊"
    assert mask_phone("090-1234-5678") == "*******5678"
    assert mask_email("taro@example.com") == "t***@example.com"
    assert mask_address("東京都千代田区サンプル町1-2-3") == "東京都千代田区…"
    assert mask_birth_date("1990-04-01") == "1990-**-**"
