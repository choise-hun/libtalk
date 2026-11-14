"""시연·개발·테스트 Fallback을 위한 멱등 초기 참조 시드 데이터(도서관 4곳·도서·소장·인기도서·테마)."""

from datetime import timedelta
import hashlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from app.common import now_kst, today_kst
from app.db import run_db

SEED_LIBRARIES: tuple[dict[str, Any], ...] = (
    {
        "provider_lib_code": "111001",
        "name": "정독도서관",
        "address": "서울특별시 종로구 북촌로5길 48",
        "tel": "02-2011-5799",
        "homepage": "https://jdlib.sen.go.kr",
        "latitude": 37.5806,
        "longitude": 126.9830,
        "closed_text": "매월 첫째·셋째 수요일, 법정공휴일",
        "operating_time_text": "평일 09:00~22:00 / 주말 09:00~17:00",
        "region_code": "11",
        "dtl_region_code": "11110",
        "isbn_search_url_template": "https://jdlib.sen.go.kr/jdlib/intro/search/index.do?isbn={isbn13}",
        "look_preset": "warm",
        "look_is_manual": False,
    },
    {
        "provider_lib_code": "111002",
        "name": "남산도서관",
        "address": "서울특별시 용산구 소월로 109",
        "tel": "02-754-7338",
        "homepage": "https://nslib.sen.go.kr",
        "latitude": 37.5526,
        "longitude": 126.9813,
        "closed_text": "매월 첫째·셋째 월요일, 법정공휴일",
        "operating_time_text": "평일 09:00~20:00 / 주말 09:00~17:00",
        "region_code": "11",
        "dtl_region_code": "11170",
        "isbn_search_url_template": "https://nslib.sen.go.kr/nslib/intro/search/index.do?isbn={isbn13}",
        "look_preset": "toffee",
        "look_is_manual": False,
    },
    {
        "provider_lib_code": "111003",
        "name": "서울도서관",
        "address": "서울특별시 중구 세종대로 110",
        "tel": "02-120",
        "homepage": "https://lib.seoul.go.kr",
        "latitude": 37.5663,
        "longitude": 126.9779,
        "closed_text": "매주 월요일, 법정공휴일",
        "operating_time_text": "화~금 09:00~21:00 / 주말 09:00~18:00",
        "region_code": "11",
        "dtl_region_code": "11140",
        "isbn_search_url_template": "https://lib.seoul.go.kr/search/tot/result?st=KWRD&si=TOTAL&q={isbn13}",
        "look_preset": "oxford",
        "look_is_manual": False,
    },
    {
        "provider_lib_code": "111004",
        "name": "마포중앙도서관",
        "address": "서울특별시 마포구 성산로 128",
        "tel": "02-3153-5800",
        "homepage": "https://mplib.mapo.go.kr",
        "latitude": 37.5638,
        "longitude": 126.9082,
        "closed_text": "매주 월요일, 법정공휴일",
        "operating_time_text": "화~일 09:00~22:00",
        "region_code": "11",
        "dtl_region_code": "11440",
        "isbn_search_url_template": None,
        "look_preset": "modern",
        "look_is_manual": True,
    },
)

SEED_BOOKS: tuple[dict[str, Any], ...] = (
    {
        "isbn13": "9788936434120",
        "title": "소년이 온다",
        "author": "한강",
        "publisher": "창비",
        "cover_url": "https://shopping-phinf.pstatic.net/main_3249140/32491401626.jpg",
        "source": "data4library",
    },
    {
        "isbn13": "9788954682152",
        "title": "작별하지 않는다",
        "author": "한강",
        "publisher": "문학동네",
        "cover_url": "https://shopping-phinf.pstatic.net/main_3246352/32463527641.jpg",
        "source": "data4library",
    },
    {
        "isbn13": "9788936434267",
        "title": "채식주의자",
        "author": "한강",
        "publisher": "창비",
        "cover_url": "https://shopping-phinf.pstatic.net/main_3243626/32436265999.jpg",
        "source": "naver",
    },
    {
        "isbn13": "9791191043297",
        "title": "불편한 편의점",
        "author": "김호연",
        "publisher": "나무옆의자",
        "cover_url": "https://shopping-phinf.pstatic.net/main_3246667/32466678902.jpg",
        "source": "data4library",
    },
    {
        "isbn13": "9791161571188",
        "title": "달까지 가자",
        "author": "장류진",
        "publisher": "창비",
        "cover_url": "https://shopping-phinf.pstatic.net/main_3248234/32482341122.jpg",
        "source": "naver",
    },
    {
        "isbn13": "9788937473401",
        "title": "도서관의 삶",
        "author": "수전 올리언",
        "publisher": "민음사",
        "cover_url": "https://shopping-phinf.pstatic.net/main_3245111/32451112233.jpg",
        "source": "data4library",
    },
)


