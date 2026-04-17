from datetime import datetime
from sqlalchemy import Boolean, String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    short_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # index=True lets the expiry cleanup query use an index scan instead of a full table scan.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Soft-delete flag.  Expired URLs are marked inactive rather than dropped
    # so that analytics data in the clicks table is preserved.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Click(Base):
    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # ForeignKey with CASCADE ensures clicks are deleted when the parent URL
    # row is hard-deleted (e.g. via an admin purge), preventing orphaned rows.
    short_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("urls.short_code", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
