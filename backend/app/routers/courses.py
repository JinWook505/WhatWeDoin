"""Course list and detail endpoints."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.category_labels import place_category_label
from app.models.enums import BudgetTier, CompanionType, ThemeTag

router = APIRouter(prefix="/v1/courses", tags=["courses"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50

# Korean labels for SEO-facing OG title/description (D-24). Keep in sync with
# frontend/src/lib/enumOptions.ts — API responses still return raw enum codes.
_THEME_TAG_KO = {
    "FOOD": "맛집", "CAFE": "카페", "BAR": "술집", "BOARD_GAME": "보드게임",
    "KARAOKE": "노래방", "ARCADE": "오락", "PARK": "공원", "CULTURE": "전시/문화",
    "SHOPPING": "쇼핑", "NIGHT_VIEW": "야경", "MOVIE": "영화", "ACTIVITY": "액티비티",
}


# ---------------------------------------------------------------------------
# Cursor helpers (keyset: bayesian_score DESC, course_id DESC)
# ---------------------------------------------------------------------------

def _encode_cursor(bayesian_score: float, course_id: int) -> str:
    payload = json.dumps({"bs": float(bayesian_score), "id": course_id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[float, int] | None:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return float(payload["bs"]), int(payload["id"])
    except Exception:
        return None


# ---------------------------------------------------------------------------
# GET /v1/courses
# ---------------------------------------------------------------------------

@router.get("")
async def list_courses(
    station_id: int | None = Query(default=None),
    theme: list[str] = Query(default=[]),
    companion_type: str | None = Query(default=None),
    head_count: int | None = Query(default=None),
    budget_tier: str | None = Query(default=None),
    sort: str = Query(default="score", pattern="^(score|recent)$"),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit + 1}

    if station_id is not None:
        conditions.append("c.station_id = :station_id")
        params["station_id"] = station_id

    if theme:
        for t in theme:
            if t not in ThemeTag._value2member_map_:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INVALID_THEME", "message": f"'{t}'는 유효한 테마가 아니에요."},
                )
        # asyncpg cannot bind a Python str to an ARRAY(enum) target via :param —
        # values are validated against ThemeTag above, so inlining as literals is safe
        # (see course_generator.py / users.py for the same established pattern).
        tag_literals = ", ".join(f"'{t}'::theme_tag" for t in theme)
        conditions.append(f"c.theme_tags && ARRAY[{tag_literals}]")

    if companion_type:
        if companion_type not in CompanionType._value2member_map_:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_COMPANION_TYPE", "message": f"'{companion_type}'는 유효한 동행 유형이 아니에요."},
            )
        conditions.append("c.companion_type = CAST(:companion_type AS companion_type)")
        params["companion_type"] = companion_type

    if head_count is not None:
        conditions.append("c.head_count = :head_count")
        params["head_count"] = head_count

    if budget_tier:
        if budget_tier not in BudgetTier._value2member_map_:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_BUDGET_TIER", "message": f"'{budget_tier}'는 유효한 예산대가 아니에요."},
            )
        conditions.append("c.budget_tier = CAST(:budget_tier AS budget_tier)")
        params["budget_tier"] = budget_tier

    # Cursor-based keyset pagination
    if cursor:
        decoded = _decode_cursor(cursor)
        if decoded is None:
            raise HTTPException(status_code=400, detail={"code": "INVALID_CURSOR", "message": "잘못된 커서입니다."})
        bs, cid = decoded
        if sort == "score":
            conditions.append("(c.bayesian_score, c.course_id) < (:cursor_bs, :cursor_id)")
        else:
            conditions.append("c.course_id < :cursor_id")
        params["cursor_bs"] = bs
        params["cursor_id"] = cid

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    if sort == "score":
        order_sql = "ORDER BY c.bayesian_score DESC, c.rating_count DESC, c.course_id DESC"
    else:
        order_sql = "ORDER BY c.course_id DESC"

    sql = text(f"""
        SELECT
            c.course_id,
            c.station_id,
            s.name AS station_name,
            c.theme_tags,
            c.budget_tier,
            c.companion_type,
            c.head_count,
            c.bayesian_score,
            c.rating_count,
            c.total_walking_distance_km,
            c.created_at,
            (
                SELECT COALESCE(json_agg(p.name ORDER BY cp.stage_order), '[]'::json)
                FROM course_places cp
                JOIN places p ON p.place_id = cp.place_id
                WHERE cp.course_id = c.course_id AND cp.option_index = 1
            ) AS preview_places
        FROM courses c
        LEFT JOIN stations s ON s.station_id = c.station_id
        {where_sql}
        {order_sql}
        LIMIT :limit
    """)

    rows = (await db.execute(sql, params)).mappings().all()

    has_next = len(rows) > limit
    items = list(rows[:limit])

    next_cursor = None
    if has_next:
        last = items[-1]
        next_cursor = _encode_cursor(float(last["bayesian_score"]), last["course_id"])

    courses_out = []
    for row in items:
        preview = row["preview_places"]
        if isinstance(preview, str):
            preview = json.loads(preview)

        courses_out.append({
            "course_id": row["course_id"],
            "station_id": row["station_id"],
            "station_name": row["station_name"],
            "theme_tags": list(row["theme_tags"] or []),
            "budget_tier": row["budget_tier"],
            "companion_type": row["companion_type"],
            "head_count": row["head_count"],
            "bayesian_score": float(row["bayesian_score"] or 0),
            "rating_count": row["rating_count"] or 0,
            "total_walking_distance_km": (
                float(row["total_walking_distance_km"])
                if row["total_walking_distance_km"] is not None
                else None
            ),
            "preview_places": preview or [],
            "created_at": str(row["created_at"]) if row["created_at"] else None,
        })

    return {
        "success": True,
        "data": {
            "courses": courses_out,
            "next_cursor": next_cursor,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# GET /v1/courses/{course_id}
# ---------------------------------------------------------------------------

_STALE_DAYS = 30


@router.get("/{course_id}")
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
):
    course_row = (
        await db.execute(
            text("""
                SELECT
                    c.course_id, c.station_id, c.theme_tags, c.budget_tier,
                    c.companion_type, c.head_count, c.total_walking_distance_km,
                    c.bayesian_score, c.rating_count, c.rating_sum, c.created_at,
                    s.name AS station_name
                FROM courses c
                LEFT JOIN stations s ON s.station_id = c.station_id
                WHERE c.course_id = :cid
            """),
            {"cid": course_id},
        )
    ).mappings().first()

    if not course_row:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "코스를 찾을 수 없어요."},
        )

    # Places (grouped by stage_order, ordered by option_index within a stage)
    place_rows = (
        await db.execute(
            text("""
                SELECT
                    cp.stage_order, cp.option_index, cp.stage_label,
                    cp.place_id, cp.description,
                    cp.walking_distance_from_station_km,
                    p.name, p.category, p.address, p.lat, p.lng,
                    p.price_range, p.business_hours, p.map_url,
                    p.user_rating_sum, p.user_rating_count,
                    p.status, p.last_synced_at
                FROM course_places cp
                JOIN places p ON p.place_id = cp.place_id
                WHERE cp.course_id = :cid
                ORDER BY cp.stage_order, cp.option_index
            """),
            {"cid": course_id},
        )
    ).mappings().all()

    now = datetime.now(timezone.utc)
    is_stale = False
    has_closed = False
    stages_by_order: dict[int, dict] = {}
    first_option_names: list[str] = []

    for p in place_rows:
        # Freshness check
        if p["last_synced_at"]:
            synced = p["last_synced_at"]
            if hasattr(synced, "tzinfo") and synced.tzinfo is None:
                synced = synced.replace(tzinfo=timezone.utc)
            elif isinstance(synced, str):
                synced = datetime.fromisoformat(synced)
            if (now - synced).days > _STALE_DAYS:
                is_stale = True

        if p["status"] == "CLOSED":
            has_closed = True

        rc = p["user_rating_count"] or 0
        rs = p["user_rating_sum"] or 0
        avg_rating = round(rs / 2.0 / rc, 1) if rc > 0 else None

        business_hours = p["business_hours"]
        if isinstance(business_hours, str):
            try:
                business_hours = json.loads(business_hours)
            except Exception:
                business_hours = None

        dist = p["walking_distance_from_station_km"]
        stage = stages_by_order.setdefault(
            p["stage_order"],
            {"stage_order": p["stage_order"], "stage_label": p["stage_label"], "options": []},
        )
        stage["options"].append({
            "place_id": p["place_id"],
            "name": p["name"],
            "category": place_category_label(p["category"]),
            "address": p["address"],
            "lat": float(p["lat"]) if p["lat"] else None,
            "lng": float(p["lng"]) if p["lng"] else None,
            "price_range": p["price_range"],
            "business_hours": business_hours,
            "map_url": p["map_url"],
            "user_rating_avg": avg_rating,
            "user_rating_count": rc,
            "status": p["status"],
            "description": p["description"] or "",
            "walking_distance_from_station_km": float(dist) if dist is not None else None,
        })
        if p["option_index"] == 1:
            first_option_names.append(p["name"])

    stages_out = [stages_by_order[k] for k in sorted(stages_by_order)]

    # Review summary
    n = course_row["rating_count"] or 0
    s = course_row["rating_sum"] or 0
    avg_score = round(s / n, 1) if n > 0 else None
    bayesian = float(course_row["bayesian_score"] or 0)

    # OG tags
    theme_str = " + ".join(_THEME_TAG_KO.get(t, t) for t in list(course_row["theme_tags"] or [])[:3])
    preview_names = " → ".join(first_option_names[:3])
    station_name = course_row["station_name"] or f"역{course_row['station_id']}"

    og_title = f"{station_name}역 | {theme_str} 코스"
    og_desc_parts = [preview_names]
    if avg_score:
        og_desc_parts.append(f"★ {avg_score}점")
    og_description = " · ".join(og_desc_parts)

    return {
        "success": True,
        "data": {
            "course_id": course_row["course_id"],
            "station_id": course_row["station_id"],
            "station_name": station_name,
            "theme_tags": list(course_row["theme_tags"] or []),
            "budget_tier": course_row["budget_tier"],
            "companion_type": course_row["companion_type"],
            "head_count": course_row["head_count"],
            "stages": stages_out,
            "bayesian_score": bayesian,
            "avg_score": avg_score,
            "rating_count": n,
            "is_stale": is_stale,
            "has_closed": has_closed,
            "created_at": str(course_row["created_at"]) if course_row["created_at"] else None,
            "og": {
                "title": og_title,
                "description": og_description,
                "image_url": None,  # V2: OG 이미지 자동생성
            },
        },
        "error": None,
    }