def _content_hash(lib: dict[str, Any]) -> str:
    raw = f"{lib['provider_lib_code']}|{lib['name']}|{lib['address']}|{lib['operating_time_text']}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def seed_reference_data(conn: Connection) -> dict[str, int]:
    """참조용 공공 도서관·도서·소장·인기도서·기본 테마를 멱등으로 삽입한다."""
    synced_at = now_kst()
    today = today_kst(synced_at)
    yesterday = today - timedelta(days=1)

    lib_ids_by_code: dict[str, int] = {}
    for lib in SEED_LIBRARIES:
        row = conn.execute(
            text(
                """
                INSERT INTO libraries (
                    provider_lib_code, name, address, tel, homepage,
                    latitude, longitude, closed_text, operating_time_text,
                    region_code, dtl_region_code, isbn_search_url_template,
                    content_hash, synced_at, look_preset, look_is_manual
                ) VALUES (
                    :provider_lib_code, :name, :address, :tel, :homepage,
                    :latitude, :longitude, :closed_text, :operating_time_text,
                    :region_code, :dtl_region_code, :isbn_search_url_template,
                    :content_hash, :synced_at, :look_preset, :look_is_manual
                )
                ON CONFLICT (provider_lib_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    address = EXCLUDED.address,
                    tel = EXCLUDED.tel,
                    homepage = EXCLUDED.homepage,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    closed_text = EXCLUDED.closed_text,
                    operating_time_text = EXCLUDED.operating_time_text,
                    region_code = EXCLUDED.region_code,
                    dtl_region_code = EXCLUDED.dtl_region_code,
                    isbn_search_url_template = EXCLUDED.isbn_search_url_template,
                    content_hash = EXCLUDED.content_hash,
                    synced_at = EXCLUDED.synced_at
                RETURNING id
                """
            ),
            {
                **lib,
                "content_hash": _content_hash(lib),
                "synced_at": synced_at,
            },
        ).one()
        lib_ids_by_code[lib["provider_lib_code"]] = int(row.id)

    book_ids_by_isbn: dict[str, int] = {}
    for book in SEED_BOOKS:
        row = conn.execute(
            text(
                """
                INSERT INTO books (isbn13, title, author, publisher, cover_url, source, fetched_at)
                VALUES (:isbn13, :title, :author, :publisher, :cover_url, :source, :fetched_at)
                ON CONFLICT (isbn13) DO UPDATE SET
                    title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    publisher = EXCLUDED.publisher,
                    cover_url = EXCLUDED.cover_url,
                    fetched_at = EXCLUDED.fetched_at
                RETURNING id
                """
            ),
            {**book, "fetched_at": synced_at},
        ).one()
        book_ids_by_isbn[book["isbn13"]] = int(row.id)

    # 소장·대출 가능 3상태(yes/no/unknown) 시드 관측치
    first_isbn = SEED_BOOKS[0]["isbn13"]
    first_book_id = book_ids_by_isbn[first_isbn]
    states = [
        ("111001", "yes", "yes"),
        ("111002", "yes", "no"),
        ("111003", "no", "no"),
        ("111004", "unknown", "unknown"),
    ]
    for lib_code, holding, loanable in states:
        conn.execute(
            text(
                """
                INSERT INTO availability_observations (
                    library_id, book_id, observed_on, holding, loanable,
                    data_date, data_date_assumed, observed_at, source
                ) VALUES (
                    :library_id, :book_id, :observed_on, :holding, :loanable,
                    :data_date, true, :observed_at, 'data4library'
                )
                ON CONFLICT (library_id, book_id, observed_on) DO UPDATE SET
                    holding = EXCLUDED.holding,
                    loanable = EXCLUDED.loanable,
                    observed_at = EXCLUDED.observed_at
                """
            ),
            {
                "library_id": lib_ids_by_code[lib_code],
                "book_id": first_book_id,
                "observed_on": today,
                "holding": holding,
                "loanable": loanable,
                "data_date": yesterday,
                "observed_at": synced_at,
            },
        )

    # 전국 인기 도서 캐시
    for rank, book in enumerate(SEED_BOOKS, start=1):
        conn.execute(
            text(
                """
                INSERT INTO popular_books_cache (
                    scope, library_id, rank, book_id, period_label, fetched_at
                ) VALUES (
                    'national', NULL, :rank, :book_id, '전국 · 최근 30일', :fetched_at
                )
                ON CONFLICT (rank) WHERE scope = 'national' DO UPDATE SET
                    book_id = EXCLUDED.book_id,
                    period_label = EXCLUDED.period_label,
                    fetched_at = EXCLUDED.fetched_at
                """
            ),
            {
                "rank": rank,
                "book_id": book_ids_by_isbn[book["isbn13"]],
                "fetched_at": synced_at,
            },
        )

    # 정독도서관 도서관별 인기 도서 캐시
    jd_lib_id = lib_ids_by_code["111001"]
    for rank, book in enumerate(SEED_BOOKS[:3], start=1):
        conn.execute(
            text(
                """
                INSERT INTO popular_books_cache (
                    scope, library_id, rank, book_id, period_label, fetched_at
                ) VALUES (
                    'library', :library_id, :rank, :book_id, '정독도서관 · 최근 30일', :fetched_at
                )
                ON CONFLICT (library_id, rank) WHERE scope = 'library' DO UPDATE SET
                    book_id = EXCLUDED.book_id,
                    period_label = EXCLUDED.period_label,
                    fetched_at = EXCLUDED.fetched_at
                """
            ),
            {
                "library_id": jd_lib_id,
                "rank": rank,
                "book_id": book_ids_by_isbn[book["isbn13"]],
                "fetched_at": synced_at,
            },
        )

    # 공통 활성 서가 테마 1건 (없을 때만 생성)
    existing_theme_id = conn.execute(
        text("SELECT id FROM shelf_themes WHERE library_id IS NULL AND title = :title LIMIT 1"),
        {"title": "이번 달 이웃들이 함께 읽는 한국 소설"},
    ).scalar_one_or_none()

    if existing_theme_id is None:
        theme_id = int(
            conn.execute(
                text(
                    """
                    INSERT INTO shelf_themes (
                        library_id, title, description, starts_on, ends_on, is_active, created_at
                    ) VALUES (
                        NULL, :title, :description, :starts_on, :ends_on, true, :created_at
                    )
                    RETURNING id
                    """
                ),
                {
                    "title": "이번 달 이웃들이 함께 읽는 한국 소설",
                    "description": "동네 도서관 광장에서 가장 많은 이야기가 오간 소설 세 권",
                    "starts_on": today - timedelta(days=7),
                    "ends_on": today + timedelta(days=30),
                    "created_at": synced_at,
                },
            ).scalar_one()
        )
    else:
        theme_id = int(existing_theme_id)

    for order, book in enumerate(SEED_BOOKS[:3], start=1):
        conn.execute(
            text(
                """
                INSERT INTO shelf_theme_books (theme_id, book_id, sort_order)
                VALUES (:theme_id, :book_id, :sort_order)
                ON CONFLICT (theme_id, book_id) DO UPDATE SET
                    sort_order = EXCLUDED.sort_order
                """
            ),
            {
                "theme_id": theme_id,
                "book_id": book_ids_by_isbn[book["isbn13"]],
                "sort_order": order,
            },
        )

    return {
        "libraries": len(lib_ids_by_code),
        "books": len(book_ids_by_isbn),
    }


async def run_seed(engine: Engine) -> dict[str, int]:
    return await run_db(engine, seed_reference_data)
