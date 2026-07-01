from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db as get_session
from app.core.deps import get_current_user_optional, require_current_user
from app.services.cache_ratelimit import (
    check_daily_quota,
    get_course_cache,
    get_idempotency_result,
    make_cache_key,
    record_request,
    set_course_cache,
)
from app.models.enums import BudgetTier, CompanionType, ThemeTag
from app.services.classifier import (
    InvalidQueryError,
    NeedsClarificationError,
    QueryClassification,
    classify_query,
)
from app.services.course_generator import (
    CourseGenerationError,
    generate_course,
    upsert_course,
)
from app.services.llm.base import LLMUnavailableError
from app.services.place_search import search_candidate_places

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/courses", tags=["recommend"])

# ---------------------------------------------------------------------------
# Placeholder texts: (temp_tier, weather_main) → list of examples
# Temp tiers: "cold"(<10°C), "cool"(10-20), "warm"(20-28), "hot"(≥28)
# Weather mains: "Clear", "Clouds", "Rain", "Snow", "other"
# ---------------------------------------------------------------------------
_PLACEHOLDERS: dict[tuple[str, str], list[str]] = {
    ("cold", "Clear"): [
        "예: 친구랑 강남역에서 따뜻한 카페 투어하다 저녁 먹고 싶어",
        "예: 혼자 홍대에서 핫초코 마시며 갤러리 구경하고 싶어",
    ],
    ("cold", "Clouds"): [
        "예: 커플이랑 신촌역 근처 실내 데이트 코스 짜줘",
        "예: 친구들이랑 건대입구에서 실내 놀거리 찾고 있어",
    ],
    ("cold", "Rain"): [
        "예: 비 오는 날 혼자 을지로에서 힙한 카페 탐방하고 싶어",
        "예: 커플이랑 비 피하면서 인사동에서 놀 수 있는 코스 추천해줘",
    ],
    ("cold", "Snow"): [
        "예: 눈 오는 날 여의도에서 낭만적인 데이트 코스 짜줘",
        "예: 친구들이랑 북촌에서 설경 구경하며 따뜻하게 먹을 곳 찾아줘",
    ],
    ("cool", "Clear"): [
        "예: 가족이랑 경복궁역에서 나들이 코스 짜줘. 애기도 있어",
        "예: 친구들이랑 한강공원 근처에서 피크닉하고 맛집 가고 싶어",
    ],
    ("cool", "Clouds"): [
        "예: 혼자 성수동에서 힙한 카페 투어하며 산책하고 싶어",
        "예: 커플이랑 이태원역에서 브런치 먹고 구경하고 싶어",
    ],
    ("cool", "Rain"): [
        "예: 비 오는 날 혼자 종로에서 조용히 책방 카페 탐방하고 싶어",
        "예: 친구랑 합정역에서 카페 돌다가 저녁 먹고 싶어",
    ],
    ("cool", "other"): [
        "예: 친구랑 마포구에서 오후 시간 알차게 보내고 싶어",
        "예: 혼자 강남 카페 투어하며 책 읽고 싶어",
    ],
    ("warm", "Clear"): [
        "예: 친구들이랑 홍대입구역에서 저녁 먹고 놀다가 집 가고 싶어. 예산 15000원",
        "예: 커플이랑 한강공원에서 선셋 보고 야경 즐기고 싶어",
    ],
    ("warm", "Clouds"): [
        "예: 혼자 성수역에서 힙한 공간 탐방하고 점심 먹고 싶어",
        "예: 가족이랑 잠실역 근처 놀이동산 말고 다른 코스 짜줘",
    ],
    ("warm", "Rain"): [
        "예: 비 와도 즐길 수 있는 신림역 데이트 코스 짜줘",
        "예: 비 오는 날 친구랑 강남에서 실내 액티비티 찾고 있어",
    ],
    ("warm", "other"): [
        "예: 친구들이랑 건대에서 점심 먹고 카페 갔다가 저녁도 먹고 싶어",
        "예: 커플이랑 낙산공원 근처에서 데이트하고 싶어",
    ],
    ("hot", "Clear"): [
        "예: 더운 날 친구랑 시원한 곳 위주로 신사역 코스 짜줘",
        "예: 혼자 강남역에서 냉방 잘 되는 카페 + 쇼핑 코스",
    ],
    ("hot", "Clouds"): [
        "예: 더운 날 커플이랑 실내 위주로 홍대 코스 짜줘",
        "예: 친구들이랑 에어컨 빵빵한 데서 놀 수 있는 코스 추천해줘",
    ],
    ("hot", "Rain"): [
        "예: 폭우에 갇혀도 즐길 수 있는 실내 코스 짜줘",
        "예: 여름 장마철에 커플이랑 홍대에서 실내 데이트",
    ],
    ("hot", "other"): [
        "예: 더운 여름 친구랑 시원하게 놀 수 있는 코스 추천해줘",
        "예: 커플이랑 실내 위주 데이트 코스 짜줘. 인당 30000원",
    ],
}

