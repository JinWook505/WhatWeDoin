"""User profile endpoints: GET/PATCH /v1/users/me, DELETE /v1/users/me."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_current_user
from app.models.enums import BudgetTier, CompanionType, DatingStage, GenderType, ThemeTag

router = APIRouter(prefix="/v1/users", tags=["users"])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    preferred_companion_type: str | None = None
    preferred_theme_tags: list[str] | None = None   # None = 건드리지 않음, [] = 초기화
    preferred_budget: str | None = None
    gender: str | None = None
    birth_year: int | None = None
    dating_stage: str | None = None
    home_station_id: int | None = None
    terms_agreed_at: datetime | None = None
    privacy_agreed_at: datetime | None = None
    marketing_agreed: bool | None = None

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str | None) -> str | None:
        if v is not None and not (2 <= len(v.strip()) <= 20):
            raise ValueError("닉네임은 2~20자여야 해요.")
        return v.strip() if v else v

    @field_validator("preferred_theme_tags")
    @classmethod
    def validate_themes(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) > 5:
            raise ValueError("테마는 최대 5개까지 선택할 수 있어요.")
        for tag in v:
            if tag not in ThemeTag._value2member_map_:
                raise ValueError(f"'{tag}'는 유효한 테마가 아니에요.")
        return v

    @field_validator("preferred_companion_type")
    @classmethod
    def validate_companion(cls, v: str | None) -> str | None:
        if v is not None and v not in CompanionType._value2member_map_:
            raise ValueError(f"'{v}'는 유효한 동행 유형이 아니에요.")
        return v

    @field_validator("preferred_budget")
    @classmethod
    def validate_budget(cls, v: str | None) -> str | None:
        if v is not None and v not in BudgetTier._value2member_map_:
            raise ValueError(f"'{v}'는 유효한 예산대가 아니에요.")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str | None) -> str | None:
        if v is not None and v not in GenderType._value2member_map_:
            raise ValueError(f"'{v}'는 유효한 성별 값이 아니에요.")
        return v

    @field_validator("dating_stage")
    @classmethod
    def validate_dating_stage(cls, v: str | None) -> str | None:
        if v is not None and v not in DatingStage._value2member_map_:
            raise ValueError(f"'{v}'는 유효한 연애 단계가 아니에요.")
        return v


# ---------------------------------------------------------------------------
# GET /v1/users/me
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_me(
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = (
        await db.execute(
            text("""
                SELECT id, nickname, email, profile_image_url,
                       preferred_companion_type, preferred_theme_tags,
                       preferred_budget, gender, birth_year, dating_stage,
                       home_station_id, marketing_agreed, created_at
                FROM users
                WHERE id = :uid
            """),
            {"uid": current_user["id"]},
        )
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "사용자를 찾을 수 없어요."})

    return {
        "success": True,
        "data": {
            "user_id": row["id"],
            "nickname": row["nickname"],
            "email": row["email"],
            "profile_image_url": row["profile_image_url"],
            "preferred_companion_type": row["preferred_companion_type"],
            "preferred_theme_tags": list(row["preferred_theme_tags"] or []),
            "preferred_budget": row["preferred_budget"],
            "gender": row["gender"],
            "birth_year": row["birth_year"],
            "dating_stage": row["dating_stage"],
            "home_station_id": row["home_station_id"],
            "marketing_agreed": row["marketing_agreed"],
            "created_at": str(row["created_at"]) if row["created_at"] else None,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# PATCH /v1/users/me
# ---------------------------------------------------------------------------

@router.patch("/me")
async def update_me(
    body: UserUpdateRequest,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user["id"]

    # Build SET clauses only for provided fields
    set_parts: list[str] = ["updated_at = now()"]
    params: dict[str, Any] = {"uid": uid}

    if body.nickname is not None:
        set_parts.append("nickname = :nickname")
        params["nickname"] = body.nickname

    if body.preferred_companion_type is not None:
        set_parts.append("preferred_companion_type = CAST(:pct AS companion_type)")
        params["pct"] = body.preferred_companion_type

    if body.preferred_theme_tags is not None:
        # asyncpg cannot bind a Python str to an ARRAY(enum) target via :param —
        # it expects a native sequence. Values are already validated against
        # ThemeTag above, so inlining as literals is safe (see course_generator.py).
        if body.preferred_theme_tags:
            tag_literals = ", ".join(f"'{t}'::theme_tag" for t in body.preferred_theme_tags)
            set_parts.append(f"preferred_theme_tags = ARRAY[{tag_literals}]")
        else:
            set_parts.append("preferred_theme_tags = ARRAY[]::theme_tag[]")

    if body.preferred_budget is not None:
        set_parts.append("preferred_budget = CAST(:pb AS budget_tier)")
        params["pb"] = body.preferred_budget

    if body.gender is not None:
        set_parts.append("gender = CAST(:gender AS gender_type)")
        params["gender"] = body.gender

    if body.birth_year is not None:
        set_parts.append("birth_year = :birth_year")
        params["birth_year"] = body.birth_year

    if body.dating_stage is not None:
        set_parts.append("dating_stage = CAST(:dating_stage AS dating_stage)")
        params["dating_stage"] = body.dating_stage

    if body.home_station_id is not None:
        set_parts.append("home_station_id = :home_station_id")
        params["home_station_id"] = body.home_station_id

    if body.terms_agreed_at is not None:
        set_parts.append("terms_agreed_at = :terms_agreed_at")
        params["terms_agreed_at"] = body.terms_agreed_at

    if body.privacy_agreed_at is not None:
        set_parts.append("privacy_agreed_at = :privacy_agreed_at")
        params["privacy_agreed_at"] = body.privacy_agreed_at

    if body.marketing_agreed is not None:
        set_parts.append("marketing_agreed = :marketing_agreed")
        params["marketing_agreed"] = body.marketing_agreed
        if body.marketing_agreed:
            set_parts.append("marketing_agreed_at = now()")

    if len(set_parts) == 1:
        # Only updated_at — nothing to change
        raise HTTPException(
            status_code=400,
            detail={"code": "NOTHING_TO_UPDATE", "message": "변경할 내용이 없어요."},
        )

    row = (
        await db.execute(
            text(f"""
                UPDATE users
                SET {', '.join(set_parts)}
                WHERE id = :uid
                RETURNING id, nickname, email, profile_image_url,
                          preferred_companion_type, preferred_theme_tags,
                          preferred_budget, gender, birth_year, dating_stage,
                          home_station_id, marketing_agreed, updated_at
            """),
            params,
        )
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "사용자를 찾을 수 없어요."})

    await db.commit()

    return {
        "success": True,
        "data": {
            "user_id": row["id"],
            "nickname": row["nickname"],
            "email": row["email"],
            "profile_image_url": row["profile_image_url"],
            "preferred_companion_type": row["preferred_companion_type"],
            "preferred_theme_tags": list(row["preferred_theme_tags"] or []),
            "preferred_budget": row["preferred_budget"],
            "gender": row["gender"],
            "birth_year": row["birth_year"],
            "dating_stage": row["dating_stage"],
            "home_station_id": row["home_station_id"],
            "marketing_agreed": row["marketing_agreed"],
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# DELETE /v1/users/me  (PIPA anonymisation, SCRUM-56)
# ---------------------------------------------------------------------------

@router.delete("/me")
async def delete_me(
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user["id"]

    # 1. Revoke all refresh tokens (covers Redis-less token invalidation)
    await db.execute(
        text("UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = :uid AND revoked_at IS NULL"),
        {"uid": uid},
    )

    # 2. Anonymise course reviews — keep rows for stats, unlink user
    await db.execute(
        text("UPDATE course_reviews SET user_id = NULL WHERE user_id = :uid"),
        {"uid": uid},
    )

    # 3. Anonymise recommendation_requests — unlink user_id (PIPA: 이용 기록 비식별화)
    await db.execute(
        text("UPDATE recommendation_requests SET user_id = NULL WHERE user_id = :uid"),
        {"uid": uid},
    )

    # 4. Anonymise user row: status=WITHDRAWN, PII zeroed, oauth_id obfuscated, withdrawn_at recorded
    await db.execute(
        text("""
            UPDATE users SET
                status             = 'WITHDRAWN',
                oauth_id           = 'withdrawn_' || id::text,
                nickname           = '탈퇴한 사용자',
                email              = NULL,
                profile_image_url  = NULL,
                gender             = 'UNKNOWN',
                birth_year         = NULL,
                dating_stage       = 'UNKNOWN',
                preferred_companion_type = NULL,
                preferred_theme_tags     = '{}',
                preferred_budget         = NULL,
                home_station_id          = NULL,
                withdrawn_at       = now(),
                updated_at         = now()
            WHERE id = :uid
        """),
        {"uid": uid},
    )

    await db.commit()

    return {"success": True, "data": {"deleted": True}, "error": None}
