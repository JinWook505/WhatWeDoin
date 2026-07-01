from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    BudgetTier,
    CompanionType,
    DatingStage,
    GenderType,
    OAuthProvider,
    ThemeTag,
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    oauth_provider: Mapped[str] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider"), nullable=False, server_default="KAKAO"
    )
    oauth_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(String)
    gender: Mapped[str | None] = mapped_column(
        Enum(GenderType, name="gender_type"), server_default="UNKNOWN"
    )
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    dating_stage: Mapped[str | None] = mapped_column(
        Enum(DatingStage, name="dating_stage"), server_default="UNKNOWN"
    )
    preferred_companion_type: Mapped[str | None] = mapped_column(
        Enum(CompanionType, name="companion_type")
    )
    preferred_theme_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(Enum(ThemeTag, name="theme_tag")), server_default=text("'{}'")
    )
    preferred_budget: Mapped[str | None] = mapped_column(
        Enum(BudgetTier, name="budget_tier")
    )
    home_station_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("stations.station_id"))
    terms_agreed_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    privacy_agreed_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    marketing_agreed: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    marketing_agreed_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(String(20), server_default="ACTIVE")
    last_login_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    withdrawn_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True))

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")  # noqa: F821


from app.models.auth import RefreshToken  # noqa: E402, F401
