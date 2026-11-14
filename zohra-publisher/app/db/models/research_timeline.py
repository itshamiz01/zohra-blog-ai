"""
Zohra — ResearchTimelineEvent model.

Structured chronological events with explicit temporal precision
(exact_timestamp, date, month, year, approximate, unknown) preserving uncertain dates.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchTimelineEvent(ZohraBase):
    __tablename__ = "research_timeline_events"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # exact_timestamp, date, month, year, approximate, unknown
    event_time_precision: Mapped[str] = mapped_column(
        String(50), nullable=False, default="date", index=True
    )
    time_raw_text: Mapped[str | None] = mapped_column(String(255), nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="major", index=True)

    source_ids: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_time_proj_time", "research_project_id", "event_time"),
    )
