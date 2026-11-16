"""시험용 가짜 외부 제공자(CI는 외부 네트워크를 쓰지 않는다, H-ARCH-07).

결과 대신 예외 인스턴스를 넣으면 그 예외를 던진다. `on_call`은 호출 순간의 상태(트랜잭션 밖인지 등)를 단언할 때 쓴다.
"""

from collections.abc import Callable
from datetime import date
from typing import Any

from app.services.provider_engine import BookInfo, HoldingResult, LibraryInfo, SearchPage


def _maybe_raise(value: Any) -> Any:
    if isinstance(value, BaseException):
        raise value
    return value


class FakeBookSearch:
    def __init__(
        self,
        books: list[BookInfo] | None = None,
        *,
        error: BaseException | None = None,
        total: int | None = None,
        on_call: Callable[[], None] | None = None,
    ) -> None:
        self.books = books or []
        self.error = error
        self.total = total
        self.on_call = on_call
        self.calls: list[tuple[str, Any]] = []

    def _enter(self, name: str, arg: Any) -> None:
        self.calls.append((name, arg))
        if self.on_call:
            self.on_call()
        if self.error is not None:
            raise self.error

    def search(self, query: str, start: int, display: int) -> SearchPage:
        self._enter("search", (query, start, display))
        matched = [b for b in self.books if query in b.title or (b.author and query in b.author)]
        return SearchPage(
            items=matched[start - 1 : start - 1 + display],
            total=self.total if self.total is not None else len(matched),
        )

    def lookup_isbn(self, isbn13: str) -> BookInfo | None:
        self._enter("lookup", isbn13)
        return next((b for b in self.books if b.isbn13 == isbn13), None)


class FakeLibraryData:
    def __init__(
        self,
        *,
        holdings: dict[str, HoldingResult | BaseException] | None = None,
        default_holding: HoldingResult | BaseException | None = None,
        popular: dict[str | None, list[BookInfo] | BaseException] | None = None,
        libraries: dict[str, list[LibraryInfo]] | None = None,
        on_call: Callable[[], None] | None = None,
    ) -> None:
        self.holdings = holdings or {}
        self.default_holding = default_holding
        self.popular_by_code = popular or {}
        self.libraries_by_region = libraries or {}
        self.on_call = on_call
        self.calls: list[tuple[str, Any]] = []

    def _enter(self, name: str, arg: Any) -> None:
        self.calls.append((name, arg))
        if self.on_call:
            self.on_call()

    def book_exist(self, lib_code: str, isbn13: str) -> HoldingResult:
        self._enter("book_exist", (lib_code, isbn13))
        value = self.holdings.get(lib_code, self.default_holding)
        if value is None:
            raise AssertionError(f"준비하지 않은 도서관 {lib_code}")
        return _maybe_raise(value)

    def popular(self, lib_code: str | None, start: date, end: date, size: int) -> list[BookInfo]:
        self._enter("popular", (lib_code, start, end, size))
        return _maybe_raise(self.popular_by_code.get(lib_code, []))

    def libraries(self, dtl_region: str, page: int, size: int) -> tuple[list[LibraryInfo], int]:
        self._enter("libraries", (dtl_region, page, size))
        libs = self.libraries_by_region.get(dtl_region, [])
        return libs[(page - 1) * size : page * size], len(libs)
