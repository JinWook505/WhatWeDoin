"""Live Kakao keyword search fallback for candidate place search.

When a user names a specific menu/dish (e.g. "치맥" → menu_keyword "치킨") and no
place in our DB matches it by name near the station, offline coverage gaps
(places.py only seeds ~45 places per broad category per station) mean the LLM
has nothing real to recommend. Rather than only pre-seeding known keywords via
scripts/etl_menu_keywords.py, this module searches Kakao's keyword API live,
persists any real matches into `places` so future requests benefit too, and
returns them immediately so the current request can use them.

Best-effort: any failure (network, API error, bad response) is swallowed and
logged — this must never break the recommend endpoint.
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

_KAKAO_KEYWORD_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
_LIVE_RADIUS_M = 5000
_LIVE_PAGE_SIZE = 15
_LIVE_TIMEOUT_SEC = 3.0


async def search_kakao_keyword_live(keyword: str, lat: float, lng: float) -> list[dict]:
    """Single-page live Kakao keyword search near (lat, lng). Returns [] on any failure."""
    api_key = settings.KAKAO_REST_API_KEY
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=_LIVE_TIMEOUT_SEC) as client:
            resp = await client.get(
                _KAKAO_KEYWORD_API_URL,
                headers={"Authorization": f"KakaoAK {api_key}"},
                params={
                    "query": keyword,
                    "x": str(lng),
                    "y": str(lat),
                    "radius": _LIVE_RADIUS_M,
                    "size": _LIVE_PAGE_SIZE,
                    "page": 1,
                },
            )
            resp.raise_for_status()
            return resp.json().get("documents", [])
    except Exception as exc:
        logger.warning("Kakao live keyword search failed for %r: %s", keyword, exc)
        return []


async def upsert_kakao_docs(
    session: AsyncSession, docs: list[dict], theme_tags: list[str]
) -> list[dict]:
    """Upsert Kakao keyword-search documents into `places`, returning candidate-shaped
    dicts (same shape as place_search._query rows) for immediate use in this request.
    """
    if not docs:
        return []

    tag_literals = ", ".join(f"'{t}'::theme_tag" for t in theme_tags) or None
    theme_tags_sql = f"ARRAY[{tag_literals}]" if tag_literals else "ARRAY[]::theme_tag[]"

    sql = text(f"""
        INSERT INTO places (
            external_source, external_id, name, category, address,
            lat, lng, geom, phone, map_url, business_hours,
            theme_tags, status, last_synced_at
        ) VALUES (
            'KAKAO'::oauth_provider, :external_id, :name, :category, :address,
            :lat, :lng, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :phone, :map_url, NULL,
            {theme_tags_sql}, 'OPEN', now()
        )
        ON CONFLICT (external_source, external_id) DO UPDATE SET
            name = EXCLUDED.name,
            theme_tags = EXCLUDED.theme_tags,
            status = 'OPEN',
            last_synced_at = now()
        RETURNING place_id, name, category, address, lat, lng,
                  price_range, business_hours, map_url, phone, thumbnail_url,
                  theme_tags, user_rating_sum, user_rating_count
    """)

    results: list[dict] = []
    for doc in docs:
        try:
            row = (
                await session.execute(sql, {
                    "external_id": doc["id"],
                    "name": doc["place_name"],
                    "category": doc.get("category_group_code", ""),
                    "address": doc.get("road_address_name") or doc.get("address_name", ""),
                    "lat": float(doc["y"]),
                    "lng": float(doc["x"]),
                    "phone": doc.get("phone") or "",
                    "map_url": doc.get("place_url") or "",
                })
            ).mappings().first()
            if row:
                results.append(dict(row))
        except Exception as exc:
            logger.warning("Failed to upsert live Kakao place %r: %s", doc.get("place_name"), exc)
    return results
