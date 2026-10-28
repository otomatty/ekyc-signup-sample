"""申込データを kintone に同期するバッチ。

実行:
    python -m batch.sync_to_kintone            # 同期する
    python -m batch.sync_to_kintone --dry-run  # 対象件数だけ表示

本番では Cloud Run Jobs ＋ Cloud Scheduler などで定期実行する想定。

二重登録を防ぐ考え方:
  前回の実行で「kintone への登録は成功したが、DB に連携済みと記録する前に落ちた」場合、
  素直に再登録すると kintone に同じ申込が2件できる。
  そこで登録の前に「申込ID」で kintone を検索し、見つかったものは更新に回す。
"""

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass

from app import repository
from app.config import get_settings
from app.db import connect, init_db

from .kintone_client import KintoneClient, KintoneError

logger = logging.getLogger("batch.sync_to_kintone")

STATUS_LABEL = {
    "VERIFIED": "本人確認OK",
    "NEEDS_REVIEW": "要確認",
    "REJECTED": "照合NG",
    "EKYC_FAILED": "本人確認エラー",
}
RESULT_LABEL = {"MATCH": "一致", "PARTIAL": "一部一致", "MISMATCH": "不一致", "SKIPPED": "対象外"}


@dataclass
class SyncSummary:
    target: int = 0
    added: int = 0
    updated: int = 0


def summarize_match(match_detail: str | None) -> str:
    """照合結果を審査担当が読める1行にする。カードの読み取り値そのものは載せない。"""
    if not match_detail:
        return ""
    items = json.loads(match_detail)
    return " / ".join(
        f"{i['label']}: {RESULT_LABEL.get(i['result'], i['result'])}" + (f"（{i['note']}）" if i["note"] else "")
        for i in items
    )


def to_kintone_record(row: sqlite3.Row) -> dict:
    """DB の1行を kintone のレコード形式に変換する。

    審査に必要な申込内容と判定結果だけを送る。
    カードから取得した基本4情報（本人確認記録）は DB 側に保管し、kintone には送らない。
    """
    return {
        "申込ID": {"value": row["id"]},
        "氏名": {"value": row["name"]},
        "生年月日": {"value": row["birth_date"]},
        "住所": {"value": row["address"]},
        "電話番号": {"value": row["phone"]},
        "メールアドレス": {"value": row["email"]},
        "プラン": {"value": row["plan"]},
        "本人確認ステータス": {"value": STATUS_LABEL.get(row["status"], row["status"])},
        "照合結果": {"value": summarize_match(row["match_detail"])},
        "エラー理由": {"value": row["failure_reason"] or ""},
        "本人確認日時": {"value": row["received_at"] or ""},
    }


def run(client: KintoneClient, conn: sqlite3.Connection, dry_run: bool = False) -> SyncSummary:
    rows = repository.list_unsynced(conn)
    summary = SyncSummary(target=len(rows))
    logger.info("sync target=%d", len(rows))
    if not rows or dry_run:
        return summary

    # 前回の途中失敗で kintone に登録済みのものを探す
    existing = client.find_ids_by_application([r["id"] for r in rows])

    to_add = [r for r in rows if not r["kintone_record_id"] and r["id"] not in existing]
    to_update = [
        (r["id"], r["kintone_record_id"] or existing[r["id"]], to_kintone_record(r))
        for r in rows
        if r["kintone_record_id"] or r["id"] in existing
    ]

    if to_add:
        record_ids = client.add_records([to_kintone_record(r) for r in to_add])
        repository.mark_synced(conn, zip([r["id"] for r in to_add], record_ids))
        summary.added = len(to_add)

    if to_update:
        client.update_records([(record_id, record) for _, record_id, record in to_update])
        repository.mark_synced(conn, [(app_id, record_id) for app_id, record_id, _ in to_update])
        summary.updated = len(to_update)

    # ログには件数とIDだけを出す。個人情報は出さない
    logger.info("sync done added=%d updated=%d", summary.added, summary.updated)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="申込データを kintone に同期する")
    parser.add_argument("--dry-run", action="store_true", help="対象件数を表示するだけで送信しない")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    init_db(settings.db_path)
    conn = connect(settings.db_path)
    client = KintoneClient(settings.kintone_base_url, settings.kintone_app_id, settings.kintone_api_token)
    try:
        summary = run(client, conn, dry_run=args.dry_run)
    except KintoneError as e:
        # 失敗は終了コードで知らせる（Cloud Run Jobs ならジョブ失敗として検知・通知できる）
        logger.error("sync failed: %s", e)
        return 1
    finally:
        conn.close()
    print(f"対象 {summary.target} 件 / 登録 {summary.added} 件 / 更新 {summary.updated} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
