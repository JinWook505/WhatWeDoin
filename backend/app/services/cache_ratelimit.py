"""Cache, idempotency, and rate-limit helpers for the recommend endpoint.

All storage uses PostgreSQL — no Redis dependency.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


# ── helpers ──────────────────────────────────────────────────────────────────

def build_cache_key(
    station_id: int,
    theme_tags: list[str],
    budget_tier: str,
    companion_type: str,
) -> str:
    """Deterministic 64-char SHA-256 hex key from recommendation parameters."""
    normalized = json.dumps(
        {
            "station_id": station_id,
            "theme_tags": sorted(theme_tags),
            "budget_tier": budget_tier,
            "companion_type": companion_type,
        },
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:64]


async def _get_config(session: AsyncSession, key: str, default: Any = None) -> Any:
    row = (
        await session.execute(
            text("SELECT value FROM app_config WHERE key = :key"),
            {"key": key},
        )
    ).scalar()
    return row if row is not None else default


# ── cache ─────────────────────────────────────────────────────────────────────

async def get_cached_course(
    session: AsyncSession,
    cache_key: str,
) -> dict | None:
    """Return cached course dict if a valid (non-expired) entry exists."""
    row = (
        await session.execute(
            text("""
                SELECT result FROM course_cache
                WHERE cache_key = :key AND expires_at > now() AT TIME ZONE 'UTC'
            """),
            {"key": cache_key},
        )
    ).scalar()
    if row is None:
        return None
    return row if isinstance(row, dict) else json.loads(row)


async def set_cached_course(
    session: AsyncSession,
    cache_key: str,
    result: dict,
    ttl_days: int = 14,
) -> None:
    """Upsert course result into course_cache."""
    await session.execute(
        text("""
            INSERT INTO course_cache (cache_key, result, expires_at)
            VALUES (:key, CAST(:result AS jsonb), now() + :ttl * INTERVAL '1 day')
            ON CONFLICT (cache_key) DO UPDATE
                SET result = EXCLUDED.result,
                    expires_at = EXCLUDED.expires_at
        """),
        {"key": cache_key, "result": json.dumps(result), "ttl": ttl_days},
    )


# ── idempotency ───────────────────────────────────────────────────────────────

async def get_idempotent_course_id(
    session: AsyncSession,
    user_id: int,
    idempotency_key: str,
) -> int | None:
    """Return the course_id for a previously processed (user_id, idempotency_key) pair."""
    row = (
        await session.execute(
            text("""
                SELECT course_id FROM recommendation_requests
                WHERE user_id = :uid AND idempotency_key = :ikey
                LIMIT 1
            """),
            {"uid": user_id, "ikey": idempotency_key},
        )
    ).scalar()
    return row


# ── rate limit ────────────────────────────────────────────────────────────────

async def check_user_daily_ratelimit(
    session: AsyncSession,
    user_id: int,
) -> bool:
    """Return True if user is within the daily LLM recommendation limit."""
    limit_raw = await _get_config(session, "ratelimit.user_daily", "3")
    tz_raw = await _get_config(session, "ratelimit.timezone", "Asia/Seoul")

    # Strip surrounding quotes that Postgres JSONB stores for string values
    daily_limit = int(str(limit_raw).strip('"'))
    tz = str(tz_raw).strip('"')

    count = (
        await session.execute(
            text("""
                SELECT COUNT(*) FROM recommendation_requests
                WHERE user_id = :uid
                  AND served_from = 'LLM'
                  AND created_at AT TIME ZONE :tz >= date_trunc('day', now() AT TIME ZONE :tz)
            """),
            {"uid": user_id, "tz": tz},
        )
    ).scalar() or 0

    return int(count) < daily_limit


async def check_review_ip_ratelimit(
    session: AsyncSession,
    ip_hash: str,
) -> bool:
    """Return True if an anonymous IP is within the daily review limit."""
    limit_raw = await _get_config(session, "ratelimit.review_ip_daily", "20")
    tz_raw = await _get_config(session, "ratelimit.timezone", "Asia/Seoul")

    daily_limit = int(str(limit_raw).strip('"'))
    tz = str(tz_raw).strip('"')

    count = (
        await session.execute(
            text("""
                SELECT COUNT(*) FROM course_reviews
                WHERE ip_hash = :ip
                  AND user_id IS NULL
                  AND created_at AT TIME ZONE :tz >= date_trunc('day', now() AT TIME ZONE :tz)
            """),
            {"ip": ip_hash, "tz": tz},
        )
    ).scalar() or 0

    return int(count) < daily_limit


# ── request recording ─────────────────────────────────────────────────────────

async def record_recommendation_request(
    session: AsyncSession,
    *,
    user_id: int,
    station_id: int,
    query_text: str,
    parsed_input: dict | None,
    exclude_place_ids: list[int],
    served_from: str,
    idempotency_key: str | None,
    course_id: int | None,
) -> None:
    """Insert a row into recommendation_requests."""
    await session.execute(
        text("""
            INSERT INTO recommendation_requests
                (user_id, station_id, query_text, parsed_input,
                 exclude_place_ids, served_from, idempotency_key, course_id)
            VALUES
                (:uid, :sid, :qtxt, CAST(:parsed AS jsonb),
                 :excl, CAST(:sf AS served_from), :ikey, :cid)
            ON CONFLICT (user_id, idempotency_key)
            WHERE idempotency_key IS NOT NULL
            DO NOTHING
        """),
        {
            "uid": user_id,
            "sid": station_id,
            "qtxt": query_text,
            "parsed": json.dumps(parsed_input) if parsed_input else None,
            "excl": exclude_place_ids,
            "sf": served_from,
            "ikey": idempotency_key,
            "cid": course_id,
        },
    )
