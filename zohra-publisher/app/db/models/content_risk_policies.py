"""
Zohra — ContentRiskPolicy model (Part 6).

Configurable safety, factual integrity, and human review policies per risk category
(health, finance, legal, political, public allegations, general).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ContentRiskPolicy(ZohraBase):
    __tablename__ = "content_risk_policies"

    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM", index=True)

    minimum_research_quality: Mapped[float] = mapped_column(Float, nullable=False, default=80.0)
    minimum_grounding: Mapped[float] = mapped_column(Float, nullable=False, default=95.0)
    minimum_factual_score: Mapped[float] = mapped_column(Float, nullable=False, default=95.0)
    minimum_citation_score: Mapped[float] = mapped_column(Float, nullable=False, default=90.0)
    minimum_overall_quality: Mapped[float] = mapped_column(Float, nullable=False, default=85.0)

    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_publish_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    freshness_requirement_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strict_quote_enforcement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    political_neutrality_enforced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    policy_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1.0")
    rules_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_crp_cat_risk", "category", "risk_level", unique=True),
    )
