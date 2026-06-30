from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db as get_session
from app.services.classifier import InvalidQueryError, classify_query
from app.services.course_generator import (
    CourseGenerationError,
    generate_course,
    upsert_course,
)
from app.services.place_search import search_candidate_places

router = APIRouter(prefix="/v1/courses", tags=["recommend"])


class RecommendRequest(BaseModel):
    station_id: int | None = None
    query: str
    exclude_place_ids: list[int] = []


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
):
    # 1. Classify
    try:
        classification = await classify_query(req.query)
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

    return {
        "success": True,
        "data": CourseResponse(
            course_id=course_id,
            title=course.title,
            description=course.description,
            station_name=station_name_resolved or classification.station_name,
            theme_tags=theme_tags,
            places=places_out,
            total_walking_distance_km=None,
            similar_top_courses=[],
            served_from="LLM",
        ).model_dump(),
        "error": None,
    }


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
