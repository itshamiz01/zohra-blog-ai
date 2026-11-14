"""Zohra Part 2 — Trend Intelligence API endpoints.

GET /api/v1/trends
GET /api/v1/trends/top
GET /api/v1/trends/emerging
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EventStatus
from app.core.security import require_admin_token
from app.db.models.events import Event
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.schemas.discovery import TrendItemResponse

router = APIRouter(prefix="/trends", tags=["Trends"])


def _to_trend_item(e: Event) -> TrendItemResponse:
    return TrendItemResponse(
        event_id=e.id,
        title=e.canonical_title,
        category=e.primary_category,
        event_type=e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
        trend_score=e.trend_score,
        velocity_score=e.velocity_score,
        momentum_score=e.momentum_score,
        confidence_score=e.confidence_score,
        source_diversity_score=e.source_diversity_score,
        source_count=e.source_count,
        document_count=e.document_count,
        status=e.status.value if hasattr(e.status, "value") else str(e.status),
        classification=e.trend_classification.value
        if hasattr(e.trend_classification, "value")
        else str(e.trend_classification),
        first_seen_at=e.first_seen_at,
        last_seen_at=e.last_seen_at,
        trend_reasons=e.trend_reasons or [],
        is_qualified=e.is_qualified_for_opportunity,
    )


@router.get("", response_model=ApiResponse[list[TrendItemResponse]])
async def list_trends(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[TrendItemResponse]]:
    """List ranked trend signals across monitored events."""
    query = (
        select(Event)
        .where(Event.status.notin_([EventStatus.REJECTED, EventStatus.ARCHIVED]))
        .order_by(desc(Event.trend_score), desc(Event.last_seen_at))
    )
    if category:
        query = query.where(Event.primary_category == category)

    query = query.limit(limit).offset(offset)
    res = await db.execute(query)
    events = list(res.scalars().all())

    return ApiResponse(success=True, data=[_to_trend_item(e) for e in events])


@router.get("/top", response_model=ApiResponse[list[TrendItemResponse]])
async def get_top_trends(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[TrendItemResponse]]:
    """Get the highest-scoring trends in the engine."""
    query = (
        select(Event)
        .where(
            Event.status.in_(
                [
                    EventStatus.ACTIVE,
                    EventStatus.ACCELERATING,
                    EventStatus.PEAKING,
                ]
            )
        )
        .order_by(desc(Event.trend_score))
        .limit(limit)
    )
    res = await db.execute(query)
    events = list(res.scalars().all())
    return ApiResponse(success=True, data=[_to_trend_item(e) for e in events])


@router.get("/emerging", response_model=ApiResponse[list[TrendItemResponse]])
async def get_emerging_trends(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[TrendItemResponse]]:
    """Get accelerating early-stage signals with rising momentum."""
    query = (
        select(Event)
        .where(Event.status.in_([EventStatus.EMERGING, EventStatus.ACCELERATING]))
        .order_by(desc(Event.velocity_score), desc(Event.first_seen_at))
        .limit(limit)
    )
    res = await db.execute(query)
    events = list(res.scalars().all())
    return ApiResponse(success=True, data=[_to_trend_item(e) for e in events])
