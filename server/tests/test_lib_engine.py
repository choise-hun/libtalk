"""LIB-0 조회 엔진: 상한 예약 원자성, 트랜잭션 밖 호출, 키 없음·실패·상한 초과의 캐시·시드 Fallback, 세 갈래 상태.

02 AC-UNKNOWN(불가·미소장으로 단정하지 않음, 오래된 캐시는 시각과 함께 구별), NFR-02(상한), 05 §11.2(call_count).
외부 네트워크는 쓰지 않는다: 가짜 제공자(provider_fakes) + 127.0.0.1 임시 HTTP 서버.
"""

import asyncio
import json
import threading
import time
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from tests.provider_fakes import FakeBookSearch, FakeLibraryData
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app import policy
from app.common import ApiError, KST, today_kst
from app.seed import SEED_BOOKS, seed_reference_data
from app.services import provider_engine as pe
from app.services.provider_engine import (
    BookInfo,
    Data4LibraryClient,
    HoldingResult,
    LibraryInfo,
    NaverBookClient,
    ProviderEngine,
    ProviderError,
    Providers,
    libraries_in_region,
    reserve_provider_call,
)

pytestmark = pytest.mark.usefixtures("clean_reference_tables")

FIRST_ISBN = SEED_BOOKS[0]["isbn13"]  # 시드 소장 관측이 붙은 책(소년이 온다)
NEW_BOOK = BookInfo(isbn13="9788932473901", title="새로 찾은 책", author="작가", publisher="출판사")
HELD = HoldingResult(holding="yes", loanable="yes")


def run(coro: Any) -> Any:
    return asyncio.run(coro)


@pytest.fixture
def seeded(db_engine: Engine) -> Engine:
    with db_engine.begin() as conn:
        seed_reference_data(conn)
    return db_engine


@pytest.fixture
def own_engine(test_db_url: str) -> Iterator[Engine]:
    """풀 사용량(checkedout)을 이 시험만 보도록 따로 만든 엔진."""
    engine = create_engine(test_db_url, connect_args={"connect_timeout": 2})
    try:
        yield engine
    finally:
        engine.dispose()


def _libs(engine: Engine, code: str = "11110") -> list[pe.LibraryRow]:
    with engine.connect() as conn:
        return libraries_in_region(conn, code)


def _all_libs(engine: Engine) -> list[pe.LibraryRow]:
    with engine.connect() as conn:
        ids = conn.execute(text("SELECT id FROM libraries ORDER BY id")).scalars().all()
        return [pe.get_library(conn, i) for i in ids]  # type: ignore[misc]


def _usage(engine: Engine, provider: str) -> int:
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT call_count FROM provider_daily_usage WHERE provider = :p AND usage_date = :d"),
            {"p": provider, "d": today_kst()},
        ).scalar_one_or_none()
    return int(value or 0)


def _fill_usage(engine: Engine, provider: str, count: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO provider_daily_usage (provider, usage_date, call_count) VALUES (:p, :d, :c) "
                "ON CONFLICT (provider, usage_date) DO UPDATE SET call_count = EXCLUDED.call_count"
            ),
            {"p": provider, "d": today_kst(), "c": count},
        )


# ─────────────────── 정규화 ───────────────────


def test_isbn_normalization() -> None:
    assert pe.normalize_isbn("8936434128 9788936434120") == "9788936434120"
    assert pe.normalize_isbn("8936434128") == "9788936434120"  # 10자리 → 13자리(05 §3.1)
    assert pe.normalize_isbn("9788936434121") is None  # 검사 숫자 틀림
    assert pe.normalize_isbn("") is None
    assert pe.isbn13_is_valid("9788936434120")
    assert not pe.isbn13_is_valid("978893643412")


def test_cover_url_is_https_only() -> None:
    assert pe.https_cover("http://img.example/a.jpg") == "https://img.example/a.jpg"
    assert pe.https_cover("https://img.example/a.jpg") == "https://img.example/a.jpg"
    assert pe.https_cover("javascript:alert(1)") is None
    assert pe.https_cover("") is None


