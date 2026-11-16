"""06 #7 검색, #8 상세, #9 추천, #12~#14 소장·대출 가능, #15 구매 링크. 인증 없음.

02 LIB-01(추천·검색), LIB-03·06·07(세 갈래·출처·기준일·실시간 확인 주소·도시 재검색), AC-LIB, AC-UNKNOWN, NFR-02.
외부 제공자는 가짜(provider_fakes)만 쓴다(CI 외부 네트워크 없음).
"""

import json
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app import policy
from app.common import today_kst
from app.main import create_app
from app.seed import SEED_BOOKS, seed_reference_data
from app.services.provider_engine import BookInfo, HoldingResult, ProviderError, Providers
from app.settings import Settings
from tests.conftest import TEST_SUPABASE_URL
from tests.provider_fakes import FakeBookSearch, FakeLibraryData

pytestmark = pytest.mark.usefixtures("clean_reference_tables")

FIRST_ISBN = SEED_BOOKS[0]["isbn13"]
JEONGDOK = {"lat": 37.5806, "lng": 126.9830}
UNSEEN_ISBN = "9791162540640"


@pytest.fixture
def seeded(db_engine: Engine) -> Engine:
    with db_engine.begin() as conn:
        seed_reference_data(conn)
    return db_engine


@pytest.fixture
def make_client(test_db_url: str, fake_jwks_client: Mock, seeded: Engine) -> Any:
    clients: list[TestClient] = []

    def _make(providers: Providers | None = None) -> TestClient:
        app = create_app(
            Settings(app_env="test", database_url=test_db_url, supabase_url=TEST_SUPABASE_URL),  # type: ignore[call-arg]
            jwks_client=fake_jwks_client,
            providers=providers or Providers(),
        )
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.__exit__(None, None, None)


def _error(response: Any) -> tuple[int, str, str]:
    body = response.json()["error"]
    assert set(body) == {"code", "message", "detail"}
    return response.status_code, body["code"], body["detail"]