_DEFAULT_PLACEHOLDERS = [
    "예: 친구들이랑 학교 끝나고 홍대입구역에서 놀다가 저녁먹고 집 가고 싶어. 예산은 인당 15000원이야.",
    "예: 혼자 성수동에서 조용히 카페 투어하고 싶어",
    "예: 커플이랑 이태원에서 저녁 먹고 야경 보고 싶어",
]


def _temp_tier(temp_c: float) -> str:
    if temp_c < 10:
        return "cold"
    if temp_c < 20:
        return "cool"
    if temp_c < 28:
        return "warm"
    return "hot"


def _time_based_placeholders() -> list[str]:
    hour = datetime.now(timezone.utc).hour + 9  # KST
    hour %= 24
    if 6 <= hour < 11:
        return ["예: 친구랑 홍대에서 브런치 먹고 카페 투어하고 싶어"]
    if 11 <= hour < 15:
        return ["예: 점심 먹고 친구랑 성수동에서 오후 보내고 싶어"]
    if 15 <= hour < 19:
        return ["예: 퇴근하고 친구랑 강남에서 저녁 먹고 놀고 싶어"]
    return ["예: 친구들이랑 홍대에서 밤에 놀 수 있는 코스 짜줘"]


async def _fetch_weather() -> dict | None:
    """Fetch Seoul weather from OpenWeatherMap. Returns None on any failure."""
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "Seoul,KR", "appid": api_key, "units": "metric", "lang": "kr"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "temp": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "description": data["weather"][0]["description"],
                "main": data["weather"][0]["main"],
                "icon": data["weather"][0]["icon"],
            }
    except Exception as exc:
        logger.warning("Weather API failed: %s", exc)
        return None


class RecommendRequest(BaseModel):
    station_id: int | None = None
    query: str
    exclude_place_ids: list[int] = []
    parsed_input: dict | None = None  # pre-filled fields after NEEDS_CLARIFICATION


class PlaceDetail(BaseModel):
    order: int
    place_id: int
    name: str
    category: str | None = None
    address: str | None = None
    business_hours: Any | None = None
    price_range: str | None = None
    user_rating_avg: float | None = None
    user_rating_count: int = 0
    map_url: str | None = None
    thumbnail_url: str | None = None
    description: str = ""


class CourseResponse(BaseModel):
    course_id: int
    title: str
    description: str
    station_name: str | None = None
    theme_tags: list[str]
    places: list[PlaceDetail]
    total_walking_distance_km: float | None = None
    similar_top_courses: list[dict] = []
    served_from: str = "LLM"


