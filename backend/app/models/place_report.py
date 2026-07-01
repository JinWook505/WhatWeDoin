from sqlalchemy import BigInteger, ForeignKey, SmallInteger, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PlaceRatingReport(Base):
    __tablename__ = "place_rating_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    place_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("places.place_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    rating_x2: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
