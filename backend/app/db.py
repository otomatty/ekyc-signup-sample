"""SQLite の接続とスキーマ。

学習用に ORM を使わず標準ライブラリの sqlite3 で書いている。
本番では Cloud SQL などの RDB と SQLAlchemy 等を使う想定。
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    birth_date        TEXT NOT NULL,
    gender            TEXT,
    postal_code       TEXT NOT NULL,
    address           TEXT NOT NULL,
    phone             TEXT NOT NULL,
    email             TEXT NOT NULL,
    plan              TEXT NOT NULL,
    status            TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    kintone_record_id TEXT,
    kintone_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS ekyc_sessions (
    session_id     TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id),
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ekyc_results (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id            TEXT NOT NULL UNIQUE,  -- 冪等性: 同じイベントは1回だけ記録
    application_id      TEXT NOT NULL REFERENCES applications(id),
    session_id          TEXT NOT NULL,
    result              TEXT NOT NULL,         -- SUCCESS / FAILED
    failure_reason      TEXT,
    verified_name       TEXT,                  -- 以下はカードから取得した基本4情報（本人確認記録）
    verified_birth_date TEXT,
    verified_gender     TEXT,
    verified_address    TEXT,
    match_result        TEXT,                  -- VERIFIED / NEEDS_REVIEW / REJECTED
    match_detail        TEXT,                  -- 項目ごとの判定（JSON）
    received_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_results_application ON ekyc_results(application_id);
"""


def connect(db_path: str) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def now_iso() -> str:
    """UTC の ISO 8601 文字列。文字列比較で前後関係が分かる形式にそろえる。"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
