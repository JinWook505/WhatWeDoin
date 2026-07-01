"""FastAPI dependencies for auth."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.services.auth import verify_access_token


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict | None:
    """Returns current user dict or None (non-blocking)."""
    token = _bearer_token(request)
    if not token:
        return None
    user_id = verify_access_token(token)
    if not user_id:
        return None
    row = (
        await db.execute(
            text(
                "SELECT id, nickname, status, preferred_theme_tags, "
                "preferred_budget, preferred_companion_type, home_station_id "
                "FROM users WHERE id=:uid"
            ),
            {"uid": user_id},
        )
    ).mappings().first()
    if not row or row["status"] != "ACTIVE":
        return None
    return dict(row)


async def require_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns current user dict or raises 401."""
    user = await get_current_user_optional(request, db)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "로그인이 필요해요."},
        )
    return user
