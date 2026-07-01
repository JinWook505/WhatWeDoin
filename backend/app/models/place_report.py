from sqlalchemy import BigInteger, ForeignKey, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlaceRatingReport(Base):
    __tablename__ = "place_rating_reports"

    ip_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    place_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("places.place_id", ondelete="CASCADE"), primary_key=True)
    rating_x2: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