def _lib_id(engine: Engine, code: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT id FROM libraries WHERE provider_lib_code = :c"), {"c": code}).scalar_one())


# ─────────── #7 검색 ───────────


def test_search_without_key_returns_seed_cache(make_client: Any) -> None:
    response = make_client().get("/api/v1/books/search", params={"q": " 한강 "})
    assert response.status_code == 200
    body = response.json()
    assert [b["title"] for b in body["items"]] == ["소년이 온다", "작별하지 않는다", "채식주의자"]
    assert (body["source"], body["fallback_reason"], body["next_start"]) == ("cache", "not_configured", None)
    assert set(body["items"][0]) == {"isbn13", "title", "author", "publisher", "cover_url", "source"}


def test_search_with_provider(make_client: Any) -> None:
    fake = FakeBookSearch([BookInfo(isbn13=UNSEEN_ISBN, title="새 검색 결과")], total=30)
    body = make_client(Providers(books=fake)).get("/api/v1/books/search", params={"q": "새"}).json()
    assert body["source"] == "naver" and body["next_start"] == 21
    assert body["items"][0]["isbn13"] == UNSEEN_ISBN


def test_search_provider_down_and_nothing_cached_is_503(make_client: Any) -> None:
    client = make_client(Providers(books=FakeBookSearch(error=ProviderError("down"))))
    assert _error(client.get("/api/v1/books/search", params={"q": "캐시에없음"}))[:2] == (
        503,
        "PROVIDER_UNAVAILABLE",
    )


@pytest.mark.parametrize(
    "params, field",
    [({}, "q"), ({"q": "   "}, "q"), ({"q": "x" * 101}, "q"), ({"q": "a", "start": 0}, "start"),
     ({"q": "a", "start": 1001}, "start")],
)
def test_search_validation(make_client: Any, params: dict, field: str) -> None:
    assert _error(make_client().get("/api/v1/books/search", params=params)) == (422, "VALIDATION_ERROR", field)


# ─────────── #8 상세 ───────────


def test_book_detail(make_client: Any) -> None:
    client = make_client()
    body = client.get(f"/api/v1/books/{FIRST_ISBN}").json()
    assert body["title"] == "소년이 온다" and body["cover_url"].startswith("https://")
    assert _error(client.get("/api/v1/books/9788936434121")) == (422, "VALIDATION_ERROR", "isbn13")
    assert _error(client.get("/api/v1/books/12345"))[:2] == (422, "VALIDATION_ERROR")
    assert _error(client.get(f"/api/v1/books/{UNSEEN_ISBN}"))[:2] == (404, "NOT_FOUND")


# ─────────── #9 추천(Q-47) ───────────


def test_recommendations_use_active_common_theme(make_client: Any) -> None:
    body = make_client().get("/api/v1/books/recommendations").json()
    assert (body["kind"], body["scope"]) == ("theme", "national")
    assert body["basis_label"] == "이번 달 이웃들이 함께 읽는 한국 소설"
    assert [b["isbn13"] for b in body["books"]] == [b["isbn13"] for b in SEED_BOOKS[:3]]


def test_recommendations_library_theme_beats_common(make_client: Any, seeded: Engine) -> None:
    lib_id = _lib_id(seeded, "111002")
    with seeded.begin() as conn:
        theme_id = conn.execute(
            text(
                "INSERT INTO shelf_themes (library_id, title, starts_on, ends_on, is_active, created_at) "
                "VALUES (:l, '남산 테마', :t, :t, true, now()) RETURNING id"
            ),
            {"l": lib_id, "t": today_kst()},
        ).scalar_one()
        book_id = conn.execute(text("SELECT id FROM books WHERE isbn13 = :i"), {"i": SEED_BOOKS[5]["isbn13"]}).scalar_one()
        conn.execute(
            text("INSERT INTO shelf_theme_books (theme_id, book_id, sort_order) VALUES (:t, :b, 1)"),
            {"t": theme_id, "b": book_id},
        )
    body = make_client().get("/api/v1/books/recommendations", params={"library_id": lib_id}).json()
    assert (body["kind"], body["scope"], body["basis_label"]) == ("theme", "library", "남산 테마")
    # 다른 도서관은 공통 테마
    other = make_client().get("/api/v1/books/recommendations", params={"library_id": _lib_id(seeded, "111001")}).json()
    assert (other["kind"], other["scope"]) == ("theme", "national")


def test_recommendations_fall_back_to_popular(make_client: Any, seeded: Engine) -> None:
    with seeded.begin() as conn:
        conn.execute(text("UPDATE shelf_themes SET is_active = false"))
    client = make_client()
    national = client.get("/api/v1/books/recommendations").json()
    assert (national["kind"], national["scope"], national["basis_label"]) == ("popular", "national", "전국 · 최근 30일")
    assert national["fetched_at"].endswith("+09:00")
    jd = client.get("/api/v1/books/recommendations", params={"library_id": _lib_id(seeded, "111001")}).json()
    assert (jd["scope"], jd["basis_label"]) == ("library", "정독도서관 · 최근 30일")
    ns = client.get("/api/v1/books/recommendations", params={"library_id": _lib_id(seeded, "111002")}).json()
    assert (ns["scope"], ns["fallback_reason"]) == ("national", "not_configured")  # 도서관 데이터 없음 → 전국
    assert _error(client.get("/api/v1/books/recommendations", params={"library_id": 999999}))[:2] == (404, "NOT_FOUND")
    assert _error(client.get("/api/v1/books/recommendations", params={"library_id": "x"}))[:2] == (422, "VALIDATION_ERROR")


def test_recommendations_nothing_at_all_is_503(make_client: Any, seeded: Engine) -> None:
    with seeded.begin() as conn:
        conn.execute(text("UPDATE shelf_themes SET is_active = false"))
        conn.execute(text("DELETE FROM popular_books_cache"))
    assert _error(make_client().get("/api/v1/books/recommendations"))[:2] == (503, "PROVIDER_UNAVAILABLE")


# ─────────── #12~#14 소장·대출 가능 ───────────


def test_availability_nearby_three_states_and_live_check(make_client: Any) -> None:
    response = make_client().get(
        f"/api/v1/books/{FIRST_ISBN}/availability", params={"scope": "nearby", **JEONGDOK}
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["scope"], body["radius_km"]) == ("nearby", 3) and body["checked_at"].endswith("+09:00")
    first, second = body["items"]
    assert first["library"]["name"] == "정독도서관" and first["library"]["distance_m"] == 0
    assert (first["holding"], first["loanable"], first["basis"]) == ("yes", "yes", "today")
    assert (second["holding"], second["loanable"]) == ("no", "no")
    assert first["source"] == "data4library" and first["observed_at"].endswith("+09:00")
    assert first["data_date_assumed"] is True and first["data_date"]
    assert first["live_check"] == {
        "url": f"https://jdlib.sen.go.kr/jdlib/intro/search/index.do?isbn={FIRST_ISBN}",
        "kind": "isbn_search",
    }
    assert "실시간" not in json.dumps(body, ensure_ascii=False)  # H-ARCH-06: 단정 문구 없음


def test_availability_city_unknown_and_homepage_link(make_client: Any) -> None:
    body = make_client().get(
        f"/api/v1/books/{FIRST_ISBN}/availability", params={"scope": "city", "dtl_region": "11440"}
    ).json()
    [item] = body["items"]
    assert (item["holding"], item["loanable"], item["basis"]) == ("unknown", "unknown", "none")
    assert item["fallback_reason"] == "not_configured" and item["observed_at"] is None
    assert item["live_check"] == {"url": "https://mplib.mapo.go.kr", "kind": "homepage"}
    assert body["dtl_region"] == "11440"


def test_availability_single_library(make_client: Any, seeded: Engine) -> None:
    client = make_client()
    lib_id = _lib_id(seeded, "111002")
    body = client.get(f"/api/v1/books/{FIRST_ISBN}/availability", params={"library_id": lib_id}).json()
    assert body["scope"] == "library" and [(i["holding"], i["loanable"]) for i in body["items"]] == [("yes", "no")]
    assert _error(client.get(f"/api/v1/books/{FIRST_ISBN}/availability", params={"library_id": 999999}))[:2] == (
        404,
        "NOT_FOUND",
    )


@pytest.mark.parametrize(
    "params, field",
    [
        ({}, "scope"),
        ({"scope": "all"}, "scope"),
        ({"scope": "nearby", "lat": 37.5}, "lat,lng"),
        ({"scope": "nearby", **JEONGDOK, "radius_km": 10}, "radius_km"),
        ({"scope": "city"}, "dtl_region"),
        ({"scope": "city", "dtl_region": "11440", "lat": 37.5}, "dtl_region"),
        ({"library_id": 1, "scope": "nearby"}, "library_id,scope"),
    ],
)
def test_availability_validation(make_client: Any, params: dict, field: str) -> None:
    response = make_client().get(f"/api/v1/books/{FIRST_ISBN}/availability", params=params)
    assert _error(response) == (422, "VALIDATION_ERROR", field)


def test_availability_bad_isbn_is_422(make_client: Any) -> None:
    response = make_client().get("/api/v1/books/abc/availability", params={"scope": "city", "dtl_region": "11440"})
    assert _error(response) == (422, "VALIDATION_ERROR", "isbn13")


def test_availability_provider_failure_is_200_unknown(make_client: Any, seeded: Engine) -> None:
    """AC-UNKNOWN: 제공자 오류는 오류 응답이 아니라 200 안의 unknown. 미소장(no)으로 저장하지 않는다."""
    fake = FakeLibraryData(default_holding=ProviderError("timeout"))
    response = make_client(Providers(library_data=fake)).get(
        f"/api/v1/books/{FIRST_ISBN}/availability", params={"scope": "city", "dtl_region": "11440"}
    )
    assert response.status_code == 200
    [item] = response.json()["items"]
    assert (item["holding"], item["loanable"], item["fallback_reason"]) == ("unknown", "unknown", "provider_error")
    with seeded.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM availability_observations WHERE holding = 'no' AND library_id = :l"),
            {"l": _lib_id(seeded, "111004")},
        ).scalar_one() == 0


