"""내 설정·탈퇴의 동시성 회귀 시험(Phase 1 리뷰 DEF-013·DEF-014)."""

import threading
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.common import ApiError
from app.main import create_app
from app.routers import me as me_mod
from app.settings import Settings
from tests.conftest import TEST_SUPABASE_URL


def _register(db_url: str, jwks: Mock, make_token: Any) -> UUID:
    sub = str(uuid4())
    app = create_app(
        Settings(app_env="test", database_url=db_url, supabase_url=TEST_SUPABASE_URL),
        jwks_client=jwks,
    )
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/auth/session", headers={"Authorization": f"Bearer {make_token(sub=sub)}"}
        )
        assert res.status_code == 200
    return UUID(sub)


class _PauseAfterFirstExecute:
    """첫 SQL을 실행한 직후 멈춰 다른 트랜잭션이 끼어들 틈을 만든다."""

    def __init__(self, conn: Connection, paused: threading.Event, release: threading.Event):
        self._conn, self._paused, self._release, self._calls = conn, paused, release, 0

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        result = self._conn.execute(*args, **kwargs)
        self._calls += 1
        if self._calls == 1:
            self._paused.set()
            assert self._release.wait(5)
        return result


def test_patch_settings_concurrent_fields_do_not_overwrite_each_other(
    test_db_url: str, db_engine: Engine, fake_jwks_client: Mock, make_token: Any
) -> None:
    uid = _register(test_db_url, fake_jwks_client, make_token)
    paused, release = threading.Event(), threading.Event()
    errors: list[BaseException] = []

    def consent_request() -> None:
        try:
            with db_engine.begin() as conn:
                me_mod.upsert_user_settings(
                    _PauseAfterFirstExecute(conn, paused, release),  # type: ignore[arg-type]
                    uid, None, True,
                )
        except BaseException as exc:  # 스레드 예외를 본 시험으로 넘긴다
            errors.append(exc)

    worker = threading.Thread(target=consent_request)
    worker.start()
    assert paused.wait(5)
    with db_engine.begin() as conn:
        me_mod.upsert_user_settings(conn, uid, 5, None)
    release.set()
    worker.join(10)
    assert not errors

    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT nearby_radius_km, return_stats_consent_at "
                "FROM user_settings WHERE user_id = :uid"
            ),
            {"uid": uid},
        ).one()
    assert row.nearby_radius_km == 5
    assert row.return_stats_consent_at is not None


def test_write_waiting_on_withdrawal_is_rejected_and_leaves_no_rows(
    test_db_url: str, db_engine: Engine, fake_jwks_client: Mock, make_token: Any
) -> None:
    """get_current_user는 통과했지만 쓰기 직전에 탈퇴가 진행 중이면, 탈퇴 커밋 뒤 403으로 거부된다."""
    uid = _register(test_db_url, fake_jwks_client, make_token)
    outcome: list[Any] = []

    def patch_request() -> None:
        try:
            with db_engine.begin() as conn:
                outcome.append(me_mod.upsert_user_settings(conn, uid, 5, True))
        except ApiError as exc:
            outcome.append(exc)

    withdraw_conn = db_engine.connect()
    try:
        tx = withdraw_conn.begin()
        me_mod.withdraw_user_account(withdraw_conn, uid)  # 아직 커밋 전: users 행을 잠그고 있다
        worker = threading.Thread(target=patch_request, daemon=True)
        worker.start()
        worker.join(0.5)
        waited = worker.is_alive()
        tx.commit()
    finally:
        withdraw_conn.close()  # 실패해도 잠금을 풀어 다음 시험의 TRUNCATE가 멈추지 않게 한다
    worker.join(10)
    assert waited, "쓰기 트랜잭션이 탈퇴 잠금을 기다리지 않았다"

    assert len(outcome) == 1 and isinstance(outcome[0], ApiError)
    assert (outcome[0].status_code, outcome[0].code) == (403, "ACCOUNT_WITHDRAWN")
    with db_engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM user_settings WHERE user_id = :uid"), {"uid": uid}
        ).scalar_one()
    assert count == 0


def test_second_withdrawal_in_flight_is_rejected(
    test_db_url: str, db_engine: Engine, fake_jwks_client: Mock, make_token: Any
) -> None:
    uid = _register(test_db_url, fake_jwks_client, make_token)
    with db_engine.begin() as conn:
        me_mod.withdraw_user_account(conn, uid)
    with db_engine.begin() as conn:
        try:
            me_mod.withdraw_user_account(conn, uid)
        except ApiError as exc:
            assert (exc.status_code, exc.code) == (403, "ACCOUNT_WITHDRAWN")
        else:
            raise AssertionError("두 번째 탈퇴가 거부되지 않았다")
