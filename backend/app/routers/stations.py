from fastapi import APIRouter, Depends, Query
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


@router.get("", response_model=list[StationResult])
async def search_stations(
    q: str = Query(default="", max_length=50),
    limit: int = Query(default=10, le=30),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        text("""
            SELECT station_id, name, lat, lng
            FROM stations
            WHERE is_supported = true
              AND (:q = '' OR name ILIKE '%' || :q || '%')
            ORDER BY name
            LIMIT :limit
        """),
        {"q": q, "limit": limit},
    )
    return [dict(r) for r in rows.mappings().all()]
