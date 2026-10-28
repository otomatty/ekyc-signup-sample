"""申込から本人確認結果までを API 経由で通して確かめるテスト。"""

import httpx

from app import repository
from app.db import connect

from .conftest import MATCH_APPLICATION, run_ekyc


def status_of(client, application_id: str, token: str) -> dict:
    res = client.get(f"/api/applications/{application_id}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    return res.json()


def test_match_flow_is_verified(client, captured_callbacks):
    application_id, token = run_ekyc(client, captured_callbacks, MATCH_APPLICATION, "match")
    body = status_of(client, application_id, token)
    assert body["status"] == "VERIFIED"
    assert body["masked_name"] == "山田 ＊＊"
    assert {i["field"]: i["result"] for i in body["match_items"]} == {
        "name": "MATCH",
        "birth_date": "MATCH",
        "gender": "MATCH",
        "address": "MATCH",
    }
    # 申込者向けの応答に、住所などの個人情報が含まれていないこと
    assert "サンプル町" not in str(body)


def test_itaiji_flow_needs_review(client, captured_callbacks):
    application = MATCH_APPLICATION | {
        "name": "高橋 花子",
        "birth_date": "1985-11-20",
        "gender": "female",
        "address": "神奈川県横浜市西区みなと見本2-5-8",
    }
    application_id, token = run_ekyc(client, captured_callbacks, application, "itaiji")
    assert status_of(client, application_id, token)["status"] == "NEEDS_REVIEW"


def test_locked_flow_can_retry(client, captured_callbacks):
    application_id, token = run_ekyc(client, captured_callbacks, MATCH_APPLICATION, "locked")
    body = status_of(client, application_id, token)
    assert body["status"] == "EKYC_FAILED"
    assert body["can_retry"] is True
    assert "ロック" in body["message"]
    # 失敗後はもう一度本人確認を始められる
    res = client.post("/api/ekyc/sessions", json={"handoff_token": token})
    assert res.status_code == 200


def test_duplicate_callback_is_ignored(client, captured_callbacks, settings):
    application_id, _ = run_ekyc(client, captured_callbacks, MATCH_APPLICATION, "match")
    url, body, headers = captured_callbacks[-1]
    res = client.post(httpx.URL(url).path, content=body, headers=headers)
    assert res.json() == {"status": "duplicate"}
    conn = connect(settings.db_path)
    assert repository.count_results(conn, application_id) == 1
    conn.close()


def test_callback_with_bad_signature_is_rejected(client, captured_callbacks):
    run_ekyc(client, captured_callbacks, MATCH_APPLICATION, "match")
    url, body, headers = captured_callbacks[-1]
    tampered = body.replace("山田".encode(), "田中".encode())
    res = client.post(httpx.URL(url).path, content=tampered, headers=headers)
    assert res.status_code == 401


def test_cannot_restart_after_verified(client, captured_callbacks):
    _, token = run_ekyc(client, captured_callbacks, MATCH_APPLICATION, "match")
    res = client.post("/api/ekyc/sessions", json={"handoff_token": token})
    assert res.status_code == 409


def test_status_requires_own_token(client):
    a = client.post("/api/applications", json=MATCH_APPLICATION).json()
    b = client.post("/api/applications", json=MATCH_APPLICATION | {"email": "b@example.com"}).json()

    assert client.get(f"/api/applications/{a['application_id']}").status_code == 401
    # 他人のトークンでは見られない（存在も明かさない）
    res = client.get(
        f"/api/applications/{a['application_id']}",
        headers={"Authorization": f"Bearer {b['handoff_token']}"},
    )
    assert res.status_code == 404


def test_validation_rejects_minor(client):
    res = client.post("/api/applications", json=MATCH_APPLICATION | {"birth_date": "2015-01-01"})
    assert res.status_code == 422
    assert "18歳以上" in res.text


def test_invalid_handoff_token(client):
    res = client.post("/api/ekyc/sessions", json={"handoff_token": "broken.token"})
    assert res.status_code == 401


def test_mock_vendor_requires_api_key(client):
    res = client.post(
        "/mock-vendor/v1/sessions",
        json={"reference_id": "x", "callback_url": "http://x", "return_url": "http://x"},
    )
    assert res.status_code == 401
