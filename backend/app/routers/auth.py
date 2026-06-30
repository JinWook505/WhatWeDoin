"""Auth endpoints: Kakao OAuth, JWT refresh, logout."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_current_user
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    exchange_kakao_code,
    get_kakao_profile,
    revoke_all_tokens,
    rotate_refresh_token,
    upsert_user,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


class KakaoLoginRequest(BaseModel):
    authorization_code: str
    redirect_uri: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# POST /v1/auth/kakao
# ---------------------------------------------------------------------------

@router.post("/kakao")
async def kakao_login(
    body: KakaoLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        kakao_tokens = await exchange_kakao_code(body.authorization_code, body.redirect_uri)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "KAKAO_AUTH_FAILED", "message": f"카카오 인증에 실패했어요. ({e.response.status_code})"},
        )

    try:
        profile = await get_kakao_profile(kakao_tokens["access_token"])
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=400,
            detail={"code": "KAKAO_PROFILE_FAILED", "message": "카카오 프로필 조회에 실패했어요."},
        )

    oauth_id = str(profile["id"])
    kakao_account = profile.get("kakao_account", {})
    properties = profile.get("properties", {})

    nickname = (
        properties.get("nickname")
        or kakao_account.get("profile", {}).get("nickname")
        or "사용자"
    )
    email = kakao_account.get("email")
    profile_image = (
        properties.get("profile_image")
        or kakao_account.get("profile", {}).get("profile_image_url")
    )

    user, is_new = await upsert_user(db, oauth_id, nickname, email, profile_image)

    user_agent = request.headers.get("User-Agent")
    access_token = create_access_token(user["id"])
    _, refresh_token = await create_refresh_token(db, user["id"], user_agent)

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "is_new_user": is_new,
            "user": {
                "id": user["id"],
                "nickname": user["nickname"],
                "profile_image_url": user.get("profile_image_url"),
                "preferred_companion_type": user.get("preferred_companion_type"),
            },
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/refresh
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_agent = request.headers.get("User-Agent")
    result = await rotate_refresh_token(db, body.refresh_token, user_agent)

    if result is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": "유효하지 않은 토큰이에요. 다시 로그인해주세요."},
        )

    access_token, new_refresh_token = result
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# POST /v1/auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout")
async def logout(
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_all_tokens(db, current_user["id"])
    return {"success": True, "data": {"logged_out": True}, "error": None}
