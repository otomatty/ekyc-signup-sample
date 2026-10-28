"""API の入出力スキーマ（Pydantic）。

FastAPI はこの型を使って入力チェックと OpenAPI（/docs）の生成を自動で行う。
"""

from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ApplicationStatus(StrEnum):
    APPLIED = "APPLIED"                    # 申込受付（本人確認前）
    EKYC_IN_PROGRESS = "EKYC_IN_PROGRESS"  # 本人確認中
    VERIFIED = "VERIFIED"                  # 本人確認OK
    NEEDS_REVIEW = "NEEDS_REVIEW"          # 担当者の目視確認が必要
    REJECTED = "REJECTED"                  # 照合NG
    EKYC_FAILED = "EKYC_FAILED"            # 本人確認そのものが失敗（ロック、失効、中断など）


# 本人確認を（再）開始できる状態
STARTABLE_STATUSES = {
    ApplicationStatus.APPLIED,
    ApplicationStatus.EKYC_IN_PROGRESS,
    ApplicationStatus.EKYC_FAILED,
}

# kintone に連携する状態（本人確認の結果が出たもの）
SYNC_TARGET_STATUSES = {
    ApplicationStatus.VERIFIED,
    ApplicationStatus.NEEDS_REVIEW,
    ApplicationStatus.REJECTED,
    ApplicationStatus.EKYC_FAILED,
}


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class Plan(StrEnum):
    LIGHT = "light"
    STANDARD = "standard"
    UNLIMITED = "unlimited"


MIN_AGE = 18


class ApplicationCreate(BaseModel):
    """申込フォームの入力（本番では既存の申込フォームに相当）。"""

    name: str = Field(min_length=1, max_length=50, description="氏名（漢字）。姓と名の間はスペース")
    birth_date: date
    gender: Gender | None = Field(default=None, description="未回答も可")
    postal_code: str = Field(pattern=r"^\d{3}-?\d{4}$")
    address: str = Field(min_length=1, max_length=200)
    phone: str = Field(pattern=r"^0\d{1,4}-?\d{1,4}-?\d{3,4}$")
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    plan: Plan

    @field_validator("name", "address")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("空白のみは入力できません")
        return v

    @field_validator("birth_date")
    @classmethod
    def check_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < MIN_AGE:
            raise ValueError(f"{MIN_AGE}歳以上の方のみお申込みいただけます")
        if v.year < 1900:
            raise ValueError("生年月日を確認してください")
        return v


class ApplicationCreated(BaseModel):
    application_id: str
    handoff_token: str = Field(description="eKYC画面へ申込IDを安全に渡すための署名付きトークン")
    expires_at: datetime


class MatchItem(BaseModel):
    field: str
    label: str
    result: Literal["MATCH", "PARTIAL", "MISMATCH", "SKIPPED"]
    note: str = ""


class ApplicationStatusResponse(BaseModel):
    """申込者に返す状態。個人情報は最小限（マスキング済みの氏名だけ）にする。"""

    application_id: str
    status: ApplicationStatus
    status_label: str
    message: str
    masked_name: str
    can_retry: bool
    match_items: list[MatchItem] = []
    updated_at: str


class EkycSessionCreate(BaseModel):
    handoff_token: str


class EkycSessionCreated(BaseModel):
    verify_url: str


# ---- ベンダーとの連携（このサンプルではモックベンダーとの取り決め） ----


class VendorIdentity(BaseModel):
    """署名用電子証明書から取得した基本4情報。"""

    name: str
    birth_date: date
    gender: Gender | None = None
    address: str


class VendorCallback(BaseModel):
    event_id: str
    session_id: str
    reference_id: str = Field(description="こちらが渡した申込ID")
    result: Literal["SUCCESS", "FAILED"]
    failure_reason: str | None = None
    identity: VendorIdentity | None = None
    verified_at: datetime

    @model_validator(mode="after")
    def check_consistency(self) -> "VendorCallback":
        if self.result == "SUCCESS" and self.identity is None:
            raise ValueError("SUCCESS のときは identity が必要です")
        if self.result == "FAILED" and not self.failure_reason:
            raise ValueError("FAILED のときは failure_reason が必要です")
        return self
