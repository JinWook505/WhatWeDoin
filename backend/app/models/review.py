from sqlalchemy import BigInteger, Enum, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ReportReason


class CourseReview(Base):
    __tablename__ = "course_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    course_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(String)
    links: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )


class CourseReviewReport(Base):
    __tablename__ = "course_review_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    review_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(
        Enum(ReportReason, name="report_reason"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
