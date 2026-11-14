"""
Zohra — Claim model.

Discrete atomic factual propositions extracted from sources with canonical representation
(subject, predicate, object, qualifiers), importance, verification levels, and writer policies.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class Claim(ZohraBase):
    __tablename__ = "claims"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_claim: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    # fact, number, date, price, capability, limitation, comparison,
    # historical, quote, prediction, opinion, attribution, availability, requirement, definition
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False, default="fact", index=True)

    subject_entity: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    predicate: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    object_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)

    temporal_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # critical, major, supporting, minor
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="major", index=True)

    # unverified, weakly_supported, supported, strongly_supported,
    # disputed, contradicted, outdated, unknown
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unverified", index=True
    )

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # 0 = No evidence, 1 = Single low/mod source, 2 = Single strong source,
    # 3 = Multiple supporting sources, 4 = Primary source + independent corroboration,
    # 5 = Exceptionally strong multi-source evidence
    verification_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    time_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attribution_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # SAFE_TO_STATE, REQUIRE_ATTRIBUTION, DO_NOT_STATE_AS_FACT, TIME_SENSITIVE_CONTEXT
    writer_policy: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DO_NOT_STATE_AS_FACT", index=True
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_claims_proj_importance", "research_project_id", "importance"),
        Index("ix_claims_proj_status", "research_project_id", "status"),
        Index("ix_claims_proj_policy", "research_project_id", "writer_policy"),
    )