# ─────────────────── 상한(NFR-02, 05 §11.2) ───────────────────


def test_reserve_is_atomic_under_concurrency(db_engine: Engine) -> None:
    """동시 30건 · 상한 10 → 정확히 10건만 허가, call_count = 10(넘지 않음)."""
    results: list[bool] = []
    barrier = threading.Barrier(30)

    def worker() -> None:
        barrier.wait()
        with db_engine.begin() as conn:
            results.append(reserve_provider_call(conn, "naver", today_kst(), 10))

    threads = [threading.Thread(target=worker) for _ in range(30)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 10
    assert _usage(db_engine, "naver") == 10


def test_limit_reached_skips_call_and_uses_cache(seeded: Engine) -> None:
    _fill_usage(seeded, "naver", policy.NAVER_DAILY_LIMIT)
    fake = FakeBookSearch([NEW_BOOK])
    engine = ProviderEngine(seeded, Providers(books=fake))
    result = run(engine.search_books("한강", 1))
    assert fake.calls == []  # 상한이면 부르지 않는다
    assert result.source == "cache" and result.fallback_reason == "limit"
    assert {b.title for b in result.items} == {"소년이 온다", "작별하지 않는다", "채식주의자"}
    assert _usage(seeded, "naver") == policy.NAVER_DAILY_LIMIT  # 예약이 상한을 넘기지 않음


def test_limit_reached_with_empty_cache_is_429(clean_reference_tables: Engine) -> None:
    _fill_usage(clean_reference_tables, "naver", policy.NAVER_DAILY_LIMIT)
    engine = ProviderEngine(clean_reference_tables, Providers(books=FakeBookSearch([NEW_BOOK])))
    with pytest.raises(ApiError) as exc:
        run(engine.search_books("새로", 1))
    assert (exc.value.status_code, exc.value.code) == (429, "PROVIDER_LIMIT")


# ─────────────────── 도서 검색·상세(06 #7·#8) ───────────────────


def test_search_without_key_uses_seed_cache(seeded: Engine) -> None:
    result = run(ProviderEngine(seeded, Providers()).search_books("한강", 1))
    assert result.source == "cache" and result.fallback_reason == "not_configured"
    assert [b.title for b in result.items] == ["소년이 온다", "작별하지 않는다", "채식주의자"]
    assert result.next_start is None


def test_search_like_wildcards_are_escaped(seeded: Engine) -> None:
    assert run(ProviderEngine(seeded, Providers()).search_books("%", 1)).items == []
    assert run(ProviderEngine(seeded, Providers()).search_books("_", 1)).items == []


def test_search_with_provider_caches_books_and_pages(clean_reference_tables: Engine) -> None:
    many = [
        BookInfo(isbn13=isbn, title=f"검색 책 {n}")
        for n, isbn in enumerate(["9788932473901", "9788936434120", "9788954682152"])
    ]
    fake = FakeBookSearch(many, total=45)
    result = run(ProviderEngine(clean_reference_tables, Providers(books=fake)).search_books("검색", 1))
    assert result.source == "naver" and result.fallback_reason is None
    assert [b.isbn13 for b in result.items] == [b.isbn13 for b in many]
    assert result.next_start == 21
    assert _usage(clean_reference_tables, "naver") == 1
    with clean_reference_tables.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM books WHERE source = 'naver'")).scalar_one() == 3
    last = run(ProviderEngine(clean_reference_tables, Providers(books=fake)).search_books("검색", 41))
    assert last.next_start is None  # 41 + 20 > 45


def test_search_provider_error_falls_back_then_503(seeded: Engine) -> None:
    engine = ProviderEngine(seeded, Providers(books=FakeBookSearch(error=ProviderError("timeout"))))
    result = run(engine.search_books("한강", 1))
    assert result.source == "cache" and result.fallback_reason == "provider_error" and result.items
    with pytest.raises(ApiError) as exc:
        run(engine.search_books("캐시에없는말", 1))
    assert (exc.value.status_code, exc.value.code) == (503, "PROVIDER_UNAVAILABLE")


def test_unexpected_provider_bug_becomes_provider_error(seeded: Engine) -> None:
    engine = ProviderEngine(seeded, Providers(books=FakeBookSearch(error=KeyError("x"))))
    assert run(engine.search_books("한강", 1)).fallback_reason == "provider_error"


def test_get_book_paths(seeded: Engine) -> None:
    fake = FakeBookSearch([NEW_BOOK])
    engine = ProviderEngine(seeded, Providers(books=fake))
    assert run(engine.get_book(FIRST_ISBN)).title == "소년이 온다"
    assert fake.calls == []  # DB에 있으면 부르지 않는다
    assert run(engine.get_book(NEW_BOOK.isbn13)).title == "새로 찾은 책"
    assert run(engine.get_book(NEW_BOOK.isbn13)).source == "naver"
    assert len(fake.calls) == 1  # 두 번째는 저장된 행

    with pytest.raises(ApiError) as missing:
        run(engine.get_book("9791162540640"))
    assert missing.value.status_code == 404

    with pytest.raises(ApiError) as no_key:
        run(ProviderEngine(seeded, Providers()).get_book("9791162540640"))
    assert no_key.value.status_code == 404

    broken = ProviderEngine(seeded, Providers(books=FakeBookSearch(error=ProviderError("x"))))
    with pytest.raises(ApiError) as down:
        run(broken.get_book("9791162540640"))
    assert (down.value.status_code, down.value.code) == (503, "PROVIDER_UNAVAILABLE")


# ─────────────────── 소장·대출(06 #12~#14, AC-UNKNOWN) ───────────────────


def _by_code(items: list[pe.AvailabilityItem]) -> dict[str, pe.AvailabilityItem]:
    return {i.library.provider_lib_code: i for i in items}


def test_availability_without_key_uses_seed_and_keeps_unknown(seeded: Engine) -> None:
    items = _by_code(run(ProviderEngine(seeded, Providers()).availability(FIRST_ISBN, _all_libs(seeded))))
    assert (items["111001"].holding, items["111001"].loanable, items["111001"].basis) == ("yes", "yes", "today")
    assert (items["111002"].holding, items["111002"].loanable) == ("yes", "no")
    assert (items["111003"].holding, items["111003"].loanable) == ("no", "no")
    # 시드의 unknown 관측은 캐시로 치지 않는다 → 키가 없으니 unknown 그대로(no로 바꾸지 않음)
    assert (items["111004"].holding, items["111004"].loanable) == ("unknown", "unknown")
    assert items["111004"].basis == "none" and items["111004"].fallback_reason == "not_configured"
    assert items["111001"].data_date == today_kst() - timedelta(days=1)
    assert items["111001"].data_date_assumed is True


def test_availability_success_is_stored_and_cached_for_today(seeded: Engine) -> None:
    lib = _libs(seeded, "11440")  # 마포중앙(시드 unknown)
    fake = FakeLibraryData(holdings={"111004": HoldingResult(holding="yes", loanable="no")})
    engine = ProviderEngine(seeded, Providers(library_data=fake))
    [item] = run(engine.availability(FIRST_ISBN, lib))
    assert (item.holding, item.loanable, item.basis, item.source) == ("yes", "no", "today", "data4library")
    assert item.data_date == today_kst() - timedelta(days=1) and item.data_date_assumed is True
    [again] = run(engine.availability(FIRST_ISBN, lib))
    assert (again.holding, again.loanable) == ("yes", "no")
    assert len(fake.calls) == 1  # 같은 서울 날짜에는 다시 부르지 않는다
    with seeded.connect() as conn:
        row = conn.execute(
            text(
                "SELECT holding, loanable, data_date_assumed FROM availability_observations "
                "WHERE library_id = :l AND observed_on = :d"
            ),
            {"l": lib[0].id, "d": today_kst()},
        ).one()
    assert tuple(row) == ("yes", "no", True)


@pytest.mark.parametrize(
    "failure, reason",
    [(ProviderError("timeout"), "provider_error"), (TimeoutError("5s"), "provider_error")],
)
def test_availability_failure_is_unknown_and_not_stored(
    clean_reference_tables: Engine, failure: BaseException, reason: str
) -> None:
    """오류·시간 초과는 unknown(H-ARCH-06): no로 저장·응답하지 않고 다음 요청에서 다시 부른다."""
    with clean_reference_tables.begin() as conn:
        seed_reference_data(conn)
        conn.execute(text("DELETE FROM availability_observations"))
    fake = FakeLibraryData(default_holding=failure)
    engine = ProviderEngine(clean_reference_tables, Providers(library_data=fake))
    libs = _all_libs(clean_reference_tables)
    items = run(engine.availability(FIRST_ISBN, libs))
    assert {(i.holding, i.loanable, i.basis, i.fallback_reason) for i in items} == {
        ("unknown", "unknown", "none", reason)
    }
    with clean_reference_tables.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM availability_observations")).scalar_one() == 0
    run(engine.availability(FIRST_ISBN, libs))
    assert len(fake.calls) == 2 * len(libs)


def test_availability_stale_cache_is_marked(clean_reference_tables: Engine) -> None:
    with clean_reference_tables.begin() as conn:
        seed_reference_data(conn)
        conn.execute(text("DELETE FROM availability_observations"))
        lib_id, book_id = conn.execute(
            text("SELECT l.id, b.id FROM libraries l, books b WHERE l.provider_lib_code='111001' AND b.isbn13=:i"),
            {"i": FIRST_ISBN},
        ).one()
        old = today_kst() - timedelta(days=3)
        conn.execute(
            text(
                "INSERT INTO availability_observations (library_id, book_id, observed_on, holding, loanable, "
                "data_date, data_date_assumed, observed_at, source) "
                "VALUES (:l, :b, :d, 'yes', 'no', :dd, true, :at, 'data4library')"
            ),
            {"l": lib_id, "b": book_id, "d": old, "dd": old - timedelta(days=1),
             "at": datetime.combine(old, datetime.min.time(), KST)},
        )
    fake = FakeLibraryData(default_holding=ProviderError("down"))
    [item] = run(
        ProviderEngine(clean_reference_tables, Providers(library_data=fake)).availability(
            FIRST_ISBN, _libs(clean_reference_tables, "11110")
        )
    )
    assert (item.holding, item.loanable, item.basis, item.fallback_reason) == ("yes", "no", "stale", "provider_error")
    assert item.observed_at is not None and item.observed_at.astimezone(KST).date() == old  # 오래된 캐시는 시각과 함께


def test_availability_all_limited_is_429_and_partial_is_unknown(seeded: Engine) -> None:
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM availability_observations"))
    _fill_usage(seeded, "data4library", policy.DATA4LIBRARY_DAILY_LIMIT)
    fake = FakeLibraryData(default_holding=HELD)
    engine = ProviderEngine(seeded, Providers(library_data=fake))
    with pytest.raises(ApiError) as exc:
        run(engine.availability(FIRST_ISBN, _all_libs(seeded)))
    assert (exc.value.status_code, exc.value.code) == (429, "PROVIDER_LIMIT")
    assert fake.calls == []

    _fill_usage(seeded, "data4library", policy.DATA4LIBRARY_DAILY_LIMIT - 1)  # 1건만 남음
    items = run(engine.availability(FIRST_ISBN, _all_libs(seeded)))
    assert sorted(i.basis for i in items) == ["none", "none", "none", "today"]
    assert {i.fallback_reason for i in items if i.basis == "none"} == {"limit"}
    assert _usage(seeded, "data4library") == policy.DATA4LIBRARY_DAILY_LIMIT


def test_availability_per_request_cap(seeded: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM availability_observations"))
    monkeypatch.setattr(policy, "AVAILABILITY_MAX_CALLS_PER_REQUEST", 1)
    fake = FakeLibraryData(default_holding=HELD)
    items = run(ProviderEngine(seeded, Providers(library_data=fake)).availability(FIRST_ISBN, _all_libs(seeded)))
    assert len(fake.calls) == 1
    assert [i.fallback_reason for i in items].count("limit") == 3


def test_external_calls_happen_outside_transactions(seeded: Engine, own_engine: Engine) -> None:
    """H-ARCH-03: 호출 순간 이 엔진의 풀에서 빌려 간 연결이 0개(트랜잭션을 쥔 채 부르지 않는다)."""
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM availability_observations"))
    seen: list[int] = []

    def check() -> None:
        seen.append(own_engine.pool.checkedout())  # type: ignore[attr-defined]

    providers = Providers(
        books=FakeBookSearch([NEW_BOOK], on_call=check),
        library_data=FakeLibraryData(
            default_holding=HELD, popular={None: [NEW_BOOK]}, on_call=check
        ),
    )
    engine = ProviderEngine(own_engine, providers)
    run(engine.search_books("새로", 1))
    with pytest.raises(ApiError):
        run(engine.get_book("9791162540640"))  # 없는 책 → 네이버 상세 조회(404)
    run(engine.availability(FIRST_ISBN, _libs(seeded, "11440")))
    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM popular_books_cache"))
    run(engine.popular_books(None))
    assert seen and set(seen) == {0}


def test_availability_for_book_unknown_to_db_does_not_store(clean_reference_tables: Engine) -> None:
    with clean_reference_tables.begin() as conn:
        seed_reference_data(conn)
    fake = FakeLibraryData(default_holding=HELD)
    [item] = run(
        ProviderEngine(clean_reference_tables, Providers(library_data=fake)).availability(
            "9791162540640", _libs(clean_reference_tables, "11110")
        )
    )
    assert (item.holding, item.basis) == ("yes", "today")
    with clean_reference_tables.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM availability_observations a JOIN books b ON b.id = a.book_id "
                 "WHERE b.isbn13 = '9791162540640'")
        ).scalar_one() == 0


