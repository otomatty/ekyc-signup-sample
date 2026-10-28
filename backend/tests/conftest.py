import os

# テスト中に app.main を import したとき、作業用DBを汚さないようにする
os.environ.setdefault("DB_PATH", ":memory:")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.deps import get_vendor_client  # noqa: E402
from app.main import create_app  # noqa: E402
from app.mock_vendor import router as mock_vendor_router  # noqa: E402
from app.services.ekyc_vendor import EkycVendorClient  # noqa: E402

MATCH_APPLICATION = {
    "name": "山田 太郎",
    "birth_date": "1990-04-01",
    "gender": "male",
    "postal_code": "100-0001",
    "address": "東京都千代田区サンプル町1-2-3 サンプルハイツ101",
    "phone": "090-1234-5678",
    "email": "taro@example.com",
    "plan": "standard",
}


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "test.db"),
        api_base_url="http://testserver",
        vendor_base_url="http://testserver/mock-vendor",
        kintone_base_url="http://testserver/mock-kintone",
        frontend_base_url="http://localhost:5173",
    )


@pytest.fixture
def app(settings):
    app = create_app(settings)
    # ベンダーへの HTTP 呼び出しを、実際のネットワークを使わず同じアプリ内のモックに向ける
    app.dependency_overrides[get_vendor_client] = lambda: EkycVendorClient(
        base_url=settings.vendor_base_url,
        api_key=settings.vendor_api_key,
        backoff_seconds=0,
        transport=httpx.ASGITransport(app=app),
    )
    return app


@pytest.fixture
def client(app) -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def captured_callbacks(monkeypatch) -> list[tuple[str, bytes, dict]]:
    """モックベンダーが送るコールバックを横取りして記録する。"""
    sent: list[tuple[str, bytes, dict]] = []

    async def fake_sender(url: str, body: bytes, headers: dict) -> int:
        sent.append((url, body, headers))
        return 200

    monkeypatch.setattr(mock_vendor_router, "callback_sender", fake_sender)
    return sent


def run_ekyc(client: TestClient, captured: list, application: dict, persona: str) -> tuple[str, str]:
    """申込 -> 本人確認開始 -> モック画面で送信 -> コールバック受信 までを通しで実行する。"""
    res = client.post("/api/applications", json=application)
    assert res.status_code == 201, res.text
    created = res.json()

    res = client.post("/api/ekyc/sessions", json={"handoff_token": created["handoff_token"]})
    assert res.status_code == 200, res.text
    verify_path = httpx.URL(res.json()["verify_url"]).path

    res = client.post(
        verify_path,
        data={"persona": persona, "password": "abc123", "action": "submit"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "http://localhost:5173/result"

    url, body, headers = captured[-1]
    res = client.post(httpx.URL(url).path, content=body, headers=headers)
    assert res.status_code == 200, res.text
    return created["application_id"], created["handoff_token"]