@router.post("/recommend")
async def recommend(
    req: RecommendRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_current_user),
):
    user_id: int = current_user["id"]
    idempotency_key = request.headers.get("X-Idempotency-Key")

    # 1. Idempotency check — return previous result if same key used
    if idempotency_key:
        cached_course_id = await get_idempotency_result(session, user_id, idempotency_key)
        if cached_course_id is not None:
            cached = await _build_response_from_course_id(session, cached_course_id, served_from="CACHE")
            if cached:
                return {"success": True, "data": cached, "error": None}

    # 2. Daily quota check (only LLM calls count)
    allowed = await check_daily_quota(session, user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "QUOTA_EXCEEDED",
                "message": "오늘 추천 횟수(3회)를 모두 사용했어요. KST 자정에 초기화됩니다.",
            },
        )

    # 3. Classify (skip when FE provides pre-filled parsed_input after NEEDS_CLARIFICATION)
    if req.parsed_input is not None:
        classification = _build_classification_from_parsed_input(req.parsed_input)
    else:
        try:
            classification = await classify_query(req.query)
        except NeedsClarificationError as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "status": "NEEDS_CLARIFICATION",
                    "partial_parsed_input": e.partial_parsed_input,
                    "missing_fields": e.missing_fields,
                },
            )
        except InvalidQueryError as e:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_QUERY", "message": str(e)},
            )

    theme_tags = [t.value for t in classification.theme_tags]
    budget_tier = (
        classification.budget_tier.value
        if classification.budget_tier
        else "UNDER_30000"
    )
    companion_type = (
        classification.companion_type.value
        if classification.companion_type
        else "COUPLE"
    )

    # 4. Resolve station (D-20: location_mention → nearest supported station;
    #    unresolved falls back to NEEDS_CLARIFICATION instead of a hard error)
    station_id = req.station_id
    station_name_resolved: str | None = classification.station_name
    if station_id is None:
        station_row = (
            await _resolve_station(session, classification.station_name)
            if classification.station_name
            else None
        )
        if not station_row:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=200,
                content={
                    "status": "NEEDS_CLARIFICATION",
                    "partial_parsed_input": {
                        "theme_tags": theme_tags,
                        "budget_tier": budget_tier,
                        "companion_type": companion_type,
                        "head_count": classification.head_count,
                    },
                    "missing_fields": ["station_id"],
                },
            )
        station_id = station_row["station_id"]
        station_name_resolved = station_row["name"]

    # 5. Cache check (skip if exclude_place_ids specified — different context)
    cache_key = make_cache_key(station_id, req.query)
    if not req.exclude_place_ids:
        cache_hit = await get_course_cache(session, cache_key)
        if cache_hit:
            await record_request(
                session,
                user_id=user_id,
                station_id=station_id,
                query_text=req.query,
                served_from="CACHE",
                course_id=cache_hit.get("course_id"),
                idempotency_key=idempotency_key,
            )
            await session.commit()
            cache_hit["served_from"] = "CACHE"
            return {"success": True, "data": cache_hit, "error": None}

    # 6. Fetch candidates
    candidates = await search_candidate_places(
        session,
        station_id,
        theme_tags=theme_tags,
        exclude_place_ids=req.exclude_place_ids or None,
    )
    if not candidates:
        raise HTTPException(
            status_code=404,
            detail={"code": "NO_CANDIDATES", "message": "No places found near this station"},
        )

    # 7. Generate
    try:
        course = await generate_course(
            session=session,
            station_id=station_id,
            theme_tags=theme_tags,
            budget_tier=budget_tier,
            companion_type=companion_type,
            query_text=req.query,
            exclude_place_ids=req.exclude_place_ids or None,
            pre_fetched_candidates=candidates,
        )
    except CourseGenerationError as e:
        raise HTTPException(
            status_code=404,
            detail={"code": "NO_CANDIDATES", "message": str(e)},
        )
    except LLMUnavailableError as exc:
        logger.error("LLM unavailable after retries: %s", exc)
        fallback_courses = await _fetch_fallback_courses(session, station_id, theme_tags)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_UNAVAILABLE",
                "message": "AI 서비스가 잠시 바빠요. 잠시 후 다시 시도해주세요.",
                "fallback_courses": fallback_courses,
            },
        )

    if course is None:
        fallback_courses = await _fetch_fallback_courses(session, station_id, theme_tags)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_UNAVAILABLE",
                "message": "AI 서비스가 잠시 바빠요. 잠시 후 다시 시도해주세요.",
                "fallback_courses": fallback_courses,
            },
        )

    # 8. Persist
    course_id = await upsert_course(
        session=session,
        station_id=station_id,
        course=course,
        theme_tags=theme_tags,
        budget_tier=budget_tier,
        companion_type=companion_type,
        query_text=req.query,
        candidates=candidates,
    )

    # 9. Build response
    place_map = await _fetch_place_map(session, course.place_ids)
    places_out: list[PlaceDetail] = []
    for idx, pid in enumerate(course.place_ids):
        p = place_map.get(pid, {})
        rc = p.get("user_rating_count") or 0
        rs = p.get("user_rating_sum") or 0
        avg_rating = round(rs / 2.0 / rc, 1) if rc > 0 else None
        places_out.append(
            PlaceDetail(
                order=idx + 1,
                place_id=pid,
                name=p.get("name", ""),
                category=p.get("category"),
                address=p.get("address"),
                business_hours=p.get("business_hours"),
                price_range=p.get("price_range"),
                user_rating_avg=avg_rating,
                user_rating_count=rc,
                map_url=p.get("map_url"),
                thumbnail_url=p.get("thumbnail_url"),
                description=course.place_descriptions.get(pid, ""),
            )
        )

    response_data = CourseResponse(
        course_id=course_id,
        title=course.title,
        description=course.description,
        station_name=station_name_resolved or classification.station_name,
        theme_tags=theme_tags,
        places=places_out,
        total_walking_distance_km=None,
        similar_top_courses=[],
        served_from="LLM",
    ).model_dump()

    # 10. Store cache + record request
    if not req.exclude_place_ids:
        await set_course_cache(session, cache_key, response_data)
    await record_request(
        session,
        user_id=user_id,
        station_id=station_id,
        query_text=req.query,
        served_from="LLM",
        course_id=course_id,
        idempotency_key=idempotency_key,
    )
    await session.commit()

    return {"success": True, "data": response_data, "error": None}


