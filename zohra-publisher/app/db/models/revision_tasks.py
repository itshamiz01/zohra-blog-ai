"""
Zohra — RevisionTask model.

Stores targeted section-level revision tasks generated when draft quality or grounding
gate indicates specific repairable flaws (e.g. redundancy, clarity, citation deficiency).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class RevisionTask(ZohraBase):
    __tablename__ = "revision_tasks"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    draft_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    section_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")  # pending, in_progress, resolved, skipped
    before_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    after_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_rt_project_status", "draft_project_id", "status"),
    )
