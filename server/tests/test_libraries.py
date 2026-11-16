"""06 #10 도서관 목록(주변 반경·시군구), #11 도서관 하나(방문 헤더: 오늘 운영시간·휴관 계산). 인증 없음.

02 LIB-02(기본 3km, 설정 5km, 직선거리), VISIT-02, AC-LIB. 좌표는 쿼리로만 받는다(NFR-05).
"""

from datetime import date
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.main import create_app
from app.routers.libraries import closed_today, today_hours
from app.seed import seed_reference_data
from app.services.provider_engine import Providers
from app.settings import Settings
from tests.conftest import TEST_SUPABASE_URL

pytestmark = pytest.mark.usefixtures("clean_reference_tables")

JEONGDOK = (37.5806, 126.9830)  # 시드 정독도서관 좌표


@pytest.fixture
def client(test_db_url: str, fake_jwks_client: Mock, db_engine: Engine) -> Any:
    with db_engine.begin() as conn:
        seed_reference_data(conn)
    app = create_app(
        Settings(app_env="test", database_url=test_db_url, supabase_url=TEST_SUPABASE_URL),  # type: ignore[call-arg]
        jwks_client=fake_jwks_client,
        providers=Providers(),
    )
    with TestClient(app) as c:
        yield c


def _error(response: Any) -> tuple[int, str, str]:
    body = response.json()["error"]
    return response.status_code, body["code"], body["detail"]


def test_nearby_default_radius_is_3km_sorted_by_distance(client: TestClient) -> None:
    """AC-LIB: 기본 3km. 정독(0m) → 서울도서관(약 1.6km). 남산(약 3.1km)·마포는 밖."""
    response = client.get("/api/v1/libraries", params={"lat": JEONGDOK[0], "lng": JEONGDOK[1]})
    assert response.status_code == 200
    body = response.json()
    assert (body["mode"], body["radius_km"]) == ("nearby", 3)
    assert [i["name"] for i in body["items"]] == ["정독도서관", "서울도서관"]
    assert body["items"][0]["distance_m"] == 0
    assert 1_000 < body["items"][1]["distance_m"] < 3_000
    assert set(body["items"][0]) == {
        "id", "name", "address", "latitude", "longitude", "dtl_region_code", "distance_m",
    }


def test_nearby_5km_includes_more(client: TestClient) -> None:
    body = client.get(
        "/api/v1/libraries", params={"lat": JEONGDOK[0], "lng": JEONGDOK[1], "radius_km": 5}
    ).json()
    assert [i["name"] for i in body["items"]] == ["정독도서관", "서울도서관", "남산도서관"]


def test_region_lists_libraries_without_distance(client: TestClient) -> None:
    body = client.get("/api/v1/libraries", params={"dtl_region": "11440"}).json()
    assert body["mode"] == "region" and body["dtl_region"] == "11440"
    assert [(i["name"], i["distance_m"]) for i in body["items"]] == [("마포중앙도서관", None)]
    assert client.get("/api/v1/libraries", params={"dtl_region": "99999"}).json()["items"] == []


@pytest.mark.parametrize(
    "params, field",
    [
        ({}, "lat,lng"),
        ({"lat": 37.5}, "lng"),
        ({"lat": 37.5, "lng": 127, "radius_km": 4}, "radius_km"),
        ({"lat": 37.5, "lng": 127, "radius_km": "x"}, "radius_km"),
        ({"lat": 100, "lng": 127}, "lat"),
        ({"lat": "nan", "lng": 127}, "lat"),
        ({"dtl_region": "abc"}, "dtl_region"),
        ({"dtl_region": "11110", "lat": 37.5}, "dtl_region,lat,lng"),
    ],
)
def test_list_validation_errors(client: TestClient, params: dict, field: str) -> None:
    assert _error(client.get("/api/v1/libraries", params=params)) == (422, "VALIDATION_ERROR", field)


def test_detail_header_fields_and_today(client: TestClient) -> None:
    [lib] = client.get("/api/v1/libraries", params={"dtl_region": "11110"}).json()["items"]
    response = client.get(f"/api/v1/libraries/{lib['id']}", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 200  # 인증 없음: 헤더를 보지 않는다
    body = response.json()
    assert body["name"] == "정독도서관"
    assert body["closed_text"] == "매월 첫째·셋째 수요일, 법정공휴일"  # 원문은 그대로
    assert set(body["today"]) == {"date", "is_closed", "hours_text", "holiday_unchecked"}
    assert body["today"]["holiday_unchecked"] is True


def test_detail_not_found_and_bad_ids(client: TestClient) -> None:
    assert _error(client.get("/api/v1/libraries/999999"))[:2] == (404, "NOT_FOUND")
    assert _error(client.get("/api/v1/libraries/abc"))[:2] == (422, "VALIDATION_ERROR")
    assert _error(client.get(f"/api/v1/libraries/{2**63}"))[:2] == (422, "VALIDATION_ERROR")
    assert _error(client.get("/api/v1/libraries/0"))[:2] == (422, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "text, day, expected",
    [
        ("매월 첫째·셋째 수요일, 법정공휴일", date(2026, 11, 4), (True, True)),  # 첫째 수
        ("매월 첫째·셋째 수요일, 법정공휴일", date(2026, 11, 11), (False, True)),  # 둘째 수
        ("매월 첫째·셋째 수요일, 법정공휴일", date(2026, 11, 18), (True, True)),  # 셋째 수
        ("매주 월요일, 법정공휴일", date(2026, 11, 16), (True, True)),
        ("매주 월요일", date(2026, 11, 17), (False, False)),
        ("매월 마지막 월요일", date(2026, 11, 30), (True, False)),
        ("매월 마지막 월요일", date(2026, 11, 23), (False, False)),
        ("도서관 사정에 따라 임시 휴관", date(2026, 11, 16), (None, False)),  # 모르면 추측하지 않음
        ("매주 월요일, 도서관 사정에 따라", date(2026, 11, 16), (True, False)),
        (None, date(2026, 11, 16), (None, False)),
    ],
)
def test_closed_today_parser(text: str | None, day: date, expected: tuple) -> None:
    assert closed_today(text, day) == expected


@pytest.mark.parametrize(
    "text, day, expected",
    [
        ("평일 09:00~22:00 / 주말 09:00~17:00", date(2026, 11, 16), "09:00~22:00"),
        ("평일 09:00~22:00 / 주말 09:00~17:00", date(2026, 11, 21), "09:00~17:00"),
        ("화~금 09:00~21:00 / 주말 09:00~18:00", date(2026, 11, 16), None),  # 월요일은 규칙 없음
        ("화~일 09:00~22:00", date(2026, 11, 22), "09:00~22:00"),
        ("연중무휴", date(2026, 11, 16), None),
        (None, date(2026, 11, 16), None),
    ],
)
def test_today_hours_parser(text: str | None, day: date, expected: str | None) -> None:
    assert today_hours(text, day) == expected