# ─────────────────── 인기 도서(06 #9) ───────────────────


def test_popular_national_fresh_cache_skips_call(seeded: Engine) -> None:
    fake = FakeLibraryData(popular={None: [NEW_BOOK]})
    result = run(ProviderEngine(seeded, Providers(library_data=fake)).popular_books(None))
    assert fake.calls == []
    assert result.scope == "national" and result.period_label == "전국 · 최근 30일"
    assert [b.isbn13 for b in result.books] == [b["isbn13"] for b in SEED_BOOKS]
    assert result.stale is False


def test_popular_national_refreshes_next_day(seeded: Engine) -> None:
    with seeded.begin() as conn:
        conn.execute(text("UPDATE popular_books_cache SET fetched_at = fetched_at - interval '1 day'"))
    fake = FakeLibraryData(popular={None: [NEW_BOOK]})
    result = run(ProviderEngine(seeded, Providers(library_data=fake)).popular_books(None))
    (_, (code, start, end, size)) = fake.calls[0]
    assert code is None and size == policy.POPULAR_SIZE
    assert end == today_kst() - timedelta(days=1) and (end - start).days == policy.POPULAR_PERIOD_DAYS - 1
    assert [b.isbn13 for b in result.books] == [NEW_BOOK.isbn13] and result.stale is False
    with seeded.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM popular_books_cache WHERE scope = 'national'")
        ).scalar_one() == 1