def test_availability_repeat_is_idempotent_and_cached(make_client: Any) -> None:
    fake = FakeLibraryData(default_holding=HoldingResult(holding="yes", loanable="no"))
    client = make_client(Providers(library_data=fake))
    params = {"scope": "city", "dtl_region": "11440"}
    first = client.get(f"/api/v1/books/{FIRST_ISBN}/availability", params=params).json()["items"]
    second = client.get(f"/api/v1/books/{FIRST_ISBN}/availability", params=params).json()["items"]
    assert first == second and len(fake.calls) == 1
    assert (first[0]["holding"], first[0]["loanable"]) == ("yes", "no")


def test_availability_all_limited_is_429(make_client: Any, seeded: Engine) -> None:
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM availability_observations"))
        conn.execute(
            text("INSERT INTO provider_daily_usage (provider, usage_date, call_count) VALUES ('data4library', :d, :c)"),
            {"d": today_kst(), "c": policy.DATA4LIBRARY_DAILY_LIMIT},
        )
    client = make_client(Providers(library_data=FakeLibraryData(default_holding=HoldingResult("yes", "yes"))))
    response = client.get(f"/api/v1/books/{FIRST_ISBN}/availability", params={"scope": "city", "dtl_region": "11440"})
    assert _error(response)[:2] == (429, "PROVIDER_LIMIT")


def test_availability_nearby_with_no_library_in_radius_is_empty(make_client: Any) -> None:
    body = make_client().get(
        f"/api/v1/books/{FIRST_ISBN}/availability", params={"scope": "nearby", "lat": 35.1, "lng": 129.0}
    ).json()
    assert body["items"] == []  # 앱은 빈 결과에서 도시 전체 재검색을 권한다(LIB-07)


# ─────────── #15 구매 링크 ───────────


def test_purchase_link(make_client: Any) -> None:
    client = make_client()
    body = client.get(f"/api/v1/books/{FIRST_ISBN}/purchase-link").json()
    assert body == {
        "isbn13": FIRST_ISBN,
        "provider": "yes24",
        "kind": "search",
        "url": f"https://www.yes24.com/Product/Search?domain=BOOK&query={FIRST_ISBN}",
    }
    assert _error(client.get("/api/v1/books/123/purchase-link"))[:2] == (422, "VALIDATION_ERROR")


def test_routers_have_no_http_client_imports() -> None:
    """H-ARCH-07: 라우터는 외부 호출을 직접 하지 않는다."""
    from pathlib import Path

    for name in ("books.py", "libraries.py"):
        source = (Path(__file__).resolve().parents[1] / "app" / "routers" / name).read_text(encoding="utf-8")
        for banned in ("httpx", "requests", "urllib", "aiohttp"):
            assert f"import {banned}" not in source and f"from {banned}" not in source
