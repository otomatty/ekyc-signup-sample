"""eKYC API。

  POST /api/ekyc/sessions  ... 本人確認を開始し、ベンダーの画面URLを返す
  POST /api/ekyc/callback  ... ベンダーから結果を受け取る（Webhook）
"""

import logging
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError

from app import repository
from app.config import Settings
from app.deps import get_app_settings, get_conn, get_vendor_client
from app.matching import PersonData, evaluate
from app.models import (
    STARTABLE_STATUSES,
    ApplicationStatus,
    EkycSessionCreate,
    EkycSessionCreated,
    VendorCallback,
)
from app.security import InvalidSignature, InvalidToken, verify_handoff_token, verify_webhook
from app.services.ekyc_vendor import EkycVendorClient, VendorError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ekyc", tags=["ekyc"])


@router.post("/sessions", response_model=EkycSessionCreated)
async def start_ekyc(
    body: EkycSessionCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    settings: Settings = Depends(get_app_settings),
    vendor: EkycVendorClient = Depends(get_vendor_client),
) -> EkycSessionCreated:
    try:
        application_id = verify_handoff_token(body.handoff_token, settings.app_secret)
    except InvalidToken as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "お手続きの有効期限が切れました。最初からやり直してください。") from e

    row = repository.get_application(conn, application_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "申込が見つかりません")
    if ApplicationStatus(row["status"]) not in STARTABLE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "この申込の本人確認は完了しています")

    try:
        session = await vendor.create_session(
            reference_id=application_id,
            callback_url=f"{settings.api_base_url}/api/ekyc/callback",
            return_url=f"{settings.frontend_base_url}/result",
        )
    except VendorError as e:
        logger.error("vendor session failed application_id=%s error=%s", application_id, e)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "本人確認サービスに接続できませんでした。時間をおいてお試しください。"
        ) from e

    repository.create_session(conn, session.session_id, application_id)
    logger.info("ekyc started application_id=%s session_id=%s", application_id, session.session_id)
    return EkycSessionCreated(verify_url=session.verify_url)


@router.post("/callback")
async def receive_callback(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, str]:
    # 署名は「受け取った生のバイト列」で検証する。JSON を解釈し直すと順序や空白が変わるため
    raw = await request.body()
    try:
        verify_webhook(
            raw,
            settings.vendor_webhook_secret,
            request.headers.get("X-Vendor-Signature"),
            request.headers.get("X-Vendor-Timestamp"),
            settings.webhook_tolerance_seconds,
        )
    except InvalidSignature as e:
        logger.warning("callback rejected: %s", e)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid signature") from e

    try:
        callback = VendorCallback.model_validate_json(raw)
    except ValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid payload") from e

    session = repository.get_session(conn, callback.session_id)
    if session is None or session["application_id"] != callback.reference_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown session")

    application = repository.get_application(conn, callback.reference_id)
    if application is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown application")

    checks = []
    if callback.result == "SUCCESS" and callback.identity is not None:
        outcome = evaluate(
            PersonData(
                name=application["name"],
                birth_date=date.fromisoformat(application["birth_date"]),
                gender=application["gender"],
                address=application["address"],
            ),
            PersonData(
                name=callback.identity.name,
                birth_date=callback.identity.birth_date,
                gender=callback.identity.gender.value if callback.identity.gender else None,
                address=callback.identity.address,
            ),
        )
        new_status, checks = outcome.overall, outcome.checks
    else:
        new_status = ApplicationStatus.EKYC_FAILED

    if not repository.save_result(conn, callback, new_status, checks):
        # 再送は正常に受け付けたことにする（ベンダーがリトライし続けないよう 200 を返す）
        logger.info("duplicate callback ignored event_id=%s", callback.event_id)
        return {"status": "duplicate"}

    logger.info(
        "callback processed application_id=%s result=%s status=%s",
        callback.reference_id,
        callback.result,
        new_status.value,
    )
    return {"status": "accepted"}