def test_popular_library_without_data_falls_back_to_national(seeded: Engine) -> None:
    [nslib] = _libs(seeded, "11170")  # 남산: 시드에 도서관별 인기 없음
    fake = FakeLibraryData(popular={"111002": []})
    result = run(ProviderEngine(seeded, Providers(library_data=fake)).popular_books(nslib))
    assert result.scope == "national" and result.fallback_reason == "no_data"


def test_popular_library_fetch_is_stored_with_label(seeded: Engine) -> None:
    [nslib] = _libs(seeded, "11170")
    fake = FakeLibraryData(popular={"111002": [NEW_BOOK, NEW_BOOK]})
    result = run(ProviderEngine(seeded, Providers(library_data=fake)).popular_books(nslib))
    assert result.scope == "library" and result.period_label == "남산도서관 · 최근 30일"
    assert [b.isbn13 for b in result.books] == [NEW_BOOK.isbn13]  # 같은 ISBN은 한 번
    again = run(ProviderEngine(seeded, Providers(library_data=fake)).popular_books(nslib))
    assert again.scope == "library" and len(fake.calls) == 1  # 3일 보관


def test_popular_failure_uses_stale_cache_or_fails(seeded: Engine) -> None:
    with seeded.begin() as conn:
        conn.execute(text("UPDATE popular_books_cache SET fetched_at = fetched_at - interval '2 days'"))
    broken = Providers(library_data=FakeLibraryData(popular={None: ProviderError("down")}))
    result = run(ProviderEngine(seeded, broken).popular_books(None))
    assert result.stale is True and result.fallback_reason == "provider_error"

    with seeded.begin() as conn:
        conn.execute(text("DELETE FROM popular_books_cache"))
    with pytest.raises(ApiError) as down:
        run(ProviderEngine(seeded, broken).popular_books(None))
    assert down.value.status_code == 503
    _fill_usage(seeded, "data4library", policy.DATA4LIBRARY_DAILY_LIMIT)
    with pytest.raises(ApiError) as limited:
        run(ProviderEngine(seeded, broken).popular_books(None))
    assert (limited.value.status_code, limited.value.code) == (429, "PROVIDER_LIMIT")


