"""M1 핵심 테이블 13종 생성, 제약·인덱스 및 전 테이블 RLS 활성화.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

M1_TABLES = (
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
)


def upgrade() -> None:
    # 2. user_profiles
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("nickname", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(nickname)) BETWEEN 1 AND 40",
            name="user_profiles_nickname_len_check",
        ),
    )

    # 3. user_settings
    op.create_table(
        "user_settings",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "nearby_radius_km",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("3"),
        ),
        sa.Column("return_stats_consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "nearby_radius_km IN (3, 5)",
            name="user_settings_nearby_radius_check",
        ),
    )

    # 4. libraries
    op.create_table(
        "libraries",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("provider_lib_code", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("tel", sa.Text(), nullable=True),
        sa.Column("homepage", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("closed_text", sa.Text(), nullable=True),
        sa.Column("operating_time_text", sa.Text(), nullable=True),
        sa.Column("region_code", sa.Text(), nullable=True),
        sa.Column("dtl_region_code", sa.Text(), nullable=True),
        sa.Column("isbn_search_url_template", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name="libraries_coords_pair_check",
        ),
    )
    op.create_index("ix_libraries_dtl_region_code", "libraries", ["dtl_region_code"])

    # 5. books
    op.create_table(
        "books",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("isbn13", sa.Text(), nullable=True, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            r"isbn13 IS NULL OR isbn13 ~ '^[0-9]{13}$'",
            name="books_isbn13_format_check",
        ),
        sa.CheckConstraint(
            "source IN ('naver', 'data4library', 'manual')",
            name="books_source_check",
        ),
    )

    # 6. availability_observations
    op.create_table(
        "availability_observations",
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("holding", sa.Text(), nullable=False),
        sa.Column("loanable", sa.Text(), nullable=False),
        sa.Column("data_date", sa.Date(), nullable=True),
        sa.Column(
            "data_date_assumed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "source",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'data4library'"),
        ),
        sa.PrimaryKeyConstraint("library_id", "book_id", "observed_on"),
        sa.CheckConstraint(
            "holding IN ('yes', 'no', 'unknown')",
            name="availability_observations_holding_check",
        ),
        sa.CheckConstraint(
            "loanable IN ('yes', 'no', 'unknown')",
            name="availability_observations_loanable_check",
        ),
    )

    # 7. popular_books_cache
    op.create_table(
        "popular_books_cache",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=True,
        ),
        sa.Column("rank", sa.SmallInteger(), nullable=False),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column("period_label", sa.Text(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "scope IN ('national', 'library')",
            name="popular_books_cache_scope_check",
        ),
        sa.CheckConstraint(
            "(scope = 'library') = (library_id IS NOT NULL)",
            name="popular_books_cache_scope_library_check",
        ),
        sa.CheckConstraint("rank >= 1", name="popular_books_cache_rank_check"),
    )
    op.create_index(
        "uq_popular_books_national_rank",
        "popular_books_cache",
        ["rank"],
        unique=True,
        postgresql_where=sa.text("scope = 'national'"),
    )
    op.create_index(
        "uq_popular_books_library_rank",
        "popular_books_cache",
        ["library_id", "rank"],
        unique=True,
        postgresql_where=sa.text("scope = 'library'"),
    )

    # 8. provider_daily_usage
    op.create_table(
        "provider_daily_usage",
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column(
            "call_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.PrimaryKeyConstraint("provider", "usage_date"),
        sa.CheckConstraint(
            "provider IN ('data4library', 'naver', 'yes24', 'kakao')",
            name="provider_daily_usage_provider_check",
        ),
        sa.CheckConstraint(
            "call_count >= 0",
            name="provider_daily_usage_call_count_check",
        ),
    )

    # 9. loan_plans
    op.create_table(
        "loan_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'planned'"),
        ),
        sa.Column("memo", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'released', 'converted')",
            name="loan_plans_status_check",
        ),
    )
    op.create_index(
        "uq_loan_plans_active",
        "loan_plans",
        ["user_id", "book_id", "library_id"],
        unique=True,
        postgresql_where=sa.text("status = 'planned'"),
    )
    op.create_index("ix_loan_plans_user_status", "loan_plans", ["user_id", "status"])

    # 10. loans
    op.create_table(
        "loans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=True,
        ),
        sa.Column(
            "plan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loan_plans.id"),
            nullable=True,
            unique=True,
        ),
        sa.Column("loaned_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column(
            "due_on_assumed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'on_loan'"),
        ),
        sa.Column("returned_on", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('on_loan', 'returned')",
            name="loans_status_check",
        ),
        sa.CheckConstraint(
            "due_on >= loaned_on",
            name="loans_due_after_loaned_check",
        ),
        sa.CheckConstraint(
            "(status = 'returned') = (returned_on IS NOT NULL)",
            name="loans_returned_on_match_check",
        ),
    )
    op.create_index(
        "uq_loans_user_book_on_loan",
        "loans",
        ["user_id", "book_id"],
        unique=True,
        postgresql_where=sa.text("status = 'on_loan'"),
    )
    op.create_index("ix_loans_user_status", "loans", ["user_id", "status"])

    # 11. library_return_stats (user_id, loan_id 컬럼을 절대 두지 않음 — 05 §3.2 R15)
    op.create_table(
        "library_return_stats",
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column("returned_on", sa.Date(), nullable=False),
        sa.Column(
            "return_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.PrimaryKeyConstraint("library_id", "book_id", "returned_on"),
        sa.CheckConstraint(
            "return_count >= 1",
            name="library_return_stats_count_check",
        ),
    )

    # 12. posts
    op.create_table(
        "posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=True,
        ),
        sa.Column("image_kind", sa.Text(), nullable=False),
        sa.Column("image_value", sa.Text(), nullable=False),
        sa.Column("overlay_text", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'published'"),
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "image_kind IN ('photo', 'cover', 'color')",
            name="posts_image_kind_check",
        ),
        sa.CheckConstraint(
            "char_length(btrim(image_value)) >= 1",
            name="posts_image_value_nonempty_check",
        ),
        sa.CheckConstraint(
            "status IN ('published', 'withdrawn', 'hidden')",
            name="posts_status_check",
        ),
    )
    op.execute(
        "CREATE INDEX ix_posts_library_published "
        "ON posts (library_id, published_at DESC) WHERE status = 'published'"
    )
    op.execute(
        "CREATE INDEX ix_posts_book_published "
        "ON posts (book_id, published_at DESC) WHERE status = 'published'"
    )

    # 13. post_reactions
    op.create_table(
        "post_reactions",
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("post_id", "user_id"),
    )

    # 14. post_bookmarks
    op.create_table(
        "post_bookmarks",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "post_id"),
    )

    for table_name in M1_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table_name in reversed(M1_TABLES):
        op.drop_table(table_name)
