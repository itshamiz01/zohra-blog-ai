"""
Zohra — EntityRelationship model.

Factual relationships between entities discovered during deep research (Knowledge Graph edges).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class EntityRelationship(ZohraBase):
    __tablename__ = "entity_relationships"

    research_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    subject_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # created_by, owned_by, acquired_by, competes_with,
    # available_in, released_by, part_of, uses, integrates_with
    predicate: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    object_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    object_value: Mapped[str | None] = mapped_column(String(255), nullable=True)

    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_ent_rel_subj_pred", "subject_entity_id", "predicate"),
    )