# ─────────────────── 도서관 목록 갱신 ───────────────────


def test_sync_libraries_inserts_updates_and_keeps_templates(seeded: Engine) -> None:
    jd = LibraryInfo(provider_lib_code="111001", name="정독도서관", address="새 주소", latitude=37.5, longitude=127.0)
    new = LibraryInfo(provider_lib_code="999001", name="새 도서관", latitude=None, longitude=None)
    fake = FakeLibraryData(libraries={"11110": [jd, new]})
    engine = ProviderEngine(seeded, Providers(library_data=fake))
    assert run(engine.sync_libraries(["11110"], page_size=1)) == {"inserted": 1, "updated": 1, "unchanged": 0}
    assert run(engine.sync_libraries(["11110"], page_size=1)) == {"inserted": 0, "updated": 0, "unchanged": 2}
    with seeded.connect() as conn:
        row = conn.execute(
            text("SELECT address, isbn_search_url_template FROM libraries WHERE provider_lib_code='111001'")
        ).one()
    assert row.address == "새 주소" and row.isbn_search_url_template  # 템플릿은 제공자가 덮지 않는다

    with pytest.raises(ApiError):
        run(ProviderEngine(seeded, Providers()).sync_libraries(["11110"]))


# ─────────────────── 실제 클라이언트 파서(127.0.0.1 임시 서버) ───────────────────


