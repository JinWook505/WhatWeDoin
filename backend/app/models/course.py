from sqlalchemy import BigInteger, Enum, Integer, Numeric, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BudgetTier, CompanionType, ThemeTag


class Course(Base):
    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    station_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    theme_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Enum(ThemeTag, name="theme_tag")),
        nullable=False,
        server_default=text("'{}'"),
    )
    budget_tier: Mapped[str] = mapped_column(
        Enum(BudgetTier, name="budget_tier"), nullable=False
    )
    companion_type: Mapped[str] = mapped_column(
        Enum(CompanionType, name="companion_type"), nullable=False
    )
    head_count: Mapped[int | None] = mapped_column(SmallInteger)
    query_text: Mapped[str | None] = mapped_column(String)
    places: Mapped[dict] = mapped_column(JSONB, nullable=False)
    total_walking_distance_km: Mapped[float | None] = mapped_column(Numeric(4, 1))
    rating_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rating_sum: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    bayesian_score: Mapped[float] = mapped_column(Numeric(5, 2), server_default=text("0"))
    content_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    course_places: Mapped[list["CoursePlaces"]] = relationship(back_populates="course")


class CoursePlaces(Base):
    __tablename__ = "course_places"

    course_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    visit_order: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    place_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    walking_distance_to_next_km: Mapped[float | None] = mapped_column(Numeric(4, 1))
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    course: Mapped["Course"] = relationship(back_populates="course_places")
