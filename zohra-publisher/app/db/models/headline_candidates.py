"""
Zohra — HeadlineCandidate model.

Stores generated headline candidates with multi-factor scores:
intent, clarity, accuracy, SEO, brand fit, and overall ranking.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class HeadlineCandidate(ZohraBase):
    __tablename__ = "headline_candidates"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    style: Mapped[str] = mapped_column(String(64), nullable=False, default="direct")

    intent_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    clarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    seo_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    brand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_hc_draft_project_id", "draft_project_id"),
        Index("ix_hc_selected", "selected"),
    )
