"""DB-M1-CORE: M1(14개) + M2(14개) 전 테이블 스키마·RLS·제약·왕복 마이그레이션 및 초기 시드 검증."""

from datetime import date
from uuid import UUID

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from app.seed import seed_reference_data

ALL_28_TABLES = {
    # 0001 (1개)
    "users",
    # 0002 M1 핵심 (13개)
    "user_profiles",
    "user_settings",
    "libraries",
    "books",
    "availability_observations",
    "popular_books_cache",
    "provider_daily_usage",
    "loan_plans",
    "loans",
    "library_return_stats",
    "posts",
    "post_reactions",
    "post_bookmarks",
    # 0003 M2 확장 (14개)
    "reading_logs",
    "guestbook_entries",
    "visit_stamps",
    "shelf_themes",
    "shelf_theme_books",
    "clubs",
    "club_participants",
    "club_comments",
    "club_reviews",
    "feed_bookmarks",
    "user_follows",
    "notifications",
    "moderation_reports",
    "user_penalties",
}

USER_A = UUID("00000000-0000-4000-8000-00000000000a")


def test_all_tables_exist_and_have_rls_without_policies(db_engine: Engine) -> None:
    with db_engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT relname, relrowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND c.relname <> 'alembic_version'
                """
            )
        ).all()
        policy_count = conn.execute(
            text("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'")
        ).scalar_one()

    found_tables = {r.relname for r in rows}
    assert found_tables == ALL_28_TABLES
    for r in rows:
        assert r.relrowsecurity is True, f"{r.relname} 테이블에 RLS가 꺼져 있어요"
    assert policy_count == 0


def test_return_stats_has_no_user_or_loan_columns(db_engine: Engine) -> None:
    """05 §3.2 R15: library_return_stats에는 user_id나 loan_id 컬럼이 없어야 한다."""
    with db_engine.connect() as conn:
        cols = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'library_return_stats'
                    """
                )
            ).all()
        }
    assert cols == {"library_id", "book_id", "returned_on", "return_count"}
    assert "user_id" not in cols
    assert "loan_id" not in cols


def test_core_domain_constraints(db_engine: Engine) -> None:
    with db_engine.begin() as conn:
        conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": USER_A})
        seed_reference_data(conn)
        lib_id = int(
            conn.execute(text("SELECT id FROM libraries LIMIT 1")).scalar_one()
        )
        book_id = int(conn.execute(text("SELECT id FROM books LIMIT 1")).scalar_one())

        # R3: 활성 빌릴 예정(status='planned')은 같은 (user, book, library)에 하나만 허용
        conn.execute(
            text(
                "INSERT INTO loan_plans (user_id, book_id, library_id, status) "
                "VALUES (:u, :b, :l, 'planned')"
            ),
            {"u": USER_A, "b": book_id, "l": lib_id},
        )

    with pytest.raises(IntegrityError):
        with db_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO loan_plans (user_id, book_id, library_id, status) "
                    "VALUES (:u, :b, :l, 'planned')"
                ),
                {"u": USER_A, "b": book_id, "l": lib_id},
            )

    # R4: 반납 예정일(due_on)은 대출일(loaned_on) 이전 불가
    with pytest.raises(IntegrityError):
        with db_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO loans (user_id, book_id, loaned_on, due_on, status) "
                    "VALUES (:u, :b, :loaned, :due, 'on_loan')"
                ),
                {
                    "u": USER_A,
                    "b": book_id,
                    "loaned": date(2026, 11, 15),
                    "due": date(2026, 11, 14),
                },
            )

    # R1: availability_observations 3상태(yes/no/unknown) 외 값 거부
    with pytest.raises(IntegrityError):
        with db_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO availability_observations "
                    "(library_id, book_id, observed_on, holding, loanable) "
                    "VALUES (:l, :b, :d, 'maybe', 'yes')"
                ),
                {"l": lib_id, "b": book_id, "d": date(2026, 11, 16)},
            )


def test_seed_is_idempotent_and_full_migration_round_trip(
    alembic_config: Config, db_engine: Engine
) -> None:
    with db_engine.begin() as conn:
        first = seed_reference_data(conn)
        second = seed_reference_data(conn)
        lib_count = int(
            conn.execute(text("SELECT count(*) FROM libraries")).scalar_one()
        )
        book_count = int(conn.execute(text("SELECT count(*) FROM books")).scalar_one())

    assert first == second == {"libraries": 4, "books": 6}
    assert lib_count == 4
    assert book_count == 6

    # 0003 -> base -> head 전체 왕복 검증
    command.downgrade(alembic_config, "base")
    with db_engine.connect() as conn:
        remaining = conn.execute(
            text(
                """
                SELECT relname FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relkind = 'r'
                  AND c.relname <> 'alembic_version'
                """
            )
        ).all()
    assert remaining == []

    command.upgrade(alembic_config, "head")
    with db_engine.connect() as conn:
        restored = {
            r.relname
            for r in conn.execute(
                text(
                    """
                    SELECT relname FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname = 'public'
                      AND c.relkind = 'r'
                      AND c.relname <> 'alembic_version'
                    """
                )
            ).all()
        }
    assert restored == ALL_28_TABLES
