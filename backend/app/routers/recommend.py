from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db as get_session
from app.core.deps import require_current_user
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
from app.services.cache_ratelimit import (
    build_cache_key,
    check_user_daily_ratelimit,
    get_cached_course,
    record_recommendation_request,
    set_cached_course,
)
from app.services.llm import LLMUnavailableError
from app.services.place_search import search_candidate_places

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/courses", tags=["recommend"])


class RecommendRequest(BaseModel):
    station_id: int | None = None
    query: str
    exclude_place_ids: list[int] = []
    parsed_input: dict | None = None  # pre-filled classification for re-request after NEEDS_CLARIFICATION


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
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(require_current_user),
):
    # 0. Daily rate-limit check (SCRUM-39)
    user_id = current_user["id"]
    if not await check_user_daily_ratelimit(session, user_id):
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "오늘 AI 추천 횟수를 모두 사용했어요. KST 자정에 초기화됩니다.",
                "retry_after": "tomorrow",
            },
        )

    # 1. Classify — skip if pre-filled parsed_input provided (re-request after NEEDS_CLARIFICATION)
    if req.parsed_input is not None:
        classification = _build_classification_from_parsed_input(req.parsed_input)
    else:
        try:
            classification = await classify_query(req.query)
        except NeedsClarificationError as e:
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
        except LLMUnavailableError as e:
            logger.error("LLM unavailable during classification: %s", e)
            fallback = await _get_fallback_courses(session, req.station_id, [])
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "LLM_UNAVAILABLE",
                    "message": "AI 서비스에 일시적인 문제가 있어요. 잠시 후 다시 시도해 주세요.",
                    "retry_after": 30,
                    "fallback_courses": fallback,
                },
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

    # 1b. Resolve station_id — from request body or classifier-extracted name
    station_id = req.station_id
    station_name_resolved: str | None = classification.station_name
    if station_id is None:
        if not classification.station_name:
            raise HTTPException(
                status_code=400,
                detail={"code": "NO_STATION", "message": "어느 역 근처인지 알 수 없어요. 동네나 역 이름을 함께 알려주세요!"},
            )
        station_row = await _resolve_station(session, classification.station_name)
        if not station_row:
            raise HTTPException(
                status_code=404,
                detail={"code": "STATION_NOT_FOUND", "message": f"'{classification.station_name}' 근처 역을 찾을 수 없어요."},
            )
        station_id = station_row["station_id"]
        station_name_resolved = station_row["name"]

    # 1c. Cache lookup (SCRUM-39) — after station & params resolved
    cache_key = build_cache_key(station_id, theme_tags, budget_tier, companion_type)
    if not req.exclude_place_ids:  # skip cache when exclusions active
        cached = await get_cached_course(session, cache_key)
        if cached:
            await record_recommendation_request(
                session,
                user_id=user_id,
                station_id=station_id,
                query_text=req.query,
                parsed_input=None,
                exclude_place_ids=[],
                served_from="CACHE",
                idempotency_key=None,
                course_id=cached.get("course_id"),
            )
            await session.commit()
            return {"success": True, "data": {**cached, "served_from": "CACHE"}, "error": None}

    # 2. Fetch candidates (shared between generate + upsert)
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

    # 3. Generate course (skip internal candidate re-fetch via pre_fetched_candidates)
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
    except LLMUnavailableError as e:
        logger.error("LLM unavailable during course generation: %s", e)
        fallback = await _get_fallback_courses(session, station_id, theme_tags)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_UNAVAILABLE",
                "message": "AI 서비스에 일시적인 문제가 있어요. 잠시 후 다시 시도해 주세요.",
                "retry_after": 30,
                "fallback_courses": fallback,
            },
        )

    if course is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "GENERATION_FAILED", "message": "LLM failed to generate a valid course"},
        )

    # 4. Persist
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

    # 4b. Record LLM request (SCRUM-39)
    await record_recommendation_request(
        session,
        user_id=user_id,
        station_id=station_id,
        query_text=req.query,
        parsed_input=req.parsed_input,
        exclude_place_ids=req.exclude_place_ids,
        served_from="LLM",
        idempotency_key=None,
        course_id=course_id,
    )

    # 5. Fetch place details for response
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

    course_out = CourseResponse(
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

    # Store in cache for future requests with same params (SCRUM-39)
    if not req.exclude_place_ids:
        await set_cached_course(session, cache_key, course_out)

    await session.commit()
    return {"success": True, "data": course_out, "error": None}


async def _resolve_station(session: AsyncSession, raw_name: str) -> dict | None:
    """Try progressively looser matches to find a station by name.

    1. Exact match
    2. After stripping trailing '역'
    3. LIKE %name% (partial)
    4. LIKE %normalized% (partial, '역' stripped)
    """
    normalized = raw_name.rstrip("역").strip()

    for name, sql in [
        (raw_name,    "SELECT station_id, name FROM stations WHERE name = :name LIMIT 1"),
        (normalized,  "SELECT station_id, name FROM stations WHERE name = :name LIMIT 1"),
        (raw_name,    "SELECT station_id, name FROM stations WHERE name LIKE :name LIMIT 1"),
        (normalized,  "SELECT station_id, name FROM stations WHERE name LIKE :name LIMIT 1"),
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


async def _get_fallback_courses(
    session: AsyncSession,
    station_id: int | None,
    theme_tags: list[str],
    limit: int = 3,
) -> list[dict]:
    """Return top-rated courses for the same station / similar theme as a fallback."""
    params: dict[str, Any] = {"limit": limit}
    conditions = []

    if station_id is not None:
        conditions.append("c.station_id = :station_id")
        params["station_id"] = station_id

    if theme_tags:
        conditions.append("c.theme_tags && CAST(:themes AS theme_tag[])")
        params["themes"] = "{" + ",".join(theme_tags) + "}"

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = text(f"""
        SELECT
            c.course_id,
            s.name AS station_name,
            c.theme_tags,
            c.bayesian_score,
            c.rating_count,
            (
                SELECT COALESCE(json_agg(p.name ORDER BY cp.visit_order), '[]'::json)
                FROM course_places cp
                JOIN places p ON p.place_id = cp.place_id
                WHERE cp.course_id = c.course_id
            ) AS preview_places
        FROM courses c
        LEFT JOIN stations s ON s.station_id = c.station_id
        {where_sql}
        ORDER BY c.bayesian_score DESC, c.rating_count DESC, c.course_id DESC
        LIMIT :limit
    """)

    try:
        rows = (await session.execute(sql, params)).mappings().all()
        result = []
        for row in rows:
            import json as _json
            preview = row["preview_places"]
            if isinstance(preview, str):
                preview = _json.loads(preview)
            result.append({
                "course_id": row["course_id"],
                "station_name": row["station_name"],
                "theme_tags": list(row["theme_tags"] or []),
                "bayesian_score": float(row["bayesian_score"] or 0),
                "preview_places": preview or [],
            })
        return result
    except Exception:
        logger.exception("Failed to fetch fallback courses")
        return []


def _build_classification_from_parsed_input(data: dict) -> QueryClassification:
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
    station_name = data.get("station_name") or None

    return QueryClassification(
        theme_tags=theme_tags,
        station_name=station_name,
        budget_tier=budget_tier,
        companion_type=companion_type,
        head_count=head_count,
    )