class _Server:
    def __init__(self, routes: dict[str, Any], delay: float = 0.0) -> None:
        self.requests: list[tuple[str, dict[str, list[str]], dict[str, str]]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                url = urlparse(self.path)
                outer.requests.append((url.path, parse_qs(url.query), dict(self.headers)))
                if delay:
                    time.sleep(delay)
                body = routes.get(url.path.rsplit("/", 1)[-1])
                if body is None:
                    self.send_response(500)
                    self.end_headers()
                    return
                raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, *args: Any) -> None:
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}/api"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def http_server() -> Iterator[Any]:
    servers: list[_Server] = []

    def _make(routes: dict[str, Any], delay: float = 0.0) -> _Server:
        server = _Server(routes, delay)
        servers.append(server)
        return server

    yield _make
    for server in servers:
        server.close()


@pytest.mark.parametrize(
    "result, expected",
    [
        ({"hasBook": "Y", "loanAvailable": "Y"}, ("yes", "yes")),
        ({"hasBook": "Y", "loanAvailable": "N"}, ("yes", "no")),
        ({"hasBook": "N", "loanAvailable": "N"}, ("no", "no")),
    ],
)
def test_data4library_book_exist_parsing(http_server: Any, result: dict, expected: tuple) -> None:
    server = http_server({"bookExist": {"response": {"result": result}}})
    holding = Data4LibraryClient("KEY", server.base, 2).book_exist("111001", FIRST_ISBN)
    assert (holding.holding, holding.loanable) == expected
    path, query, _ = server.requests[0]
    assert path.endswith("/bookExist") and query["libCode"] == ["111001"] and query["isbn13"] == [FIRST_ISBN]


