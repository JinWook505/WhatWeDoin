"""Course list and detail endpoints."""
from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db

router = APIRouter(prefix="/v1/courses", tags=["courses"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


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
        conditions.append("c.theme_tags && CAST(:themes AS theme_tag[])")
        params["themes"] = "{" + ",".join(theme) + "}"

    if companion_type:
        conditions.append("c.companion_type = CAST(:companion_type AS companion_type)")
        params["companion_type"] = companion_type

    if head_count is not None:
        conditions.append("c.head_count = :head_count")
        params["head_count"] = head_count

    if budget_tier:
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
                SELECT COALESCE(json_agg(p.name ORDER BY cp.visit_order), '[]'::json)
                FROM course_places cp
                JOIN places p ON p.place_id = cp.place_id
                WHERE cp.course_id = c.course_id
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
