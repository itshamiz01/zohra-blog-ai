"""
Zohra — ContentStrategy model.

Stores structured editorial intent, reader problem, job-to-be-done, differentiation,
information gain strategy, tone, depth, and target length ranges.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class ContentStrategy(ZohraBase):
    __tablename__ = "content_strategies"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reader_problem: Mapped[str] = mapped_column(Text, nullable=False)
    reader_goal: Mapped[str] = mapped_column(Text, nullable=False)
    search_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    content_goal: Mapped[str] = mapped_column(Text, nullable=False)

    recommended_content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    angle: Mapped[str] = mapped_column(Text, nullable=False)
    differentiation_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    information_gain_strategy: Mapped[str] = mapped_column(Text, nullable=False)

    tone: Mapped[str] = mapped_column(String(64), nullable=False, default="authoritative_approachable")
    depth: Mapped[str] = mapped_column(String(32), nullable=False, default="comprehensive")

    target_length_min: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)
    target_length_max: Mapped[int] = mapped_column(Integer, nullable=False, default=2400)

    conversion_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_cs_draft_project_id", "draft_project_id"),
    )
