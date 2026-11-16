"""도서관 목록(06 #10)과 도서관 하나(06 #11, 방문 페이지 헤더). 인증 없음.

데이터는 조회 엔진(`app.services.provider_engine`)의 `libraries` 행만 읽는다(외부 호출 없음).
좌표는 거리 계산에만 쓰고 저장·로그하지 않는다(NFR-05).
"""

import re
from datetime import date
from typing import Any

from fastapi import APIRouter, Path, Query, Request

from app import policy
from app.common import ApiError, today_kst
from app.db import run_db
from app.services.provider_engine import (
    LibraryRow,
    get_library,
    libraries_in_region,
    libraries_nearby,
)

router = APIRouter(prefix="/api/v1/libraries")

MSG_VALIDATION = "요청 형식이 올바르지 않아요."
MSG_NOT_FOUND = "찾을 수 없어요."
DTL_REGION_PATTERN = r"^[0-9]{5}$"
BIGINT_MAX = 2**63 - 1  # libraries.id(bigint) 밖의 값은 DB 오류(500) 대신 422


def validation_error(*fields: str) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", MSG_VALIDATION, ",".join(sorted(fields)))


def check_radius(radius_km: int | None) -> int:
    if radius_km is None:
        return policy.NEARBY_DEFAULT_RADIUS_KM
    if radius_km not in policy.NEARBY_RADII_KM:
        raise validation_error("radius_km")
    return radius_km


def library_summary(lib: LibraryRow, distance_km: float | None) -> dict[str, Any]:
    return {
        "id": lib.id,
        "name": lib.name,
        "address": lib.address,
        "latitude": lib.latitude,
        "longitude": lib.longitude,
        "dtl_region_code": lib.dtl_region_code,
        "distance_m": round(distance_km * 1000) if distance_km is not None else None,
    }


# ─────────── 오늘 운영시간·휴관 계산(06 #11 "휴관 원문과 계산 결과", Q-22) ───────────
# 제공자 원문은 자유 문장이다. 아는 꼴만 계산하고 모르면 null(추측하지 않음). 원문은 그대로 함께 준다.

WEEKDAYS = "월화수목금토일"
ORDINALS = {"첫째": 1, "둘째": 2, "셋째": 3, "넷째": 4, "다섯째": 5, "마지막": -1}
_HOURS_RE = re.compile(r"^(?P<days>.*?)\s*(?P<open>\d{1,2}:\d{2})\s*[~\-–]\s*(?P<close>\d{1,2}:\d{2})")
_WEEKLY_RE = re.compile(r"매주\s*(?P<days>[월화수목금토일](?:\s*[·,]\s*[월화수목금토일])*)\s*요일")
_MONTHLY_RE = re.compile(
    r"매월\s*(?P<nths>(?:첫째|둘째|셋째|넷째|다섯째|마지막)(?:\s*[·,]\s*(?:첫째|둘째|셋째|넷째|다섯째|마지막))*)"
    r"\s*(?:주\s*)?(?P<day>[월화수목금토일])\s*요일"
)


def _parse_days(spec: str) -> set[int] | None:
    spec = spec.replace("요일", "").replace(" ", "")
    if not spec or spec == "매일":
        return set(range(7))
    days: set[int] = set()
    for part in re.split(r"[·,]", spec):
        if part == "평일":
            days |= {0, 1, 2, 3, 4}
        elif part == "주말":
            days |= {5, 6}
        elif re.fullmatch(r"[월화수목금토일]~[월화수목금토일]", part):
            start, end = WEEKDAYS.index(part[0]), WEEKDAYS.index(part[2])
            days |= set(range(start, end + 1)) if start <= end else set()
        elif part in WEEKDAYS and len(part) == 1:
            days.add(WEEKDAYS.index(part))
        else:
            return None
    return days or None


def today_hours(operating_time_text: str | None, today: date) -> str | None:
    """"평일 09:00~22:00 / 주말 09:00~17:00" 꼴에서 오늘 시간. 못 읽으면 None."""
    if not operating_time_text:
        return None
    for segment in re.split(r"[/\n,]", operating_time_text):
        match = _HOURS_RE.match(segment.strip())
        if not match:
            continue
        days = _parse_days(match.group("days"))
        if days is not None and today.weekday() in days:
            return f"{match.group('open')}~{match.group('close')}"
    return None