@pytest.mark.parametrize(
    "body",
    [
        {"response": {"result": {"hasBook": "?", "loanAvailable": "Y"}}},  # 모르는 값을 no로 추측하지 않음
        {"response": {"result": {"hasBook": "Y"}}},
        {"response": {"error": "인증키 오류"}},
        {"unexpected": True},
        "not json",
    ],
)
def test_data4library_unexpected_shapes_are_provider_errors(http_server: Any, body: Any) -> None:
    server = http_server({"bookExist": body})
    with pytest.raises(ProviderError):
        Data4LibraryClient("KEY", server.base, 2).book_exist("111001", FIRST_ISBN)


def test_http_error_and_timeout_are_provider_errors(http_server: Any) -> None:
    with pytest.raises(ProviderError):
        Data4LibraryClient("KEY", http_server({}).base, 2).book_exist("1", FIRST_ISBN)  # 500
    slow = http_server({"bookExist": {"response": {"result": {"hasBook": "Y", "loanAvailable": "Y"}}}}, delay=1.0)
    started = time.monotonic()
    with pytest.raises(ProviderError):
        Data4LibraryClient("KEY", slow.base, 0.2).book_exist("1", FIRST_ISBN)
    assert time.monotonic() - started < 1.0


def test_data4library_popular_and_libraries_parsing(http_server: Any) -> None:
    server = http_server(
        {
            "loanItemSrch": {"response": {"docs": [
                {"doc": {"bookname": "소년이 온다", "authors": "한강", "isbn13": FIRST_ISBN,
                         "bookImageURL": "http://img.example/a.jpg"}},
                {"doc": {"bookname": "ISBN 없음", "isbn13": ""}},
            ]}},
            "libSrch": {"response": {"numFound": 1, "libs": [
                {"lib": {"libCode": "999", "libName": "새 도서관", "latitude": "37.1", "longitude": ""}},
            ]}},
        }
    )
    client = Data4LibraryClient("KEY", server.base, 2)
    [book] = client.popular(None, date(2026, 10, 1), date(2026, 10, 30), 20)
    assert (book.isbn13, book.cover_url) == (FIRST_ISBN, "https://img.example/a.jpg")
    libs, total = client.libraries("11110", 1, 100)
    assert total == 1 and libs[0].latitude is None and libs[0].longitude is None  # 짝이 안 맞으면 둘 다 비움


def test_naver_search_parsing_and_headers(http_server: Any) -> None:
    server = http_server(
        {
            "book.json": {"total": 2, "items": [
                {"title": "<b>소년</b>이 온다", "author": "한강^저자2", "isbn": "8936434128 9788936434120",
                 "publisher": "창비", "image": "https://img.example/b.jpg"},
                {"title": "ISBN 없는 책", "isbn": ""},
            ]},
            "book_adv.json": {"items": [{"title": "소년이 온다", "isbn": FIRST_ISBN}]},
        }
    )
    client = NaverBookClient("ID", "SECRET", server.base, 2)
    page = client.search("소년", 1, 20)
    assert page.total == 2 and [(b.title, b.author) for b in page.items] == [("소년이 온다", "한강, 저자2")]
    _, query, headers = server.requests[0]
    assert query["query"] == ["소년"] and headers["X-Naver-Client-Id"] == "ID"
    assert client.lookup_isbn(FIRST_ISBN) is not None
    assert client.lookup_isbn("9788954682152") is None  # 다른 ISBN만 오면 없음


def test_build_providers_only_with_keys() -> None:
    from app.settings import Settings

    base = {"app_env": "local", "database_url": "postgresql+psycopg://u:p@localhost:5433/x"}
    empty = pe.build_providers(Settings(**base))  # type: ignore[arg-type]
    assert empty.books is None and empty.library_data is None
    full = pe.build_providers(
        Settings(**base, data4library_api_key="k", naver_client_id="i", naver_client_secret="s")  # type: ignore[arg-type]
    )
    assert isinstance(full.books, NaverBookClient) and isinstance(full.library_data, Data4LibraryClient)
