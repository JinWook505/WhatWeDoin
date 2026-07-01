import hashlib
from collections import defaultdict
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.place import Place
from app.models.place_report import PlaceRatingReport

router = APIRouter(prefix="/v1/places", tags=["places"])

# MVP 인메모리 레이트리밋: {"{ip_hash}:{date}": count}
_rate_counters: dict[str, int] = defaultdict(int)
_RATE_LIMIT_DAILY = 10


def _ip_hash(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _check_rate_limit(ip_hash: str) -> None:
    key = f"{ip_hash}:{date.today()}"
    if _rate_counters[key] >= _RATE_LIMIT_DAILY:
        raise HTTPException(status_code=429, detail="RATE_LIMIT_EXCEEDED")
    _rate_counters[key] += 1


class PlaceReportRequest(BaseModel):
    business_hours_text: str | None = None
    price_range: str | None = None
    rating: float | None = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: float | None) -> float | None:
        if v is None:
            return v
        if not (1.0 <= v <= 5.0):
            raise ValueError("rating must be between 1.0 and 5.0")
        if round(v * 2) != v * 2:
            raise ValueError("rating must be in 0.5 steps")
        return v


class PlaceReportResponse(BaseModel):
    success: bool
    data: dict[str, Any]
    error: str | None = None


@router.post("/{place_id}/report", response_model=PlaceReportResponse)
async def report_place(
    place_id: int,
    body: PlaceReportRequest,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlaceReportResponse:
    ip_hash = _ip_hash(request)
    _check_rate_limit(ip_hash)

    place = await db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="PLACE_NOT_FOUND")

    avg_rating: float | None = None
    rating_count: int = place.user_rating_count

    if body.rating is not None:
        rating_x2 = round(body.rating * 2)

        existing = await db.get(PlaceRatingReport, (ip_hash, place_id))
        if existing is not None:
            # 이전 rating 차감 후 새 값 반영 (이중 반영 방지)
            place.user_rating_sum = place.user_rating_sum - existing.rating_x2 + rating_x2
            existing.rating_x2 = rating_x2
        else:
            place.user_rating_sum += rating_x2
            place.user_rating_count += 1
            db.add(PlaceRatingReport(
                ip_hash=ip_hash,
                place_id=place_id,
                rating_x2=rating_x2,
            ))

        rating_count = place.user_rating_count
        if rating_count > 0:
            avg_rating = round(place.user_rating_sum / 2.0 / rating_count, 1)

    if body.business_hours_text is not None:
        place.business_hours = body.business_hours_text

    if body.price_range is not None:
        place.price_range = body.price_range

    await db.commit()

    return PlaceReportResponse(
        success=True,
        data={
            "recorded": True,
            "avg_rating": avg_rating,
            "rating_count": rating_count,
        },
    )
