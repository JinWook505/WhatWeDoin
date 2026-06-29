from sqlalchemy import String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CourseCache(Base):
    __tablename__ = "course_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
