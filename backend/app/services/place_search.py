import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.kakao_places import search_kakao_keyword_live, upsert_kakao_docs

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
    menu_keyword: str | None = None,
) -> list[dict]:
    """Return candidate places near a station via PostGIS ST_DWithin.

    Expands radius from radius_km → _RADIUS_EXPANSION_KM if fewer than
    _MIN_CANDIDATES results are found on the first pass.

    When menu_keyword is given (e.g. "치킨" from a "치맥" request), candidates
    whose name contains it are sorted first — boosted, not filtered, so the
    pool still fills out with theme/distance matches when few or no names match.
    """
    results = await _query(
        session, station_id, radius_km, theme_tags, exclude_place_ids, limit, menu_keyword
    )

    if len(results) < _MIN_CANDIDATES:
        logger.info(
            "station=%s: only %d candidates at %.1fkm, expanding to %.1fkm",
            station_id, len(results), radius_km, _RADIUS_EXPANSION_KM,
        )
        results = await _query(
            session, station_id, _RADIUS_EXPANSION_KM, theme_tags, exclude_place_ids, limit,
            menu_keyword,
        )

    # If theme filter yields too few results, fall back to no theme filter
    if len(results) < _MIN_CANDIDATES and theme_tags:
        logger.info(
            "station=%s: theme filter yielded only %d candidates, retrying without theme filter",
            station_id, len(results),
        )
        results = await _query(
            session, station_id, _RADIUS_EXPANSION_KM, None, exclude_place_ids, limit, menu_keyword
        )

    # No local place name actually matches the user's menu keyword (e.g. "치킨") —
    # our offline coverage is a fixed-size sample per station, not exhaustive.
    # Search Kakao live, persist any real matches, and use them for this request too.
    if menu_keyword and not any(menu_keyword in (r.get("name") or "") for r in results):
        live_results = await _live_keyword_fallback(session, station_id, menu_keyword, theme_tags)
        if live_results:
            existing_ids = {r["place_id"] for r in results}
            fresh = [r for r in live_results if r["place_id"] not in existing_ids]
            results = (fresh + results)[:limit]

    return results


async def _live_keyword_fallback(
    session: AsyncSession, station_id: int, menu_keyword: str, theme_tags: list[str] | None,
) -> list[dict]:
    station_row = (
        await session.execute(
            text("SELECT lat, lng FROM stations WHERE station_id = :sid"),
            {"sid": station_id},
        )
    ).mappings().first()
    if not station_row:
        return []

    docs = await search_kakao_keyword_live(menu_keyword, station_row["lat"], station_row["lng"])
    if not docs:
        return []

    logger.info(
        "station=%s: live Kakao search for '%s' found %d results, upserting",
        station_id, menu_keyword, len(docs),
    )
    return await upsert_kakao_docs(session, docs, theme_tags or ["FOOD"])


async def _query(
    session: AsyncSession,
    station_id: int,
    radius_km: float,
    theme_tags: list[str] | None,
    exclude_place_ids: list[int] | None,
    limit: int,
    menu_keyword: str | None = None,
) -> list[dict]:
    # Build filters inline to avoid asyncpg custom-type array binding issues
    theme_clause = ""
    if theme_tags:
        tag_literals = ", ".join(f"'{t}'::theme_tag" for t in theme_tags)
        theme_clause = f"AND p.theme_tags && ARRAY[{tag_literals}]"

    exclude_clause = ""
    if exclude_place_ids:
        id_literals = ", ".join(str(i) for i in exclude_place_ids)
        exclude_clause = f"AND p.place_id NOT IN ({id_literals})"

    order_clause = "distance_m"
    params: dict = {
        "station_id": station_id,
        "radius_m": radius_km * 1000,
        "limit": limit,
    }
    if menu_keyword:
        order_clause = "(p.name ILIKE :menu_kw) DESC, distance_m"
        params["menu_kw"] = f"%{menu_keyword}%"

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
          {theme_clause}
          {exclude_clause}
        ORDER BY {order_clause}
        LIMIT :limit
    """)

    result = await session.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]
