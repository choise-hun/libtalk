"""AUTH-2·3 내 설정(GET/PATCH /api/v1/me/settings) 및 회원 탈퇴(DELETE /api/v1/me) 검증."""

from datetime import date
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.main import create_app
from app.seed import seed_reference_data
from app.settings import Settings
from tests.conftest import TEST_SUPABASE_URL


def _client(db_url: str, fake_jwks_client: Mock) -> TestClient:
    app = create_app(
        Settings(app_env="test", database_url=db_url, supabase_url=TEST_SUPABASE_URL),
        jwks_client=fake_jwks_client,
    )
    return TestClient(app)


def _auth(make_token: Any, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(sub=sub)}"}


def test_session_creates_default_user_profile(
    test_db_url: str, db_engine: Engine, fake_jwks_client: Mock, make_token: Any
) -> None:
    user_id = uuid4()
    sub = str(user_id)

    with _client(test_db_url, fake_jwks_client) as client:
        res = client.post("/api/v1/auth/session", headers=_auth(make_token, sub))
        assert res.status_code == 200
        assert res.json()["is_new"] is True

    with db_engine.connect() as conn:
        profile = conn.execute(
            text("SELECT nickname FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).one_or_none()
        assert profile is not None
        assert profile.nickname == f"이웃-{sub[:4]}"


def test_me_settings_default_and_patch(
    test_db_url: str, db_engine: Engine, fake_jwks_client: Mock, make_token: Any
) -> None:
    user_id = uuid4()
    sub = str(user_id)

    with _client(test_db_url, fake_jwks_client) as client:
        assert client.post("/api/v1/auth/session", headers=_auth(make_token, sub)).status_code == 200

        # 1. 행이 없을 때 기본값 반환 및 DB 무변경 확인
        get_res = client.get("/api/v1/me/settings", headers=_auth(make_token, sub))
        assert get_res.status_code == 200
        assert get_res.json() == {
            "nearby_radius_km": 3,
            "return_stats_consent": False,
            "return_stats_consent_at": None,
            "updated_at": None,
        }
        with db_engine.connect() as conn:
            count = conn.execute(
                text("SELECT count(*) FROM user_settings WHERE user_id = :uid"),
                {"uid": user_id},
            ).scalar_one()
            assert count == 0

        # 2. 반경 5km + 반납 통계 동의 활성화
        patch_res = client.patch(
            "/api/v1/me/settings",
            headers=_auth(make_token, sub),
            json={"nearby_radius_km": 5, "return_stats_consent": True},
        )
        assert patch_res.status_code == 200
        body = patch_res.json()
        assert body["nearby_radius_km"] == 5
        assert body["return_stats_consent"] is True
        assert isinstance(body["return_stats_consent_at"], str)
        assert body["return_stats_consent_at"].endswith("+09:00")
        first_consent_at = body["return_stats_consent_at"]

        # 3. 반경만 3km로 변경 시 기존 동의 시각 유지
        patch_radius = client.patch(
            "/api/v1/me/settings",
            headers=_auth(make_token, sub),
            json={"nearby_radius_km": 3},
        )
        assert patch_radius.status_code == 200
        assert patch_radius.json()["nearby_radius_km"] == 3
        assert patch_radius.json()["return_stats_consent"] is True
        assert patch_radius.json()["return_stats_consent_at"] == first_consent_at

        # 3-1. 이미 동의한 상태에서 다시 동의해도 처음 동의 시각을 유지(DEF-015)
        with db_engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE user_settings SET return_stats_consent_at = "
                    "'2026-01-02T03:04:05+09:00' WHERE user_id = :uid"
                ),
                {"uid": user_id},
            )
        patch_again = client.patch(
            "/api/v1/me/settings",
            headers=_auth(make_token, sub),
            json={"return_stats_consent": True},
        )
        assert patch_again.status_code == 200
        assert patch_again.json()["return_stats_consent_at"] == "2026-01-02T03:04:05+09:00"

        # 4. 반납 통계 동의 철회 시 consent_at 초기화
        patch_revoke = client.patch(
            "/api/v1/me/settings",
            headers=_auth(make_token, sub),
            json={"return_stats_consent": False},
        )
        assert patch_revoke.status_code == 200
        assert patch_revoke.json()["return_stats_consent"] is False
        assert patch_revoke.json()["return_stats_consent_at"] is None

        # 5. 잘못된 반경(4km) 및 빈 본문은 422 VALIDATION_ERROR
        bad_radius = client.patch(
            "/api/v1/me/settings",
            headers=_auth(make_token, sub),
            json={"nearby_radius_km": 4},
        )
        assert bad_radius.status_code == 422
        assert bad_radius.json()["error"]["code"] == "VALIDATION_ERROR"

        empty_patch = client.patch(
            "/api/v1/me/settings",
            headers=_auth(make_token, sub),
            json={},
        )
        assert empty_patch.status_code == 422
        assert empty_patch.json()["error"]["code"] == "VALIDATION_ERROR"


