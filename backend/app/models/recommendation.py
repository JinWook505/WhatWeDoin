from sqlalchemy import BigInteger, Enum, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ServedFrom


class RecommendationRequest(Base):
    __tablename__ = "recommendation_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    station_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    parsed_input: Mapped[dict | None] = mapped_column(JSONB)
    exclude_place_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(BigInteger), server_default=text("'{}'")
    )
    served_from: Mapped[str] = mapped_column(
        Enum(ServedFrom, name="served_from"), nullable=False
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    course_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
