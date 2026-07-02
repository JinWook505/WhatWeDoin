"""Cache, idempotency, and daily rate-limit helpers (PostgreSQL-only, no Redis).

Tables used:
  recommendation_requests — idempotency + daily quota counting
  course_cache            — LLM result cache keyed by content hash
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_DAILY_LIMIT = 3
_CACHE_TTL_DAYS = 14


# ---------------------------------------------------------------------------
# Cache key
# ---------------------------------------------------------------------------

def make_cache_key(station_id: int, query_text: str) -> str:
    normalized = re.sub(r"\s+", " ", query_text.strip().lower())
    payload = f"{station_id}:{normalized}"
    return hashlib.sha256(payload.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Course cache
# ---------------------------------------------------------------------------

async def get_course_cache(db: AsyncSession, cache_key: str) -> dict | None:
    row = (
        await db.execute(
            text("""
                SELECT result FROM course_cache
                WHERE cache_key = :key AND expires_at > now()
            """),
            {"key": cache_key},
        )
    ).mappings().first()
    if not row:
        return None
    result = row["result"]
    return result if isinstance(result, dict) else json.loads(result)


async def set_course_cache(db: AsyncSession, cache_key: str, result: dict) -> None:
    await db.execute(
        text("""
            INSERT INTO course_cache (cache_key, result, expires_at)
            VALUES (:key, CAST(:result AS jsonb), now() + (:days * interval '1 day'))
            ON CONFLICT (cache_key) DO UPDATE
                SET result = EXCLUDED.result, expires_at = EXCLUDED.expires_at
        """),
        {"key": cache_key, "result": json.dumps(result), "days": _CACHE_TTL_DAYS},
    )


# ---------------------------------------------------------------------------
# Daily quota  (count served_from='LLM' requests today KST per user)
# ---------------------------------------------------------------------------

async def check_daily_quota(db: AsyncSession, user_id: int) -> bool:
    """Return True if user is within daily limit, False if exceeded."""
    row = (
        await db.execute(
            text("""
                SELECT COUNT(*) AS cnt
                FROM recommendation_requests
                WHERE user_id = :uid
                  AND served_from = 'LLM'
                  AND created_at >= date_trunc('day', now() AT TIME ZONE 'Asia/Seoul')
                                    AT TIME ZONE 'Asia/Seoul'
            """),
            {"uid": user_id},
        )
    ).mappings().first()
    count = int(row["cnt"]) if row else 0
    return count < _DAILY_LIMIT


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

async def acquire_idempotency_lock(db: AsyncSession, user_id: int, idempotency_key: str) -> None:
    """Serialize concurrent requests sharing the same (user_id, idempotency_key).

    pg_advisory_xact_lock is held until the current transaction commits or
    rolls back, so a second request with the same key blocks here until the
    first request's course row is committed, then re-checks idempotency and
    replays the cached result instead of generating a duplicate course.
    """
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"{user_id}:{idempotency_key}"},
    )


async def get_idempotency_result(
    db: AsyncSession,
    user_id: int,
    idempotency_key: str,
) -> int | None:
    """Return course_id of a previous identical request, or None."""
    row = (
        await db.execute(
            text("""
                SELECT course_id FROM recommendation_requests
                WHERE user_id = :uid AND idempotency_key = :key
                LIMIT 1
            """),
            {"uid": user_id, "key": idempotency_key},
        )
    ).mappings().first()
    return row["course_id"] if row else None


# ---------------------------------------------------------------------------
# Record request
# ---------------------------------------------------------------------------

async def record_request(
    db: AsyncSession,
    *,
    user_id: int,
    station_id: int,
    query_text: str,
    served_from: str,  # 'LLM' or 'CACHE'
    course_id: int | None,
    idempotency_key: str | None = None,
) -> None:
    await db.execute(
        text("""
            INSERT INTO recommendation_requests
                (user_id, station_id, query_text, served_from, course_id, idempotency_key)
            VALUES (:uid, :sid, :query, CAST(:served AS served_from), :cid, :ikey)
            ON CONFLICT (user_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL
            DO NOTHING
        """),
        {
            "uid": user_id,
            "sid": station_id,
            "query": query_text,
            "served": served_from,
            "cid": course_id,
            "ikey": idempotency_key,
        },
    )
