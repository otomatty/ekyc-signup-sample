"""申込 API。

本番では既存の申込フォーム（クライゼルなどのフォーム SaaS）が申込を受け付けることが多いが、
このサンプルでは同じ役割を FastAPI のエンドポイントで代用している。
"""

import json
import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app import repository
from app.config import Settings
from app.deps import application_id_from_bearer, get_app_settings, get_conn
from app.masking import mask_name
from app.models import (
    STARTABLE_STATUSES,
    ApplicationCreate,
    ApplicationCreated,
    ApplicationStatus,
    ApplicationStatusResponse,
    MatchItem,
)
from app.security import issue_handoff_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/applications", tags=["applications"])

STATUS_TEXT: dict[ApplicationStatus, tuple[str, str]] = {
    ApplicationStatus.APPLIED: ("申込受付", "本人確認を開始してください。"),
    ApplicationStatus.EKYC_IN_PROGRESS: ("本人確認中", "本人確認の結果を待っています。"),
    ApplicationStatus.VERIFIED: ("本人確認完了", "本人確認が完了しました。このまま審査に進みます。"),
    ApplicationStatus.NEEDS_REVIEW: (
        "担当者確認中",
        "担当者がお申込内容を確認します。結果はメールでお知らせします。",
    ),
    ApplicationStatus.REJECTED: (
        "本人確認NG",
        "お申込内容と、マイナンバーカードの情報が一致しませんでした。入力内容をご確認ください。",
    ),
    ApplicationStatus.EKYC_FAILED: ("本人確認エラー", "本人確認を完了できませんでした。"),
}

FAILURE_TEXT = {
    "PIN_LOCKED": "パスワードがロックされています。お住まいの市区町村の窓口で再設定してから、もう一度お試しください。",
    "CERT_REVOKED": "電子証明書が失効しています。市区町村の窓口で再発行してから、もう一度お試しください。",
    "CERT_EXPIRED": "電子証明書の有効期限が切れています。市区町村の窓口で更新してから、もう一度お試しください。",
    "CANCELLED": "本人確認が中断されました。もう一度お試しください。",
}


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApplicationCreated)
def create_application(
    body: ApplicationCreate,
    conn: sqlite3.Connection = Depends(get_conn),
    settings: Settings = Depends(get_app_settings),
) -> ApplicationCreated:
    application_id = repository.create_application(conn, body)
    token, expires_at = issue_handoff_token(application_id, settings.app_secret, settings.handoff_token_ttl_seconds)
    # ログに個人情報を出さない。必要なら申込IDとマスク済みの値だけ
    logger.info("application created id=%s name=%s", application_id, mask_name(body.name))
    return ApplicationCreated(application_id=application_id, handoff_token=token, expires_at=expires_at)


@router.get("/{application_id}", response_model=ApplicationStatusResponse)
def get_application_status(
    application_id: str,
    token_application_id: str = Depends(application_id_from_bearer),
    conn: sqlite3.Connection = Depends(get_conn),
) -> ApplicationStatusResponse:
    # トークンの申込IDとURLの申込IDが違う = 他人の申込を見ようとしている。
    # 存在の有無も教えないよう 404 を返す
    if token_application_id != application_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "申込が見つかりません")
    row = repository.get_application(conn, application_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "申込が見つかりません")

    current = ApplicationStatus(row["status"])
    label, message = STATUS_TEXT[current]
    match_items: list[MatchItem] = []

    result = repository.get_latest_result(conn, application_id)
    if result is not None:
        if current == ApplicationStatus.EKYC_FAILED:
            message = FAILURE_TEXT.get(result["failure_reason"], message)
        if result["match_detail"]:
            match_items = [MatchItem(**item) for item in json.loads(result["match_detail"])]

    return ApplicationStatusResponse(
        application_id=application_id,
        status=current,
        status_label=label,
        message=message,
        masked_name=mask_name(row["name"]),
        can_retry=current in STARTABLE_STATUSES,
        match_items=match_items,
        updated_at=row["updated_at"],
    )