async def _build_response_from_course_id(
    session: AsyncSession,
    course_id: int,
    served_from: str = "CACHE",
) -> dict | None:
    """Reconstruct a response dict from a persisted course_id."""
    course_row = (
        await session.execute(
            text("""
                SELECT c.course_id, c.theme_tags, c.station_id,
                       s.name AS station_name
                FROM courses c
                LEFT JOIN stations s ON s.station_id = c.station_id
                WHERE c.course_id = :cid
            """),
            {"cid": course_id},
        )
    ).mappings().first()
    if not course_row:
        return None

    place_rows = (
        await session.execute(
            text("""
                SELECT cp.visit_order, p.place_id, p.name, p.category, p.address,
                       p.business_hours, p.price_range, p.user_rating_sum,
                       p.user_rating_count, p.map_url, p.thumbnail_url,
                       cp.description
                FROM course_places cp
                JOIN places p ON p.place_id = cp.place_id
                WHERE cp.course_id = :cid
                ORDER BY cp.visit_order
            """),
            {"cid": course_id},
        )
    ).mappings().all()

    places_out = []
    for p in place_rows:
        rc = p["user_rating_count"] or 0
        rs = p["user_rating_sum"] or 0
        places_out.append({
            "order": p["visit_order"],
            "place_id": p["place_id"],
            "name": p["name"],
            "category": p["category"],
            "address": p["address"],
            "business_hours": p["business_hours"],
            "price_range": p["price_range"],
            "user_rating_avg": round(rs / 2.0 / rc, 1) if rc > 0 else None,
            "user_rating_count": rc,
            "map_url": p["map_url"],
            "thumbnail_url": p["thumbnail_url"],
            "description": p["description"] or "",
        })

    return {
        "course_id": course_id,
        "title": "",
        "description": "",
        "station_name": course_row["station_name"],
        "theme_tags": list(course_row["theme_tags"] or []),
        "places": places_out,
        "total_walking_distance_km": None,
        "similar_top_courses": [],
        "served_from": served_from,
    }


async def _resolve_station(session: AsyncSession, raw_name: str) -> dict | None:
    normalized = raw_name.rstrip("역").strip()
    for name, sql in [
        (raw_name,   "SELECT station_id, name FROM stations WHERE name = :name LIMIT 1"),
        (normalized, "SELECT station_id, name FROM stations WHERE name = :name LIMIT 1"),
        (raw_name,   "SELECT station_id, name FROM stations WHERE name LIKE :name LIMIT 1"),
        (normalized, "SELECT station_id, name FROM stations WHERE name LIKE :name LIMIT 1"),
    ]:
        query = name if "LIKE" not in sql else f"%{name}%"
        row = (await session.execute(text(sql), {"name": query})).mappings().first()
        if row:
            return dict(row)
    return None


async def _fetch_place_map(session: AsyncSession, place_ids: list[int]) -> dict[int, dict]:
    if not place_ids:
        return {}
    result = await session.execute(
        text("""
            SELECT place_id, name, category, address, business_hours,
                   price_range, user_rating_sum, user_rating_count,
                   map_url, thumbnail_url
            FROM places
            WHERE place_id = ANY(:ids)
        """),
        {"ids": place_ids},
    )
    return {row["place_id"]: dict(row) for row in result.mappings().all()}