def test_delete_me_withdraws_and_isolates_other_user(
    test_db_url: str, db_engine: Engine, fake_jwks_client: Mock, make_token: Any
) -> None:
    user_a = uuid4()
    user_b = uuid4()
    sub_a = str(user_a)
    sub_b = str(user_b)

    with db_engine.begin() as conn:
        seed_reference_data(conn)
        lib_id = conn.execute(text("SELECT id FROM libraries LIMIT 1")).scalar_one()
        book_id = conn.execute(text("SELECT id FROM books LIMIT 1")).scalar_one()

    with _client(test_db_url, fake_jwks_client) as client:
        assert client.post("/api/v1/auth/session", headers=_auth(make_token, sub_a)).status_code == 200
        assert client.post("/api/v1/auth/session", headers=_auth(make_token, sub_b)).status_code == 200
        assert (
            client.patch(
                "/api/v1/me/settings",
                headers=_auth(make_token, sub_a),
                json={"nearby_radius_km": 5, "return_stats_consent": True},
            ).status_code
            == 200
        )
        assert (
            client.patch(
                "/api/v1/me/settings",
                headers=_auth(make_token, sub_b),
                json={"nearby_radius_km": 5},
            ).status_code
            == 200
        )

    plan_a = uuid4()
    plan_b = uuid4()
    loan_a = uuid4()
    loan_b = uuid4()
    post_a = uuid4()
    post_b = uuid4()
    gb_a = uuid4()
    gb_b = uuid4()

    with db_engine.begin() as conn:
        for uid, plan_id, loan_id, post_id, gb_id in (
            (user_a, plan_a, loan_a, post_a, gb_a),
            (user_b, plan_b, loan_b, post_b, gb_b),
        ):
            conn.execute(
                text(
                    """
                    INSERT INTO loan_plans (id, user_id, library_id, book_id, status)
                    VALUES (:id, :uid, :lib_id, :book_id, 'planned')
                    """
                ),
                {"id": plan_id, "uid": uid, "lib_id": lib_id, "book_id": book_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO loans (
                        id, user_id, library_id, book_id, plan_id,
                        loaned_on, due_on, status
                    )
                    VALUES (:id, :uid, :lib_id, :book_id, :plan_id, :loaned_on, :due_on, 'on_loan')
                    """
                ),
                {
                    "id": loan_id,
                    "uid": uid,
                    "lib_id": lib_id,
                    "book_id": book_id,
                    "plan_id": plan_id,
                    "loaned_on": date(2026, 4, 1),
                    "due_on": date(2026, 4, 15),
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO reading_logs (
                        id, user_id, library_id, book_id, read_on, content
                    )
                    VALUES (:id, :uid, :lib_id, :book_id, :read_on, '메모')
                    """
                ),
                {
                    "id": uuid4(),
                    "uid": uid,
                    "lib_id": lib_id,
                    "book_id": book_id,
                    "read_on": date(2026, 4, 2),
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO visit_stamps (
                        id, user_id, library_id, visited_on, is_public
                    )
                    VALUES (:id, :uid, :lib_id, :visited_on, true)
                    """
                ),
                {
                    "id": uuid4(),
                    "uid": uid,
                    "lib_id": lib_id,
                    "visited_on": date(2026, 4, 2),
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO posts (
                        id, user_id, library_id, book_id, body,
                        image_kind, image_value, status
                    )
                    VALUES (:id, :uid, :lib_id, :book_id, '글 본문', 'color', 'forest', 'published')
                    """
                ),
                {"id": post_id, "uid": uid, "lib_id": lib_id, "book_id": book_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO guestbook_entries (
                        id, user_id, library_id, content, status
                    )
                    VALUES (:id, :uid, :lib_id, '방명록 한 줄', 'published')
                    """
                ),
                {"id": gb_id, "uid": uid, "lib_id": lib_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO post_bookmarks (user_id, post_id)
                    VALUES (:uid, :post_id)
                    """
                ),
                {"uid": uid, "post_id": post_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO post_reactions (post_id, user_id)
                    VALUES (:post_id, :uid)
                    """
                ),
                {"uid": uid, "post_id": post_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO feed_bookmarks (
                        user_id, target_type, target_id, library_id
                    )
                    VALUES (:uid, 'post', :target_id, :lib_id)
                    """
                ),
                {"uid": uid, "target_id": post_id, "lib_id": lib_id},
            )
            conn.execute(
                text(
                    """
                    INSERT INTO notifications (
                        id, user_id, kind, title, body
                    )
                    VALUES (:id, :uid, 'club_confirmed', '알림', '내용')
                    """
                ),
                {"id": uuid4(), "uid": uid},
            )

        conn.execute(
            text(
                """
                INSERT INTO user_follows (follower_id, followee_id)
                VALUES (:a, :b)
                """
            ),
            {"a": user_a, "b": user_b},
        )
        # 나를 건 팔로우도 지워져야 한다(DEF-015: 한쪽 방향만 지우는 변형이 통과하던 빈틈)
        conn.execute(
            text("INSERT INTO user_follows (follower_id, followee_id) VALUES (:b, :a)"),
            {"a": user_a, "b": user_b},
        )
        conn.execute(
            text("UPDATE user_profiles SET bio = '소개', avatar_url = 'a.png' WHERE user_id = :a"),
            {"a": user_a},
        )

    with _client(test_db_url, fake_jwks_client) as client:
        del_res = client.delete("/api/v1/me", headers=_auth(make_token, sub_a))
        assert del_res.status_code == 200
        del_body = del_res.json()
        assert del_body["user_id"] == sub_a
        assert del_body["status"] == "withdrawn"
        assert del_body["withdrawn_at"].endswith("+09:00")

        # 탈퇴한 계정 A로 재호출 시 모든 인증 경로에서 403 ACCOUNT_WITHDRAWN
        for method, path in (
            ("GET", "/api/v1/me"),
            ("GET", "/api/v1/me/settings"),
            ("DELETE", "/api/v1/me"),
            ("POST", "/api/v1/auth/session"),
        ):
            r = client.request(method, path, headers=_auth(make_token, sub_a))
            assert r.status_code == 403
            assert r.json()["error"]["code"] == "ACCOUNT_WITHDRAWN"

        # 사용자 B는 정상 이용 가능
        me_b = client.get("/api/v1/me", headers=_auth(make_token, sub_b))
        assert me_b.status_code == 200
        assert me_b.json()["status"] == "active"

    with db_engine.connect() as conn:
        # A의 개인 데이터는 즉시 0건
        for table in (
            "loans",
            "loan_plans",
            "reading_logs",
            "visit_stamps",
            "post_bookmarks",
            "post_reactions",
            "feed_bookmarks",
            "notifications",
            "user_settings",
        ):
            cnt_a = conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE user_id = :uid"),
                {"uid": user_a},
            ).scalar_one()
            assert cnt_a == 0, f"{table} rows for withdrawn user A not deleted"

            cnt_b = conn.execute(
                text(f"SELECT count(*) FROM {table} WHERE user_id = :uid"),
                {"uid": user_b},
            ).scalar_one()
            assert cnt_b == 1, f"{table} rows for active user B affected"

        follow_cnt = conn.execute(
            text(
                "SELECT count(*) FROM user_follows WHERE follower_id = :uid OR followee_id = :uid"
            ),
            {"uid": user_a},
        ).scalar_one()
        assert follow_cnt == 0

        # 프로필 익명화(05 §11.1): A만 바뀌고 B는 그대로
        profile_a = conn.execute(
            text("SELECT nickname, bio, avatar_url FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_a},
        ).one()
        assert tuple(profile_a) == ("탈퇴한 이웃", None, None)
        nickname_b = conn.execute(
            text("SELECT nickname FROM user_profiles WHERE user_id = :uid"), {"uid": user_b}
        ).scalar_one()
        assert nickname_b == f"이웃-{sub_b[:4]}"

        # A의 공개 게시물과 방명록은 비노출 상태로 전환, B는 published 유지
        status_post_a = conn.execute(
            text("SELECT status FROM posts WHERE id = :id"), {"id": post_a}
        ).scalar_one()
        status_post_b = conn.execute(
            text("SELECT status FROM posts WHERE id = :id"), {"id": post_b}
        ).scalar_one()
        assert status_post_a == "withdrawn"
        assert status_post_b == "published"

        status_gb_a = conn.execute(
            text("SELECT status FROM guestbook_entries WHERE id = :id"), {"id": gb_a}
        ).scalar_one()
        status_gb_b = conn.execute(
            text("SELECT status FROM guestbook_entries WHERE id = :id"), {"id": gb_b}
        ).scalar_one()
        assert status_gb_a == "deleted"
        assert status_gb_b == "published"
