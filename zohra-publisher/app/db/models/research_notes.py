"""
Zohra — ResearchNote model.

Internal investigator/writer notes, observation warnings, and audit annotations.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase


class ResearchNote(ZohraBase):
    __tablename__ = "research_notes"

    research_project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # observation, warning, follow_up, uncertainty, source_issue, writer_note
    note_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="observation", index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True)

    __table_args__ = (
        Index("ix_res_note_proj_type", "research_project_id", "note_type"),
    )
