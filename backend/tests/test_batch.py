"""kintone 同期バッチのテスト。モック kintone に対して実行する。"""

import uuid
from datetime import date

import pytest

from app import repository
from app.db import connect
from app.models import ApplicationCreate, ApplicationStatus, VendorCallback
from batch.kintone_client import KintoneClient, KintoneError
from batch.sync_to_kintone import run

from .conftest import MATCH_APPLICATION


@pytest.fixture
def conn(settings, client):  # client を先に作り、DB を初期化しておく
    c = connect(settings.db_path)
    yield c
    c.close()


@pytest.fixture
def kintone(settings, client) -> KintoneClient:
    return KintoneClient(
        settings.kintone_base_url,
        settings.kintone_app_id,
        settings.kintone_api_token,
        backoff_seconds=0,
        http=client,  # TestClient も httpx.Client なので、そのまま渡せる
    )


def make_verified(conn, n: int = 1, status: ApplicationStatus = ApplicationStatus.VERIFIED) -> list[str]:
    ids = []
    for i in range(n):
        app_id = repository.create_application(
            conn, ApplicationCreate(**(MATCH_APPLICATION | {"email": f"user{i}@example.com"}))
        )
        session_id = f"ses_{uuid.uuid4().hex}"
        repository.create_session(conn, session_id, app_id)
        callback = VendorCallback(
            event_id=f"evt_{uuid.uuid4().hex}",
            session_id=session_id,
            reference_id=app_id,
            result="SUCCESS",
            identity={"name": "山田 太郎", "birth_date": date(1990, 4, 1), "gender": "male", "address": "x"},
            verified_at="2026-10-28T00:00:00Z",
        )
        repository.save_result(conn, callback, status)
        ids.append(app_id)
    return ids


def kintone_records(client) -> list[dict]:
    return client.get("/mock-kintone/debug/records").json()


def test_first_run_adds_and_second_run_does_nothing(client, conn, kintone):
    make_verified(conn, 3)
    first = run(kintone, conn)
    assert (first.added, first.updated) == (3, 0)
    second = run(kintone, conn)
    assert (second.target, second.added, second.updated) == (0, 0, 0)
    assert len(kintone_records(client)) == 3


def test_status_change_is_sent_as_update(client, conn, kintone):
    [app_id] = make_verified(conn, 1, ApplicationStatus.NEEDS_REVIEW)
    run(kintone, conn)
    with conn:
        repository.update_status(conn, app_id, ApplicationStatus.VERIFIED)
    summary = run(kintone, conn)
    assert (summary.added, summary.updated) == (0, 1)
    [record] = kintone_records(client)
    assert record["本人確認ステータス"] == "本人確認OK"


def test_more_than_100_records_are_split(client, conn, kintone):
    make_verified(conn, 150)
    summary = run(kintone, conn)
    assert summary.added == 150
    assert len(kintone_records(client)) == 150


def test_recovers_from_previous_partial_failure(client, conn, kintone):
    """前回 kintone への登録だけ成功し、DB への記録前に落ちたケース。二重登録しない。"""
    [app_id] = make_verified(conn, 1)
    row = repository.list_unsynced(conn)[0]
    from batch.sync_to_kintone import to_kintone_record

    kintone.add_records([to_kintone_record(row)])  # 登録だけ済んでいる状態を作る

    summary = run(kintone, conn)
    assert (summary.added, summary.updated) == (0, 1)
    assert len(kintone_records(client)) == 1


def test_retries_temporary_failure(app, client, conn, kintone):
    app.state.mock_kintone.fail_remaining = 2  # 2回 503 を返したあと成功する
    make_verified(conn, 1)
    assert run(kintone, conn).added == 1


def test_gives_up_after_max_attempts(app, client, conn, kintone):
    app.state.mock_kintone.fail_remaining = 10
    make_verified(conn, 1)
    with pytest.raises(KintoneError):
        run(kintone, conn)
    # 失敗したものは未連携のまま残り、次回の実行で再送される
    assert len(repository.list_unsynced(conn)) == 1


def test_card_identity_is_not_sent_to_kintone(client, conn, kintone):
    make_verified(conn, 1)
    run(kintone, conn)
    [record] = kintone_records(client)
    assert set(record) >= {"申込ID", "本人確認ステータス", "照合結果"}
    assert not any(k.startswith("verified_") for k in record)
