"""
Zohra — EditorialDraftPackage model.

The canonical immutable artifact handed off from Part 5 to Part 6.
Contains the complete structured article, claim citations, grounding analysis,
quality scores, SEO metadata, schema candidates, and internal link suggestions.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class EditorialDraftPackage(ZohraBase):
    __tablename__ = "editorial_draft_packages"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    research_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_opportunities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready_for_part6", index=True)

    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    grounding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    intent_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    package_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False)

    __table_args__ = (
        Index("ix_edp_draft_project_id", "draft_project_id"),
        Index("ix_edp_opp_id", "opportunity_id"),
    )
