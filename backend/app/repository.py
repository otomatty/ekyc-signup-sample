"""DB アクセス。SQL はここに集め、ルーターから直接書かない。"""

import json
import sqlite3
import uuid
from collections.abc import Iterable

from app.db import now_iso
from app.matching import FieldCheck
from app.models import SYNC_TARGET_STATUSES, ApplicationCreate, ApplicationStatus, VendorCallback


def create_application(conn: sqlite3.Connection, data: ApplicationCreate) -> str:
    application_id = str(uuid.uuid4())
    now = now_iso()
    with conn:
        conn.execute(
            """
            INSERT INTO applications
              (id, name, birth_date, gender, postal_code, address, phone, email, plan,
               status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                application_id,
                data.name,
                data.birth_date.isoformat(),
                data.gender.value if data.gender else None,
                data.postal_code,
                data.address,
                data.phone,
                data.email,
                data.plan.value,
                ApplicationStatus.APPLIED.value,
                now,
                now,
            ),
        )
    return application_id


def get_application(conn: sqlite3.Connection, application_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()


def update_status(conn: sqlite3.Connection, application_id: str, status: ApplicationStatus) -> None:
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = ? WHERE id = ?",
        (status.value, now_iso(), application_id),
    )


def create_session(conn: sqlite3.Connection, session_id: str, application_id: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO ekyc_sessions (session_id, application_id, created_at) VALUES (?, ?, ?)",
            (session_id, application_id, now_iso()),
        )
        update_status(conn, application_id, ApplicationStatus.EKYC_IN_PROGRESS)


def get_session(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM ekyc_sessions WHERE session_id = ?", (session_id,)).fetchone()


def save_result(
    conn: sqlite3.Connection,
    callback: VendorCallback,
    new_status: ApplicationStatus,
    checks: Iterable[FieldCheck] = (),
) -> bool:
    """結果を保存し、申込の状態を更新する。同じ event_id が既にあれば何もせず False。

    「結果の保存」と「状態の更新」を1つのトランザクションにまとめ、片方だけ反映される状態を防ぐ。
    """
    identity = callback.identity
    detail = json.dumps(
        [{"field": c.field, "label": c.label, "result": c.result.value, "note": c.note} for c in checks],
        ensure_ascii=False,
    )
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO ekyc_results
                  (event_id, application_id, session_id, result, failure_reason,
                   verified_name, verified_birth_date, verified_gender, verified_address,
                   match_result, match_detail, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    callback.event_id,
                    callback.reference_id,
                    callback.session_id,
                    callback.result,
                    callback.failure_reason,
                    identity.name if identity else None,
                    identity.birth_date.isoformat() if identity else None,
                    identity.gender.value if identity and identity.gender else None,
                    identity.address if identity else None,
                    new_status.value if callback.result == "SUCCESS" else None,
                    detail,
                    now_iso(),
                ),
            )
            update_status(conn, callback.reference_id, new_status)
    except sqlite3.IntegrityError:
        # event_id の UNIQUE 制約違反 = 同じコールバックの再送
        return False
    return True


def get_latest_result(conn: sqlite3.Connection, application_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM ekyc_results WHERE application_id = ? ORDER BY id DESC LIMIT 1",
        (application_id,),
    ).fetchone()


def count_results(conn: sqlite3.Connection, application_id: str) -> int:
    row = conn.execute("SELECT COUNT(*) FROM ekyc_results WHERE application_id = ?", (application_id,)).fetchone()
    return int(row[0])


def list_unsynced(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """kintone にまだ反映していない申込（未連携、または連携後に更新されたもの）。"""
    placeholders = ",".join("?" for _ in SYNC_TARGET_STATUSES)
    return conn.execute(
        f"""
        SELECT a.*, r.result AS ekyc_result, r.failure_reason, r.match_detail, r.received_at
        FROM applications a
        LEFT JOIN ekyc_results r ON r.id = (
            SELECT MAX(id) FROM ekyc_results WHERE application_id = a.id
        )
        WHERE a.status IN ({placeholders})
          AND (a.kintone_synced_at IS NULL OR a.updated_at > a.kintone_synced_at)
        ORDER BY a.created_at
        """,
        tuple(s.value for s in SYNC_TARGET_STATUSES),
    ).fetchall()


def mark_synced(conn: sqlite3.Connection, pairs: Iterable[tuple[str, str]]) -> None:
    """(申込ID, kintoneレコードID) の組を連携済みにする。"""
    now = now_iso()
    with conn:
        conn.executemany(
            "UPDATE applications SET kintone_record_id = ?, kintone_synced_at = ? WHERE id = ?",
            [(record_id, now, application_id) for application_id, record_id in pairs],
        )