async def _fetch_fallback_courses(
    session: AsyncSession,
    station_id: int,
    theme_tags: list[str],
    limit: int = 3,
) -> list[dict]:
    """Fetch popular courses from same station with similar themes for LLM fallback."""
    try:
        rows = (
            await session.execute(
                text("""
                    SELECT c.course_id, c.theme_tags, c.bayesian_score, c.rating_count,
                           s.name AS station_name,
                           (
                               SELECT COALESCE(json_agg(p.name ORDER BY cp.visit_order), '[]'::json)
                               FROM course_places cp
                               JOIN places p ON p.place_id = cp.place_id
                               WHERE cp.course_id = c.course_id
                           ) AS preview_places
                    FROM courses c
                    LEFT JOIN stations s ON s.station_id = c.station_id
                    WHERE c.station_id = :sid
                      AND c.theme_tags && CAST(:themes AS theme_tag[])
                    ORDER BY c.bayesian_score DESC, c.rating_count DESC
                    LIMIT :limit
                """),
                {
                    "sid": station_id,
                    "themes": "{" + ",".join(theme_tags) + "}" if theme_tags else "{}",
                    "limit": limit,
                },
            )
        ).mappings().all()

        return [
            {
                "course_id": r["course_id"],
                "station_name": r["station_name"],
                "theme_tags": list(r["theme_tags"] or []),
                "bayesian_score": float(r["bayesian_score"] or 0),
                "rating_count": r["rating_count"] or 0,
                "preview_places": r["preview_places"] if isinstance(r["preview_places"], list) else [],
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("Failed to fetch fallback courses: %s", exc)
        return []


# ---------------------------------------------------------------------------
# GET /v1/recommend/placeholder
# ---------------------------------------------------------------------------

placeholder_router = APIRouter(prefix="/v1/recommend", tags=["recommend"])


@placeholder_router.get("/placeholder")
async def get_placeholder(
    session: AsyncSession = Depends(get_session),
    current_user: dict | None = Depends(get_current_user_optional),
):
    """Return dynamic placeholder text and current Seoul weather.

    Fallback chain: OpenWeatherMap → time-based → static default.
    """
    weather = await _fetch_weather()

    if weather:
        tier = _temp_tier(weather["temp"])
        main = weather["main"] if weather["main"] in ("Clear", "Clouds", "Rain", "Snow") else "other"
        key = (tier, main)
        candidates = _PLACEHOLDERS.get(key) or _PLACEHOLDERS.get((tier, "other")) or _DEFAULT_PLACEHOLDERS
    else:
        candidates = _time_based_placeholders()

    # Recent queries for logged-in users
    recent_queries: list[str] = []
    if current_user:
        rows = (
            await session.execute(
                text("""
                    SELECT DISTINCT query_text
                    FROM courses
                    WHERE query_text IS NOT NULL
                    ORDER BY query_text
                    LIMIT 3
                """),
            )
        ).mappings().all()
        recent_queries = [r["query_text"] for r in rows if r["query_text"]]

    return {
        "success": True,
        "data": {
            "placeholders": candidates,
            "weather": weather,
            "recent_queries": recent_queries,
        },
        "error": None,
    }


def _build_classification_from_parsed_input(data: dict) -> "QueryClassification":
    theme_tags = []
    for t in data.get("theme_tags") or []:
        try:
            theme_tags.append(ThemeTag(t))
        except ValueError:
            pass

    budget_raw = data.get("budget_tier")
    budget_tier = None
    if budget_raw:
        try:
            budget_tier = BudgetTier(budget_raw)
        except ValueError:
            pass

    companion_raw = data.get("companion_type")
    companion_type = None
    if companion_raw:
        try:
            companion_type = CompanionType(companion_raw)
        except ValueError:
            pass

    raw_count = data.get("head_count")
    head_count = max(1, min(10, int(raw_count))) if raw_count else 2

    return QueryClassification(
        theme_tags=theme_tags,
        station_name=data.get("station_name") or None,
        budget_tier=budget_tier,
        companion_type=companion_type,
        head_count=head_count,
    )
