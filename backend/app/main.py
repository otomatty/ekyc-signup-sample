"""アプリの組み立て。

  uvicorn app.main:app --reload --port 8000

で起動すると、次がまとめて動く。
  /api/...          本体の API（申込、eKYC）
  /mock-vendor/...  モックの eKYC ベンダー
  /mock-kintone/... モックの kintone
  /docs             自動生成される API 仕様（Swagger UI）
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.db import init_db
from app.mock_kintone.router import MockKintoneStore
from app.mock_kintone.router import router as mock_kintone_router
from app.mock_vendor.router import router as mock_vendor_router
from app.routers import applications, ekyc


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    init_db(settings.db_path)

    app = FastAPI(
        title="eKYC Sample API",
        version="0.1.0",
        description="WEB申込 × eKYC 改修を学ぶためのサンプル。モックのベンダーと kintone を同梱。",
    )
    app.state.settings = settings
    app.state.mock_vendor_sessions = {}
    app.state.mock_kintone = MockKintoneStore(fail_remaining=settings.mock_kintone_fail_first_n)

    # 本番のように申込フォームと API のドメインが分かれる場合に必要。
    # 開発中は Vite のプロキシ経由なので同一オリジンになる。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(applications.router)
    app.include_router(ekyc.router)
    app.include_router(mock_vendor_router)
    app.include_router(mock_kintone_router)

    @app.get("/api/healthz", tags=["system"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
