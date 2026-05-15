from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    songkick_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    artist: Mapped[str] = mapped_column(String(255), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    venue: Mapped[str] = mapped_column(String(255), default="")
    songkick_url: Mapped[str] = mapped_column(String(512))
    ticket_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (Index("ix_events_artist_lower", "artist"),)
