from sqlalchemy import BigInteger, ForeignKey, String, TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String)
    issued_at: Mapped[str] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at: Mapped[str] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at: Mapped[str | None] = mapped_column(TIMESTAMP(timezone=True))

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")  # noqa: F821


from app.models.user import User  # noqa: E402, F401
