"""도서 검색·상세·추천·소장 조회·구매 링크(06 #7~#9, #12~#15). 인증 없음.

외부 데이터는 조회 엔진(`ProviderEngine`)으로만 얻는다(H-ARCH-07: 이 파일에 HTTP 클라이언트 import 없음).
소장·대출은 yes/no/unknown 세 갈래와 출처·조회 시각·데이터 기준일(추정 여부)을 그대로 준다(H-ARCH-06).
"""

from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app import policy
from app.common import KST, ApiError, now_kst, today_kst
from app.db import run_db
from app.routers.libraries import (
    BIGINT_MAX,
    DTL_REGION_PATTERN,
    MSG_NOT_FOUND,
    check_radius,
    library_summary,
    validation_error,
)
from app.services.provider_engine import (
    AvailabilityItem,
    BookRecord,
    LibraryRow,
    ProviderEngine,
    get_library,
    isbn13_is_valid,
    libraries_in_region,
    libraries_nearby,
    live_check_link,
)

router = APIRouter(prefix="/api/v1/books")


def _engine(request: Request) -> ProviderEngine:
    return request.app.state.provider_engine


def _isbn(isbn13: str) -> str:
    if not isbn13_is_valid(isbn13):
        raise validation_error("isbn13")
    return isbn13


def _iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(KST).isoformat(timespec="seconds")
    return value.isoformat()


async def _library_or_404(request: Request, library_id: int) -> LibraryRow:
    lib = await run_db(request.app.state.engine, lambda c: get_library(c, library_id))
    if lib is None:
        raise ApiError(404, "NOT_FOUND", MSG_NOT_FOUND)
    return lib


# ─────────── #7 검색 ───────────


@router.get("/search")
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1, max_length=policy.SEARCH_QUERY_MAX_CHARS),
    start: int = Query(1, ge=1, le=policy.SEARCH_MAX_START),
) -> Any:
    query = q.strip()
    if not query:
        raise validation_error("q")
    result = await _engine(request).search_books(query, start)
    return {
        "items": [book.public() for book in result.items],
        "next_start": result.next_start,
        "source": result.source,
        "fallback_reason": result.fallback_reason,
    }


# ─────────── #9 검색 진입 추천(02 §9 Q-47: 도서관 테마 → 공통 테마 → 인기 도서) ───────────


def _active_theme(conn: Connection, library_id: int | None, today: date) -> dict[str, Any] | None:
    """범위별로 오늘이 기간 안이고 is_active인 테마 중 starts_on이 가장 늦은 하나. 책이 없으면 None."""
    theme = conn.execute(
        text(
            """
            SELECT id, title, description FROM shelf_themes
            WHERE is_active AND :today BETWEEN starts_on AND ends_on
              AND library_id IS NOT DISTINCT FROM :library_id
            ORDER BY starts_on DESC, id DESC
            LIMIT 1
            """
        ),
        {"today": today, "library_id": library_id},
    ).first()
    if theme is None:
        return None
    books = conn.execute(
        text(
            """
            SELECT b.id, b.isbn13, b.title, b.author, b.publisher, b.cover_url, b.source
            FROM shelf_theme_books t JOIN books b ON b.id = t.book_id
            WHERE t.theme_id = :theme_id AND b.isbn13 IS NOT NULL
            ORDER BY t.sort_order, b.id
            LIMIT :limit
            """
        ),
        {"theme_id": theme.id, "limit": policy.RECOMMENDATION_MAX_BOOKS},
    ).all()
    if not books:
        return None
    return {
        "theme": {"id": int(theme.id), "title": theme.title, "description": theme.description},
        "books": [
            BookRecord(int(r.id), r.isbn13, r.title, r.author, r.publisher, r.cover_url, r.source).public()
            for r in books
        ],
    }


