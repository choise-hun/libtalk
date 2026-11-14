"""M2 확장 컬럼 및 신규 테이블 14종(15~28번) 생성, 전 테이블 RLS 활성화.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

M2_TABLES = (
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
)


def upgrade() -> None:
    # 10.1 기존 M1 테이블의 M2 확장 컬럼
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
    )
    op.create_check_constraint(
        "users_role_check",
        "users",
        "role IN ('user', 'admin')",
    )

    op.add_column("user_profiles", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("avatar_url", sa.Text(), nullable=True))
    op.create_check_constraint(
        "user_profiles_bio_len_check",
        "user_profiles",
        "bio IS NULL OR char_length(bio) <= 150",
    )

    op.add_column(
        "libraries",
        sa.Column(
            "look_preset",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'warm'"),
        ),
    )
    op.add_column(
        "libraries",
        sa.Column(
            "look_is_manual",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_check_constraint(
        "libraries_look_preset_check",
        "libraries",
        "look_preset IN ('warm', 'toffee', 'oxford', 'modern')",
    )

    # 15. reading_logs
    op.create_table(
        "reading_logs",
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
            "loan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("loans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("read_on", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
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
    )

    # posts M2 확장 컬럼 (reading_logs 생성 이후 FK 연결)
    op.add_column("posts", sa.Column("template_key", sa.Text(), nullable=True))
    op.add_column(
        "posts",
        sa.Column(
            "reading_log_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reading_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "posts",
        sa.Column(
            "like_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_check_constraint(
        "posts_template_key_check",
        "posts",
        "template_key IS NULL OR template_key IN ('minimal', 'ink', 'warm_memo', 'classic')",
    )
    op.create_check_constraint(
        "posts_like_count_check",
        "posts",
        "like_count >= 0",
    )

    # 16. guestbook_entries
    op.create_table(
        "guestbook_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'published'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "char_length(content) BETWEEN 1 AND 300",
            name="guestbook_entries_content_len_check",
        ),
        sa.CheckConstraint(
            "status IN ('published', 'deleted', 'hidden')",
            name="guestbook_entries_status_check",
        ),
    )

    # 17. visit_stamps
    op.create_table(
        "visit_stamps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("visited_on", sa.Date(), nullable=False),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id",
            "library_id",
            "visited_on",
            name="uq_visit_stamps_user_library_day",
        ),
    )

    # 18. shelf_themes
    op.create_table(
        "shelf_themes",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "ends_on >= starts_on",
            name="shelf_themes_date_order_check",
        ),
    )

    # 19. shelf_theme_books
    op.create_table(
        "shelf_theme_books",
        sa.Column(
            "theme_id",
            sa.BigInteger(),
            sa.ForeignKey("shelf_themes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=False,
        ),
        sa.Column(
            "sort_order",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.PrimaryKeyConstraint("theme_id", "book_id"),
    )

    # 20. clubs
    op.create_table(
        "clubs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "creator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.BigInteger(),
            sa.ForeignKey("books.id"),
            nullable=True,
        ),
        sa.Column(
            "parent_club_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clubs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("place_text", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capacity", sa.SmallInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "capacity IS NULL OR capacity >= 2",
            name="clubs_capacity_check",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed', 'cancelled', 'completed')",
            name="clubs_status_check",
        ),
    )

    # 21. club_participants
    op.create_table(
        "club_participants",
        sa.Column(
            "club_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clubs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'registered'"),
        ),
        sa.Column("self_attended", sa.Boolean(), nullable=True),
        sa.Column(
            "host_attendance",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "joined_at",
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
        sa.PrimaryKeyConstraint("club_id", "user_id"),
        sa.CheckConstraint(
            "status IN ('registered', 'cancelled', 'excluded')",
            name="club_participants_status_check",
        ),
        sa.CheckConstraint(
            "host_attendance IN ('pending', 'attended', 'no_show')",
            name="club_participants_host_attendance_check",
        ),
    )

    # 22. club_comments
    op.create_table(
        "club_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "club_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clubs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'visible'"),
        ),
        sa.Column(
            "delete_requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("delete_request_reason", sa.Text(), nullable=True),
        sa.Column("delete_request_status", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('visible', 'deleted_by_author', 'hidden_by_admin')",
            name="club_comments_status_check",
        ),
        sa.CheckConstraint(
            "delete_request_status IS NULL OR delete_request_status IN "
            "('pending', 'approved_delete', 'approved_restrict', 'rejected')",
            name="club_comments_delete_req_status_check",
        ),
    )

    # 23. club_reviews
    op.create_table(
        "club_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "club_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clubs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "shared_post_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("posts.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.UniqueConstraint("club_id", "user_id", name="uq_club_reviews_club_user"),
    )

    # 24. feed_bookmarks
    op.create_table(
        "feed_bookmarks",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "library_id",
            sa.BigInteger(),
            sa.ForeignKey("libraries.id"),
            nullable=False,
        ),
        sa.Column(
            "saved_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "target_type", "target_id"),
        sa.CheckConstraint(
            "target_type IN ('post', 'guestbook', 'club', 'stamp')",
            name="feed_bookmarks_target_type_check",
        ),
    )

    # 25. user_follows
    op.create_table(
        "user_follows",
        sa.Column(
            "follower_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "followee_id",
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
        sa.PrimaryKeyConstraint("follower_id", "followee_id"),
        sa.CheckConstraint(
            "follower_id <> followee_id",
            name="user_follows_no_self_check",
        ),
    )

    # 26. notifications
    op.create_table(
        "notifications",
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
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('club_confirmed', 'club_changed', 'club_cancelled', "
            "'club_ended', 'club_next', 'moderation', 'penalty')",
            name="notifications_kind_check",
        ),
    )

    # 27. moderation_reports
    op.create_table(
        "moderation_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "reporter_id",
            "target_type",
            "target_id",
            name="uq_moderation_reports_reporter_target",
        ),
        sa.CheckConstraint(
            "target_type IN ('post', 'guestbook', 'club', 'club_comment')",
            name="moderation_reports_target_type_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'hidden', 'dismissed')",
            name="moderation_reports_status_check",
        ),
    )

    # 28. user_penalties
    op.create_table(
        "user_penalties",
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
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "strike_count",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "club_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clubs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "starts_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_permanent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("appeal_text", sa.Text(), nullable=True),
        sa.Column("appeal_status", sa.Text(), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.CheckConstraint(
            "kind IN ('no_show', 'comment_abuse')",
            name="user_penalties_kind_check",
        ),
        sa.CheckConstraint(
            "appeal_status IS NULL OR appeal_status IN ('pending', 'released', 'rejected')",
            name="user_penalties_appeal_status_check",
        ),
    )

    for table_name in M2_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_constraint("posts_like_count_check", "posts", type_="check")
    op.drop_constraint("posts_template_key_check", "posts", type_="check")
    op.drop_column("posts", "like_count")
    op.drop_column("posts", "reading_log_id")
    op.drop_column("posts", "template_key")

    for table_name in reversed(M2_TABLES):
        op.drop_table(table_name)

    op.drop_constraint("libraries_look_preset_check", "libraries", type_="check")
    op.drop_column("libraries", "look_is_manual")
    op.drop_column("libraries", "look_preset")

    op.drop_constraint("user_profiles_bio_len_check", "user_profiles", type_="check")
    op.drop_column("user_profiles", "avatar_url")
    op.drop_column("user_profiles", "bio")

    op.drop_constraint("users_role_check", "users", type_="check")
    op.drop_column("users", "role")
