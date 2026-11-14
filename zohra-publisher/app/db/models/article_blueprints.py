"""
Zohra — ArticleBlueprint model.

Stores structured blueprints containing working title, article promise, introduction goal,
detailed section outlines, claim allocations, citation plans, FAQ plans, and table plans.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ArticleBlueprint(ZohraBase):
    __tablename__ = "article_blueprints"

    draft_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("draft_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    working_title: Mapped[str] = mapped_column(String(512), nullable=False)
    article_promise: Mapped[str] = mapped_column(Text, nullable=False)

    primary_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_audience: Mapped[str | None] = mapped_column(String(256), nullable=True)

    introduction_goal: Mapped[str] = mapped_column(Text, nullable=False)
    sections_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False)
    conclusion_goal: Mapped[str] = mapped_column(Text, nullable=False)

    faq_plan_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    table_plan_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    citation_plan_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    internal_link_plan_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    claim_allocation_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_ab_draft_project_id", "draft_project_id"),
    )
