"""
Zohra — InternalLinkCandidate model.

Stores identified internal linking suggestions mapping specific draft sections
to existing relevant site content or pillar articles for Part 7 finalization.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class InternalLinkCandidate(ZohraBase):
    __tablename__ = "internal_link_candidates"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_section_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_content_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)
    recommended_anchor_context: Mapped[str] = mapped_column(Text, nullable=False)

    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("ix_ilc_project_section", "draft_project_id", "source_section_id"),
    )
