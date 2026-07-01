"""Station list (viewport bounds) and search endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db as get_session

router = APIRouter(prefix="/v1/stations", tags=["stations"])


class StationResult(BaseModel):
    station_id: int
    name: str
    lat: float
    lng: float
    lines: list[str] = []
    is_supported: bool = True


async def _fetch_lines(session: AsyncSession, station_ids: list[int]) -> dict[int, list[str]]:
    if not station_ids:
        return {}
    rows = await session.execute(
        text("SELECT station_id, line_no FROM station_lines WHERE station_id = ANY(:ids)"),
        {"ids": station_ids},
    )
    result: dict[int, list[str]] = {}
    for r in rows.mappings().all():
        result.setdefault(r["station_id"], []).append(r["line_no"])
    return result


# ---------------------------------------------------------------------------
# GET /v1/stations  — viewport bounds query (SCRUM-30)
# ---------------------------------------------------------------------------

@router.get("", response_model=list[StationResult])
async def list_stations(
    sw_lat: float | None = Query(default=None, description="남서 위도"),
    sw_lng: float | None = Query(default=None, description="남서 경도"),
    ne_lat: float | None = Query(default=None, description="북동 위도"),
    ne_lng: float | None = Query(default=None, description="북동 경도"),
    q: str = Query(default="", max_length=50, description="역명 검색어"),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    conditions = ["is_supported = true"]
    params: dict = {"limit": limit}

    if sw_lat is not None and sw_lng is not None and ne_lat is not None and ne_lng is not None:
        conditions.append(
            "geom && ST_MakeEnvelope(:sw_lng, :sw_lat, :ne_lng, :ne_lat, 4326)"
        )
        params.update({"sw_lat": sw_lat, "sw_lng": sw_lng, "ne_lat": ne_lat, "ne_lng": ne_lng})

    if q:
        conditions.append("name ILIKE '%' || :q || '%'")
        params["q"] = q

    where = " AND ".join(conditions)
    rows = await session.execute(
        text(f"""
            SELECT station_id, name, lat, lng, is_supported
            FROM stations
            WHERE {where}
            ORDER BY name
            LIMIT :limit
        """),
        params,
    )
    stations = [dict(r) for r in rows.mappings().all()]
    if not stations:
        return []

    lines_map = await _fetch_lines(session, [s["station_id"] for s in stations])
    for s in stations:
        s["lines"] = sorted(lines_map.get(s["station_id"], []))
    return stations


# ---------------------------------------------------------------------------
# GET /v1/stations/search  — name autocomplete (SCRUM-32)
# ---------------------------------------------------------------------------

@router.get("/search", response_model=list[StationResult])
async def search_stations(
    q: str = Query(default="", max_length=50, description="역명 검색어"),
    limit: int = Query(default=10, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text("""
            SELECT station_id, name, lat, lng, is_supported
            FROM stations
            WHERE is_supported = true
              AND (:q = '' OR name ILIKE '%' || :q || '%')
            ORDER BY name
            LIMIT :limit
        """),
        {"q": q, "limit": limit},
    )
    stations = [dict(r) for r in rows.mappings().all()]
    if not stations:
        return []

    lines_map = await _fetch_lines(session, [s["station_id"] for s in stations])
    for s in stations:
        s["lines"] = sorted(lines_map.get(s["station_id"], []))
    return stations


# ---------------------------------------------------------------------------
# GET /v1/stations/{station_id}  — single station detail
# ---------------------------------------------------------------------------

@router.get("/{station_id}", response_model=StationResult)
async def get_station(
    station_id: int,
    session: AsyncSession = Depends(get_session),
):
    row = (
        await session.execute(
            text("""
                SELECT station_id, name, lat, lng, is_supported
                FROM stations
                WHERE station_id = :sid
            """),
            {"sid": station_id},
        )
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "역을 찾을 수 없어요."})

    station = dict(row)
    lines_map = await _fetch_lines(session, [station_id])
    station["lines"] = sorted(lines_map.get(station_id, []))
    return station
