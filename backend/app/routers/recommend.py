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
    station_id: int
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

    # 2. Fetch candidates (shared between generate + upsert)
    candidates = await search_candidate_places(
        session,
        req.station_id,
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
            station_id=req.station_id,
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
        station_id=req.station_id,
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
            theme_tags=theme_tags,
            places=places_out,
            total_walking_distance_km=None,
            similar_top_courses=[],
            served_from="LLM",
        ).model_dump(),
        "error": None,
    }


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