@router.get("/recommendations")
async def recommendations(
    request: Request, library_id: int | None = Query(None, ge=1, le=BIGINT_MAX)
) -> Any:
    library = await _library_or_404(request, library_id) if library_id is not None else None
    today = today_kst()
    scopes: list[tuple[Literal["library", "national"], int | None]] = (
        [("library", library.id), ("national", None)] if library else [("national", None)]
    )
    for scope, theme_library_id in scopes:
        found = await run_db(request.app.state.engine, lambda c: _active_theme(c, theme_library_id, today))
        if found is not None:
            return {
                "kind": "theme",
                "scope": scope,
                "library_id": theme_library_id,
                "basis_label": found["theme"]["title"],
                "theme": found["theme"],
                "books": found["books"],
                "fetched_at": None,
                "stale": False,
                "fallback_reason": None,
            }
    popular = await _engine(request).popular_books(library)
    return {
        "kind": "popular",
        "scope": popular.scope,
        "library_id": popular.library_id,
        "basis_label": popular.period_label,
        "theme": None,
        "books": [book.public() for book in popular.books[: policy.RECOMMENDATION_MAX_BOOKS]],
        "fetched_at": _iso(popular.fetched_at),
        "stale": popular.stale,
        "fallback_reason": popular.fallback_reason,
    }


# ─────────── #8 상세 ───────────


@router.get("/{isbn13}")
async def book_detail(request: Request, isbn13: str) -> Any:
    return (await _engine(request).get_book(_isbn(isbn13))).public()


# ─────────── #12~#14 소장·대출 가능 ───────────


def _availability_item(item: AvailabilityItem, isbn13: str, distance_km: float | None) -> dict[str, Any]:
    url, kind = live_check_link(item.library, isbn13)
    summary = library_summary(item.library, distance_km)
    return {
        "library": {k: summary[k] for k in ("id", "name", "address", "distance_m")},
        "holding": item.holding,
        "loanable": item.loanable,
        "basis": item.basis,
        "source": item.source,
        "observed_at": _iso(item.observed_at),
        "data_date": _iso(item.data_date),
        "data_date_assumed": item.data_date_assumed,
        "fallback_reason": item.fallback_reason,
        "live_check": {"url": url, "kind": kind} if url else None,
    }


@router.get("/{isbn13}/availability")
async def availability(
    request: Request,
    isbn13: str,
    scope: Literal["nearby", "city"] | None = Query(None),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: int | None = Query(None),
    dtl_region: str | None = Query(None, pattern=DTL_REGION_PATTERN),
    library_id: int | None = Query(None, ge=1, le=BIGINT_MAX),
) -> Any:
    isbn13 = _isbn(isbn13)
    db = request.app.state.engine
    distances: dict[int, float] = {}
    radius: int | None = None
    if library_id is not None:
        if scope is not None or lat is not None or lng is not None or radius_km is not None or dtl_region:
            raise validation_error("library_id", "scope")
        libraries = [await _library_or_404(request, library_id)]
        scope_name = "library"
    elif scope == "nearby":
        if lat is None or lng is None or dtl_region is not None:
            raise validation_error("lat", "lng")
        radius = check_radius(radius_km)
        found = await run_db(db, lambda c: libraries_nearby(c, lat, lng, radius))
        libraries = [lib for lib, _ in found]
        distances = {lib.id: d for lib, d in found}
        scope_name = "nearby"
    elif scope == "city":
        if dtl_region is None or lat is not None or lng is not None or radius_km is not None:
            raise validation_error("dtl_region")
        libraries = await run_db(db, lambda c: libraries_in_region(c, dtl_region))
        scope_name = "city"
    else:
        raise validation_error("scope")

    items = await _engine(request).availability(isbn13, libraries)
    return {
        "isbn13": isbn13,
        "scope": scope_name,
        "radius_km": radius,
        "dtl_region": dtl_region if scope_name == "city" else None,
        "checked_at": now_kst().isoformat(timespec="seconds"),
        "items": [_availability_item(i, isbn13, distances.get(i.library.id)) for i in items],
    }


# ─────────── #15 구매 링크(Q-41 ② 미결: 예스24 검색 주소만) ───────────


@router.get("/{isbn13}/purchase-link")
async def purchase_link(isbn13: str) -> Any:
    isbn13 = _isbn(isbn13)
    return {
        "isbn13": isbn13,
        "provider": "yes24",
        "kind": "search",
        "url": policy.YES24_SEARCH_URL_TEMPLATE.format(isbn13=isbn13),
    }
