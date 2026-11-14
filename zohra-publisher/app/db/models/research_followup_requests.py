"""
Zohra — ResearchFollowupRequest model.

Stores structured requests back to Part 4 when drafting identifies critical missing facts
that are required to satisfy the article promise or user search intent.
Prevents the Writer from hallucinating missing facts.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class ResearchFollowupRequest(ZohraBase):
    __tablename__ = "research_followup_requests"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="high")  # critical, high, medium, low
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending, in_progress, resolved, cancelled

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_rfr_draft_project", "draft_project_id"),
        Index("ix_rfr_status", "status"),
    )
