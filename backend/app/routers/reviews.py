"""Course review endpoints: POST/GET/DELETE + report."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user_optional

router = APIRouter(prefix="/v1/courses/{course_id}/reviews", tags=["reviews"])

# Bayesian prior constants (PRD D-18)
_PRIOR_MEAN = 50
_PRIOR_COUNT = 5


def _ip_hash(request: Request) -> str:
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "0.0.0.0")
    ip = ip.split(",")[0].strip()
    return hashlib.sha256(ip.encode()).hexdigest()[:64]


def _recalc_bayesian(rating_sum: int, rating_count: int) -> float:
    """bayesian = (C·m + Σscore) / (C + n)"""
    return (_PRIOR_COUNT * _PRIOR_MEAN + rating_sum) / (_PRIOR_COUNT + rating_count)


async def _update_course_rating(
    db: AsyncSession,
    course_id: int,
    old_score: int | None,
    new_score: int | None,
) -> tuple[float, int]:
    """
    Adjust rating_sum and rating_count atomically, recalculate bayesian_score.
    old_score=None means insert, new_score=None means delete.
    Returns (new_bayesian_score, new_rating_count).
    """
    if old_score is None and new_score is not None:
        # Insert
        delta_sum, delta_count = new_score, 1
    elif old_score is not None and new_score is not None:
        # Update
        delta_sum, delta_count = new_score - old_score, 0
    elif old_score is not None and new_score is None:
        # Delete
        delta_sum, delta_count = -old_score, -1
    else:
        return 0.0, 0

    row = (
        await db.execute(
            text("""
                UPDATE courses
                SET rating_sum   = rating_sum   + :ds,
                    rating_count = rating_count + :dc,
                    updated_at   = now()
                WHERE course_id = :cid
                RETURNING rating_sum, rating_count
            """),
            {"ds": delta_sum, "dc": delta_count, "cid": course_id},
        )
    ).mappings().first()

    if not row:
        return 0.0, 0

    new_sum = row["rating_sum"]
    new_count = row["rating_count"]
    new_bayesian = _recalc_bayesian(new_sum, new_count)

    await db.execute(
        text("UPDATE courses SET bayesian_score = :bs WHERE course_id = :cid"),
        {"bs": round(new_bayesian, 2), "cid": course_id},
    )
    return new_bayesian, new_count


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    score: int
    comment: str | None = None
    links: list[str] = []

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if not (0 <= v <= 100) or v % 5 != 0:
            raise ValueError("score는 0~100 사이 5단위여야 해요.")
        return v


class ReportRequest(BaseModel):
    reason: str
    comment: str | None = None


# ---------------------------------------------------------------------------
# POST /v1/courses/{course_id}/reviews  (upsert)
# ---------------------------------------------------------------------------

@router.post("")
async def upsert_review(
    course_id: int,
    body: ReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    # Verify course exists
    exists = (
        await db.execute(
            text("SELECT 1 FROM courses WHERE course_id = :cid"),
            {"cid": course_id},
        )
    ).scalar()
    if not exists:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "코스를 찾을 수 없어요."},
        )

    user_id = current_user["id"] if current_user else None
    ip = _ip_hash(request) if not user_id else None

    links_json = json.dumps(body.links)

    if user_id:
        existing = (
            await db.execute(
                text("SELECT id, score FROM course_reviews WHERE course_id=:cid AND user_id=:uid"),
                {"cid": course_id, "uid": user_id},
            )
        ).mappings().first()
    else:
        existing = (
            await db.execute(
                text("SELECT id, score FROM course_reviews WHERE course_id=:cid AND ip_hash=:ip AND user_id IS NULL"),
                {"cid": course_id, "ip": ip},
            )
        ).mappings().first()

    old_score = existing["score"] if existing else None

    if existing:
        # Update
        await db.execute(
            text("""
                UPDATE course_reviews
                SET score=:score, comment=:comment, links=CAST(:links AS jsonb), updated_at=now()
                WHERE id=:rid
            """),
            {"score": body.score, "comment": body.comment, "links": links_json, "rid": existing["id"]},
        )
        review_id = existing["id"]
    else:
        # Insert
        result = await db.execute(
            text("""
                INSERT INTO course_reviews (course_id, user_id, ip_hash, score, comment, links)
                VALUES (:cid, :uid, :ip, :score, :comment, CAST(:links AS jsonb))
                RETURNING id
            """),
            {"cid": course_id, "uid": user_id, "ip": ip,
             "score": body.score, "comment": body.comment, "links": links_json},
        )
        review_id = result.scalar()

    new_bayesian, new_count = await _update_course_rating(db, course_id, old_score, body.score)
    await db.commit()

    return {
        "success": True,
        "data": {
            "recorded": True,
            "review_id": review_id,
            "course_bayesian_score": round(new_bayesian, 2),
            "rating_count": new_count,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# GET /v1/courses/{course_id}/reviews
# ---------------------------------------------------------------------------

@router.get("")
async def list_reviews(
    course_id: int,
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    user_id = current_user["id"] if current_user else None
    ip = _ip_hash(request)

    # Summary
    summary_row = (
        await db.execute(
            text("SELECT bayesian_score, rating_count, rating_sum FROM courses WHERE course_id=:cid"),
            {"cid": course_id},
        )
    ).mappings().first()
    if not summary_row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "코스를 찾을 수 없어요."})

    n = summary_row["rating_count"] or 0
    s = summary_row["rating_sum"] or 0

    # Cursor pagination by review id DESC
    cursor_cond = "AND r.id < :cursor_id" if cursor else ""
    params: dict[str, Any] = {"cid": course_id, "limit": limit + 1}
    if cursor:
        try:
            params["cursor_id"] = int(cursor)
        except ValueError:
            raise HTTPException(status_code=400, detail={"code": "INVALID_CURSOR", "message": "잘못된 커서입니다."})

    rows = (
        await db.execute(
            text(f"""
                SELECT r.id, r.score, r.comment, r.links, r.created_at,
                       r.user_id, r.ip_hash
                FROM course_reviews r
                WHERE r.course_id = :cid {cursor_cond}
                ORDER BY r.id DESC
                LIMIT :limit
            """),
            params,
        )
    ).mappings().all()

    has_next = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = str(items[-1]["id"]) if has_next else None

    reviews_out = []
    for r in items:
        links = r["links"]
        if isinstance(links, str):
            try:
                links = json.loads(links)
            except Exception:
                links = []

        is_mine = (user_id is not None and r["user_id"] == user_id) or (
            not user_id and r["ip_hash"] == ip and r["user_id"] is None
        )
        reviews_out.append({
            "review_id": r["id"],
            "score": r["score"],
            "comment": r["comment"],
            "links": links or [],
            "is_mine": is_mine,
            "created_at": str(r["created_at"]) if r["created_at"] else None,
        })

    return {
        "success": True,
        "data": {
            "summary": {
                "bayesian_score": round(float(summary_row["bayesian_score"] or 0), 2),
                "avg_score": round(s / n, 1) if n > 0 else None,
                "rating_count": n,
            },
            "reviews": reviews_out,
            "next_cursor": next_cursor,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# DELETE /v1/courses/{course_id}/reviews/me
# ---------------------------------------------------------------------------

@router.delete("/me")
async def delete_my_review(
    course_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    user_id = current_user["id"] if current_user else None
    ip = _ip_hash(request) if not user_id else None

    if user_id:
        existing = (
            await db.execute(
                text("SELECT id, score FROM course_reviews WHERE course_id=:cid AND user_id=:uid"),
                {"cid": course_id, "uid": user_id},
            )
        ).mappings().first()
    else:
        existing = (
            await db.execute(
                text("SELECT id, score FROM course_reviews WHERE course_id=:cid AND ip_hash=:ip AND user_id IS NULL"),
                {"cid": course_id, "ip": ip},
            )
        ).mappings().first()

    if not existing:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "삭제할 리뷰가 없어요."},
        )

    await db.execute(
        text("DELETE FROM course_reviews WHERE id=:rid"),
        {"rid": existing["id"]},
    )
    await _update_course_rating(db, course_id, existing["score"], None)
    await db.commit()

    return {"success": True, "data": {"deleted": True}, "error": None}


# ---------------------------------------------------------------------------
# POST /v1/courses/{course_id}/reviews/{review_id}/report
# ---------------------------------------------------------------------------

report_router = APIRouter(prefix="/v1/courses/{course_id}/reviews/{review_id}/report", tags=["reviews"])


@report_router.post("")
async def report_review(
    course_id: int,
    review_id: int,
    body: ReportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_optional),
):
    user_id = current_user["id"] if current_user else None
    ip = _ip_hash(request) if not user_id else None

    # Verify review belongs to course
    exists = (
        await db.execute(
            text("SELECT 1 FROM course_reviews WHERE id=:rid AND course_id=:cid"),
            {"rid": review_id, "cid": course_id},
        )
    ).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "리뷰를 찾을 수 없어요."})

    await db.execute(
        text("""
            INSERT INTO course_review_reports (review_id, user_id, ip_hash, reason, comment)
            VALUES (:rid, :uid, :ip, CAST(:reason AS report_reason), :comment)
            ON CONFLICT DO NOTHING
        """),
        {"rid": review_id, "uid": user_id, "ip": ip,
         "reason": body.reason, "comment": body.comment},
    )
    await db.commit()

    return {"success": True, "data": {"recorded": True}, "error": None}
