"""Kakao OAuth + JWT auth service."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

_KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_KAKAO_PROFILE_URL = "https://kapi.kakao.com/v2/user/me"


# ---------------------------------------------------------------------------
# Kakao OAuth helpers
# ---------------------------------------------------------------------------

async def exchange_kakao_code(code: str, redirect_uri: str) -> dict:
    """Exchange Kakao authorization code for tokens."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _KAKAO_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.KAKAO_REST_API_KEY,
                "client_secret": settings.KAKAO_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
    resp.raise_for_status()
    return resp.json()


async def get_kakao_profile(kakao_access_token: str) -> dict:
    """Fetch Kakao user profile."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            _KAKAO_PROFILE_URL,
            headers={"Authorization": f"Bearer {kakao_access_token}"},
            timeout=10,
        )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# User upsert
# ---------------------------------------------------------------------------

async def upsert_user(
    db: AsyncSession,
    oauth_id: str,
    nickname: str,
    email: str | None,
    profile_image_url: str | None,
) -> tuple[dict, bool]:
    """Insert or update user, return (user_row, is_new)."""
    now = datetime.now(timezone.utc)
    row = (
        await db.execute(
            text("SELECT id, status FROM users WHERE oauth_provider='KAKAO' AND oauth_id=:oid"),
            {"oid": oauth_id},
        )
    ).mappings().first()

    if row:
        await db.execute(
            text("""
                UPDATE users
                SET nickname=:nick, email=:email, profile_image_url=:pic,
                    last_login_at=:now, updated_at=:now
                WHERE id=:uid
            """),
            {"nick": nickname, "email": email, "pic": profile_image_url,
             "now": now, "uid": row["id"]},
        )
        await db.commit()
        user = (
            await db.execute(text("SELECT * FROM users WHERE id=:uid"), {"uid": row["id"]})
        ).mappings().first()
        return dict(user), False

    result = await db.execute(
        text("""
            INSERT INTO users
                (oauth_provider, oauth_id, email, nickname, profile_image_url,
                 terms_agreed_at, privacy_agreed_at, last_login_at, created_at, updated_at)
            VALUES ('KAKAO', :oid, :email, :nick, :pic, :now, :now, :now, :now, :now)
            RETURNING *
        """),
        {"oid": oauth_id, "email": email, "nick": nickname,
         "pic": profile_image_url, "now": now},
    )
    await db.commit()
    user = result.mappings().first()
    return dict(user), True


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": _now_utc() + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES),
        "iat": _now_utc(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_access_token(token: str) -> int | None:
    """Return user_id from a valid access token, or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Refresh token DB helpers
# ---------------------------------------------------------------------------

async def create_refresh_token(
    db: AsyncSession, user_id: int, user_agent: str | None
) -> tuple[str, str]:
    """Persist a new refresh token. Returns (jti, signed_jwt)."""
    jti = str(uuid.uuid4())
    expires_at = _now_utc() + timedelta(days=settings.JWT_REFRESH_TTL_DAYS)

    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "exp": expires_at,
        "iat": _now_utc(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    await db.execute(
        text("""
            INSERT INTO refresh_tokens (jti, user_id, user_agent, expires_at)
            VALUES (:jti, :uid, :ua, :exp)
        """),
        {"jti": jti, "uid": user_id, "ua": user_agent, "exp": expires_at},
    )
    await db.commit()
    return jti, token


async def rotate_refresh_token(
    db: AsyncSession, old_token: str, user_agent: str | None
) -> tuple[str, str] | None:
    """
    Rotate refresh token.
    - If jti already revoked → revoke all user tokens (reuse attack) and return None.
    - If jti valid → revoke it and issue new pair.
    Returns (new_access_token, new_refresh_token) or None on reuse attack.
    """
    try:
        payload = jwt.decode(old_token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None

    if payload.get("type") != "refresh":
        return None

    jti = payload.get("jti")
    user_id = int(payload["sub"])

    row = (
        await db.execute(
            text("SELECT jti, revoked_at FROM refresh_tokens WHERE jti=:jti"),
            {"jti": jti},
        )
    ).mappings().first()

    if not row:
        return None

    if row["revoked_at"] is not None:
        # Reuse detected — revoke every token for this user
        await db.execute(
            text("UPDATE refresh_tokens SET revoked_at=now() WHERE user_id=:uid AND revoked_at IS NULL"),
            {"uid": user_id},
        )
        await db.commit()
        return None

    # Normal rotation
    await db.execute(
        text("UPDATE refresh_tokens SET revoked_at=now() WHERE jti=:jti"),
        {"jti": jti},
    )
    access = create_access_token(user_id)
    _, refresh = await create_refresh_token(db, user_id, user_agent)
    return access, refresh


async def revoke_all_tokens(db: AsyncSession, user_id: int) -> None:
    """Revoke all active refresh tokens for user (logout)."""
    await db.execute(
        text("UPDATE refresh_tokens SET revoked_at=now() WHERE user_id=:uid AND revoked_at IS NULL"),
        {"uid": user_id},
    )
    await db.commit()
