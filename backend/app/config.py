"""アプリ設定。

環境変数（または backend/.env）から読み込む。
本番では秘密情報を .env に置かず、Secret Manager などから注入する想定。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 申込ID受け渡しトークン
    app_secret: str = "dev-only-app-secret-change-me"
    handoff_token_ttl_seconds: int = 1800

    # データベース
    db_path: str = "./data/ekyc_sample.db"

    # URL
    api_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"
    cors_origins: list[str] = ["http://localhost:5173"]

    # eKYCベンダー
    vendor_base_url: str = "http://localhost:8000/mock-vendor"
    vendor_api_key: str = "dev-vendor-api-key"
    vendor_webhook_secret: str = "dev-vendor-webhook-secret"
    vendor_timeout_seconds: float = 5.0
    webhook_tolerance_seconds: int = 300

    # モックの挙動
    mock_vendor_duplicate_callback: bool = False
    mock_kintone_fail_first_n: int = 0

    # kintone
    kintone_base_url: str = "http://localhost:8000/mock-kintone"
    kintone_app_id: int = 1
    kintone_api_token: str = "dev-kintone-api-token"


@lru_cache
def get_settings() -> Settings:
    return Settings()
