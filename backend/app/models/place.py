from sqlalchemy import BigInteger, Double, Enum, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import OAuthProvider, ThemeTag


class Place(Base):
    __tablename__ = "places"

    place_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    external_source: Mapped[str] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lng: Mapped[float] = mapped_column(Double, nullable=False)
    # geom: GEOGRAPHY(Point, 4326) — managed via raw SQL in migration
    price_range: Mapped[str | None] = mapped_column(String(50))
    business_hours: Mapped[dict | None] = mapped_column(JSONB)
    map_url: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String(30))
    thumbnail_url: Mapped[str | None] = mapped_column(String)
    theme_tags: Mapped[list[str]] = mapped_column(
        ARRAY(Enum(ThemeTag, name="theme_tag")), server_default=text("'{}'")
    )
    status: Mapped[str] = mapped_column(String(10), server_default="OPEN")
    last_synced_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
