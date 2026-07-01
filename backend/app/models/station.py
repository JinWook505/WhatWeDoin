from sqlalchemy import BigInteger, Boolean, Double, ForeignKey, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Station(Base):
    __tablename__ = "stations"

    station_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(64))
    external_source: Mapped[str | None] = mapped_column(String(10))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float] = mapped_column(Double, nullable=False)
    lng: Mapped[float] = mapped_column(Double, nullable=False)
    # geom is a PostGIS GEOGRAPHY(Point, 4326) — managed via raw SQL in migration
    is_supported: Mapped[bool] = mapped_column(Boolean, server_default=text("TRUE"))
    created_at: Mapped[str | None] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    lines: Mapped[list["StationLine"]] = relationship(back_populates="station")


class StationLine(Base):
    __tablename__ = "station_lines"

    station_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("stations.station_id"),
        primary_key=True,
    )
    line_no: Mapped[str] = mapped_column(String(20), primary_key=True)

    station: Mapped["Station"] = relationship(back_populates="lines")
