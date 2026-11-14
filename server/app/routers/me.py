"""내 설정 조회·변경(GET/PATCH /api/v1/me/settings) 및 회원 탈퇴(DELETE /api/v1/me)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.auth import (
    MSG_WITHDRAWN,
    CurrentUser,
    get_current_user,
    lock_active_user,
)
from app.common import ApiError, now_kst
from app.db import run_db

router = APIRouter()

DEFAULT_NEARBY_RADIUS_KM = 3
ALLOWED_RADIUS_KM = (3, 5)
WITHDRAWN_NICKNAME = "탈퇴한 이웃"


class SettingsPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nearby_radius_km: StrictInt | None = None
    return_stats_consent: StrictBool | None = None


def _format_kst_or_none(value: datetime | None) -> str | None:
    if value is None:
        return None
    return now_kst(value).isoformat(timespec="seconds")


def select_user_settings(conn: Connection, user_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        text(
            """
            SELECT nearby_radius_km, return_stats_consent_at, updated_at
            FROM user_settings
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).one_or_none()
    if row is None:
        return {
            "nearby_radius_km": DEFAULT_NEARBY_RADIUS_KM,
            "return_stats_consent": False,
            "return_stats_consent_at": None,
            "updated_at": None,
        }
    return {
        "nearby_radius_km": int(row.nearby_radius_km),
        "return_stats_consent": row.return_stats_consent_at is not None,
        "return_stats_consent_at": _format_kst_or_none(row.return_stats_consent_at),
        "updated_at": _format_kst_or_none(row.updated_at),
    }


def upsert_user_settings(
    conn: Connection,
    user_id: UUID,
    nearby_radius_km: int | None,
    return_stats_consent: bool | None,
) -> dict[str, Any]:
    lock_active_user(conn, user_id)
    # DEF-013: 읽고-고쳐-쓰기를 하지 않는다. 보내지 않은 칸은 ON CONFLICT 갱신 시점의
    # 최신 행 값(user_settings.*)을 그대로 두어, 동시에 다른 칸을 바꾼 요청을 덮지 않는다.
    row = conn.execute(
        text(
            """
            INSERT INTO user_settings (
                user_id, nearby_radius_km, return_stats_consent_at, updated_at
            )
            VALUES (
                :user_id,
                COALESCE(CAST(:radius AS integer), :default_radius),
                CASE WHEN CAST(:consent AS boolean) THEN CAST(:now AS timestamptz) END,
                CAST(:now AS timestamptz)
            )
            ON CONFLICT (user_id) DO UPDATE SET
                nearby_radius_km = COALESCE(
                    CAST(:radius AS integer), user_settings.nearby_radius_km
                ),
                return_stats_consent_at = CASE
                    WHEN CAST(:consent AS boolean) IS NULL
                        THEN user_settings.return_stats_consent_at
                    WHEN CAST(:consent AS boolean)
                        THEN COALESCE(
                            user_settings.return_stats_consent_at, CAST(:now AS timestamptz)
                        )
                    ELSE NULL
                END,
                updated_at = CAST(:now AS timestamptz)
            RETURNING nearby_radius_km, return_stats_consent_at, updated_at
            """
        ),
        {
            "user_id": user_id,
            "radius": nearby_radius_km,
            "default_radius": DEFAULT_NEARBY_RADIUS_KM,
            "consent": return_stats_consent,
            "now": now_kst(),
        },
    ).one()

    return {
        "nearby_radius_km": int(row.nearby_radius_km),
        "return_stats_consent": row.return_stats_consent_at is not None,
        "return_stats_consent_at": _format_kst_or_none(row.return_stats_consent_at),
        "updated_at": _format_kst_or_none(row.updated_at),
    }


def withdraw_user_account(conn: Connection, user_id: UUID) -> dict[str, Any]:
    now = now_kst()

    # 0. 계정 상태를 먼저 바꿔 users 행을 잠근다(DEF-014). 동시에 들어온 쓰기(lock_active_user)는
    #    이 커밋을 기다린 뒤 탈퇴 상태를 보고 거부되고, 두 번째 탈퇴 요청도 여기서 403이 된다.
    withdrawn = conn.execute(
        text(
            """
            UPDATE users
            SET status = 'withdrawn'
            WHERE id = :user_id AND status = 'active'
            RETURNING id
            """
        ),
        {"user_id": user_id},
    ).one_or_none()
    if withdrawn is None:
        raise ApiError(403, "ACCOUNT_WITHDRAWN", MSG_WITHDRAWN)

    # 1. 공개 콘텐츠 비노출 상태 전환 (Q-23, AC-DELETE)
    conn.execute(
        text(
            """
            UPDATE posts
            SET status = 'withdrawn', updated_at = :now
            WHERE user_id = :user_id AND status != 'withdrawn'
            """
        ),
        {"user_id": user_id, "now": now},
    )
    conn.execute(
        text(
            """
            UPDATE guestbook_entries
            SET status = 'deleted'
            WHERE user_id = :user_id AND status != 'deleted'
            """
        ),
        {"user_id": user_id},
    )

    # 2. 개인 전용 데이터 즉시 삭제 (loans -> loan_plans 순서 준수)
    for table_sql in (
        "DELETE FROM loans WHERE user_id = :user_id",
        "DELETE FROM loan_plans WHERE user_id = :user_id",
        "DELETE FROM reading_logs WHERE user_id = :user_id",
        "DELETE FROM visit_stamps WHERE user_id = :user_id",
        "DELETE FROM post_bookmarks WHERE user_id = :user_id",
        "DELETE FROM post_reactions WHERE user_id = :user_id",
        "DELETE FROM feed_bookmarks WHERE user_id = :user_id",
        "DELETE FROM notifications WHERE user_id = :user_id",
        "DELETE FROM user_follows WHERE follower_id = :user_id OR followee_id = :user_id",
        "DELETE FROM user_settings WHERE user_id = :user_id",
    ):
        conn.execute(text(table_sql), {"user_id": user_id})

    # 3. 프로필 익명화(계정 상태는 0에서 이미 바꿨다)
    conn.execute(
        text(
            """
            UPDATE user_profiles
            SET nickname = :nickname, bio = NULL, avatar_url = NULL, updated_at = :now
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id, "nickname": WITHDRAWN_NICKNAME, "now": now},
    )

    return {
        "user_id": str(user_id),
        "status": "withdrawn",
        "withdrawn_at": now.isoformat(timespec="seconds"),
    }


@router.get("/api/v1/me/settings")
async def get_my_settings(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict[str, Any]:
    return await run_db(
        request.app.state.engine,
        lambda c: select_user_settings(c, user.id),
    )


@router.patch("/api/v1/me/settings")
async def patch_my_settings(
    payload: SettingsPatchRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    if payload.nearby_radius_km is None and payload.return_stats_consent is None:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "요청 형식이 올바르지 않아요.",
            "nearby_radius_km,return_stats_consent",
        )
    if (
        payload.nearby_radius_km is not None
        and payload.nearby_radius_km not in ALLOWED_RADIUS_KM
    ):
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "요청 형식이 올바르지 않아요.",
            "nearby_radius_km",
        )
    return await run_db(
        request.app.state.engine,
        lambda c: upsert_user_settings(
            c,
            user.id,
            payload.nearby_radius_km,
            payload.return_stats_consent,
        ),
    )


@router.delete("/api/v1/me")
async def delete_me(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict[str, Any]:
    return await run_db(
        request.app.state.engine,
        lambda c: withdraw_user_account(c, user.id),
    )
