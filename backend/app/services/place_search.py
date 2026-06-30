import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MIN_CANDIDATES = 5
_RADIUS_EXPANSION_KM = 7.0


async def search_candidate_places(
    session: AsyncSession,
    station_id: int,
    radius_km: float = 5.0,
    theme_tags: list[str] | None = None,
    exclude_place_ids: list[int] | None = None,
    limit: int = 30,
) -> list[dict]:
    """Return candidate places near a station via PostGIS ST_DWithin.

    Expands radius from radius_km → _RADIUS_EXPANSION_KM if fewer than
    _MIN_CANDIDATES results are found on the first pass.
    """
    results = await _query(session, station_id, radius_km, theme_tags, exclude_place_ids, limit)

    if len(results) < _MIN_CANDIDATES:
        logger.info(
            "station=%s: only %d candidates at %.1fkm, expanding to %.1fkm",
            station_id, len(results), radius_km, _RADIUS_EXPANSION_KM,
        )
        results = await _query(
            session, station_id, _RADIUS_EXPANSION_KM, theme_tags, exclude_place_ids, limit
        )

    return results


async def _query(
    session: AsyncSession,
    station_id: int,
    radius_km: float,
    theme_tags: list[str] | None,
    exclude_place_ids: list[int] | None,
    limit: int,
) -> list[dict]:
    theme_filter = "AND p.theme_tags && CAST(:theme_tags AS theme_tag[])" if theme_tags else ""
    exclude_filter = "AND p.place_id != ALL(:exclude_ids)" if exclude_place_ids else ""

    sql = text(f"""
        SELECT
            p.place_id, p.name, p.category, p.address,
            p.lat, p.lng, p.price_range, p.business_hours,
            p.map_url, p.phone, p.thumbnail_url, p.theme_tags,
            p.user_rating_sum, p.user_rating_count,
            ST_Distance(p.geom::geography, s.geom::geography) AS distance_m
        FROM places p
        JOIN stations s ON s.station_id = :station_id
        WHERE p.status = 'OPEN'
          AND ST_DWithin(p.geom::geography, s.geom::geography, :radius_m)
          {theme_filter}
          {exclude_filter}
        ORDER BY distance_m
        LIMIT :limit
    """)

    params: dict = {
        "station_id": station_id,
        "radius_m": radius_km * 1000,
        "limit": limit,
    }
    if theme_tags:
        params["theme_tags"] = "{" + ",".join(theme_tags) + "}"
    if exclude_place_ids:
        params["exclude_ids"] = exclude_place_ids

    result = await session.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]
