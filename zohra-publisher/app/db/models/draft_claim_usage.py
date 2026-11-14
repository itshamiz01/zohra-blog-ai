"""
Zohra — DraftClaimUsage model.

Tracks allocation, placement, and verified usage of Part 4 claims within specific draft sections.
Enforces attribution requirements and prevents prohibited or unverified claims.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class DraftClaimUsage(ZohraBase):
    __tablename__ = "draft_claim_usage"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    usage_type: Mapped[str] = mapped_column(String(32), nullable=False, default="primary")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    citation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_dcu_project_claim", "draft_project_id", "claim_id"),
        Index("ix_dcu_project_section", "draft_project_id", "section_id"),
    )
