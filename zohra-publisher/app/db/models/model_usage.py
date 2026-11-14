"""
model_usage — Per-call LLM token/cost accounting.
Foundation for the Cost Control Engine.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ZohraBase


class ModelUsage(ZohraBase):
    __tablename__ = "model_usage"

    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    estimated_input_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_output_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_total_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")

    operation: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_model_usage_provider_model", "provider", "model"),
        Index("ix_model_usage_created_at", "created_at"),
    )