def _nth_weekday_matches(today: date, nths: list[int], weekday: int) -> bool:
    if today.weekday() != weekday:
        return False
    nth = (today.day - 1) // 7 + 1
    is_last = (today.day + 7) > _days_in_month(today)
    return nth in nths or (-1 in nths and is_last)


def _days_in_month(day: date) -> int:
    following = date(day.year + (day.month == 12), day.month % 12 + 1, 1)
    return (following - date(day.year, day.month, 1)).days


def closed_today(closed_text: str | None, today: date) -> tuple[bool | None, bool]:
    """(오늘 휴관인지, 공휴일 규칙이 있어 확인하지 못했는지).

    아는 규칙(매주 X요일, 매월 N째 X요일)에 오늘이 걸리면 True. 모르는 문장이 하나라도 있으면 None.
    "공휴일"은 달력을 보지 않으므로 계산에서 빼고 두 번째 값으로 알린다.
    """
    if not closed_text:
        return None, False
    holiday_rule = "공휴일" in closed_text
    unknown = False
    for clause in re.split(r"[,/\n]", closed_text):
        clause = clause.strip()
        if not clause:
            continue
        weekly, monthly = _WEEKLY_RE.search(clause), _MONTHLY_RE.search(clause)
        if weekly:
            if today.weekday() in {WEEKDAYS.index(d) for d in re.findall(r"[월화수목금토일]", weekly.group("days"))}:
                return True, holiday_rule
        elif monthly:
            nths = [ORDINALS[n] for n in re.findall(r"첫째|둘째|셋째|넷째|다섯째|마지막", monthly.group("nths"))]
            if _nth_weekday_matches(today, nths, WEEKDAYS.index(monthly.group("day"))):
                return True, holiday_rule
        elif "공휴일" in clause:
            continue
        else:
            unknown = True
    return (None if unknown else False), holiday_rule


# ─────────── 엔드포인트 ───────────


@router.get("")
async def list_libraries(
    request: Request,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: int | None = Query(None),
    dtl_region: str | None = Query(None, pattern=DTL_REGION_PATTERN),
) -> Any:
    engine = request.app.state.engine
    if dtl_region is not None:
        if lat is not None or lng is not None or radius_km is not None:
            raise validation_error("dtl_region", "lat", "lng")
        libs = await run_db(engine, lambda c: libraries_in_region(c, dtl_region))
        return {
            "mode": "region",
            "radius_km": None,
            "dtl_region": dtl_region,
            "items": [library_summary(lib, None) for lib in libs],
        }
    if lat is None or lng is None:
        raise validation_error(*(["lat"] if lat is None else []), *(["lng"] if lng is None else []))
    radius = check_radius(radius_km)
    found = await run_db(engine, lambda c: libraries_nearby(c, lat, lng, radius))
    return {
        "mode": "nearby",
        "radius_km": radius,
        "dtl_region": None,
        "items": [library_summary(lib, d) for lib, d in found],
    }


@router.get("/{library_id}")
async def library_detail(request: Request, library_id: int = Path(ge=1, le=BIGINT_MAX)) -> Any:
    lib = await run_db(request.app.state.engine, lambda c: get_library(c, library_id))
    if lib is None:
        raise ApiError(404, "NOT_FOUND", MSG_NOT_FOUND)
    today = today_kst()
    is_closed, holiday_unchecked = closed_today(lib.closed_text, today)
    return {
        "id": lib.id,
        "name": lib.name,
        "address": lib.address,
        "tel": lib.tel,
        "homepage": lib.homepage,
        "latitude": lib.latitude,
        "longitude": lib.longitude,
        "dtl_region_code": lib.dtl_region_code,
        "operating_time_text": lib.operating_time_text,
        "closed_text": lib.closed_text,
        "today": {
            "date": today.isoformat(),
            "is_closed": is_closed,
            "hours_text": None if is_closed else today_hours(lib.operating_time_text, today),
            "holiday_unchecked": holiday_unchecked,
        },
    }
