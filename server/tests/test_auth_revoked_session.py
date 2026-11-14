"""DEF-008: 로그아웃·철회된 Supabase 세션의 토큰 거부(AUTH-02, AC-AUTH)."""

from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.main import create_app
from app.settings import Settings
from tests.conftest import TEST_SUPABASE_URL


@pytest.fixture
def auth_sessions(db_engine: Engine) -> Iterator[None]:
    """시험 DB에는 Supabase auth 스키마가 없어 auth.sessions의 필요한 칸만 대역으로 만든다."""
    with db_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS auth"))
        conn.execute(
            text("CREATE TABLE auth.sessions (id uuid PRIMARY KEY, user_id uuid NOT NULL)")
        )
    try:
        yield
    finally:
        with db_engine.begin() as conn:
            conn.execute(text("DROP SCHEMA auth CASCADE"))


def _client(db_url: str, jwks: Mock, check: bool = True) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                app_env="test", database_url=db_url, supabase_url=TEST_SUPABASE_URL,
                auth_session_check=check,
            ),
            jwks_client=jwks,
        )
    )


def _h(make_token: Any, sub: str, session_id: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=sub, session_id=session_id)}"}


def _add_session(engine: Engine, sid: UUID, uid: UUID) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO auth.sessions (id, user_id) VALUES (:s, :u)"), {"s": sid, "u": uid}
        )


def test_signed_out_session_is_rejected_for_reads_and_writes(
    auth_sessions: None, test_db_url: str, db_engine: Engine,
    fake_jwks_client: Mock, make_token: Any,
) -> None:
    uid, sid = uuid4(), uuid4()
    _add_session(db_engine, sid, uid)
    headers = _h(make_token, str(uid), str(sid))
    with _client(test_db_url, fake_jwks_client) as client:
        assert client.post("/api/v1/auth/session", headers=headers).status_code == 200
        assert client.get("/api/v1/me", headers=headers).status_code == 200
        assert client.patch(
            "/api/v1/me/settings", headers=headers, json={"nearby_radius_km": 5}
        ).status_code == 200

        # Supabase signOut()은 auth.sessions 행을 지운다
        with db_engine.begin() as conn:
            conn.execute(text("DELETE FROM auth.sessions WHERE id = :s"), {"s": sid})

        for method, path, body in (
            ("GET", "/api/v1/me", None),
            ("GET", "/api/v1/me/settings", None),
            ("PATCH", "/api/v1/me/settings", {"nearby_radius_km": 3}),
            ("DELETE", "/api/v1/me", None),
        ):
            res = client.request(method, path, headers=headers, json=body)
            assert res.status_code == 401, (method, path)
            assert res.json()["error"]["code"] == "AUTH_INVALID"

    with db_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT u.status, s.nearby_radius_km FROM users u "
                "JOIN user_settings s ON s.user_id = u.id WHERE u.id = :u"
            ),
            {"u": uid},
        ).one()
    assert (row.status, row.nearby_radius_km) == ("active", 5)


@pytest.mark.parametrize("session_id", [None, "session-a", 7])
def test_token_without_valid_session_id_is_rejected(
    auth_sessions: None, test_db_url: str, db_engine: Engine,
    fake_jwks_client: Mock, make_token: Any, session_id: Any,
) -> None:
    uid = uuid4()
    with _client(test_db_url, fake_jwks_client) as client:
        assert client.post(
            "/api/v1/auth/session", headers=_h(make_token, str(uid), str(uuid4()))
        ).status_code == 200
        res = client.get("/api/v1/me", headers=_h(make_token, str(uid), session_id))
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_INVALID"


def test_other_users_session_id_is_rejected(
    auth_sessions: None, test_db_url: str, db_engine: Engine,
    fake_jwks_client: Mock, make_token: Any,
) -> None:
    uid_a, uid_b, sid_b = uuid4(), uuid4(), uuid4()
    _add_session(db_engine, sid_b, uid_b)
    with _client(test_db_url, fake_jwks_client) as client:
        assert client.post(
            "/api/v1/auth/session", headers=_h(make_token, str(uid_a), str(sid_b))
        ).status_code == 200
        res = client.get("/api/v1/me", headers=_h(make_token, str(uid_a), str(sid_b)))
    assert res.status_code == 401


def test_check_disabled_does_not_touch_auth_schema(
    test_db_url: str, fake_jwks_client: Mock, make_token: Any
) -> None:
    uid = uuid4()
    with _client(test_db_url, fake_jwks_client, check=False) as client:
        headers = _h(make_token, str(uid), "session-a")
        assert client.post("/api/v1/auth/session", headers=headers).status_code == 200
        assert client.get("/api/v1/me", headers=headers).status_code == 200


def test_production_requires_session_check() -> None:
    with pytest.raises(ValidationError, match="AUTH_SESSION_CHECK"):
        Settings(
            app_env="production", database_url="postgresql+psycopg://u@db.example/x",
            supabase_url=TEST_SUPABASE_URL, auth_session_check=False,
        )
    Settings(
        app_env="production", database_url="postgresql+psycopg://u@db.example/x",
        supabase_url=TEST_SUPABASE_URL, auth_session_check=True,
    )
