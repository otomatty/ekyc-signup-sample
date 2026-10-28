"""FastAPI の依存性（Depends）。

React でいう Context のように「どこからでも同じものを受け取る」仕組み。
テストでは app.dependency_overrides で差し替えられる。
"""

import sqlite3
from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, Request, status

from app.config import Settings
from app.db import connect
from app.security import InvalidToken, verify_handoff_token
from app.services.ekyc_vendor import EkycVendorClient


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_conn(settings: Settings = Depends(get_app_settings)) -> Iterator[sqlite3.Connection]:
    conn = connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_vendor_client(settings: Settings = Depends(get_app_settings)) -> EkycVendorClient:
    return EkycVendorClient(
        base_url=settings.vendor_base_url,
        api_key=settings.vendor_api_key,
        timeout=settings.vendor_timeout_seconds,
    )


def application_id_from_bearer(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_app_settings),
) -> str:
    """Authorization: Bearer <handoff_token> から申込IDを取り出す。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "トークンがありません")
    try:
        return verify_handoff_token(authorization.removeprefix("Bearer "), settings.app_secret)
    except InvalidToken as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "トークンが無効です") from e
