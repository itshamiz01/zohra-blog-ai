"""Zohra Part 2 — Event Intelligence API endpoints.

GET  /api/v1/events
GET  /api/v1/events/trending
GET  /api/v1/events/emerging
GET  /api/v1/events/{id}
GET  /api/v1/events/{id}/documents
GET  /api/v1/events/{id}/sources
GET  /api/v1/events/{id}/entities
GET  /api/v1/events/{id}/snapshots
POST /api/v1/events/merge
POST /api/v1/events/{id}/split
POST /api/v1/events/{id}/reject
POST /api/v1/events/{id}/restore
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import EventStatus
from app.core.security import require_admin_token
from app.db.models.entities import DocumentEntity, Entity
from app.db.models.event_documents import EventDocument
from app.db.models.event_snapshots import EventSnapshot
from app.db.models.events import Event
from app.db.models.source_documents import SourceDocument
from app.db.models.sources import Source
from app.db.session import get_db
from app.discovery.clustering.operations import merge_events, split_event
from app.schemas.api import ApiResponse
from app.schemas.discovery import (
    EntityResponse,
    EventDetailResponse,
    EventDocumentResponse,
    EventMergeRequest,
    EventResponse,
    EventSnapshotResponse,
    EventSplitRequest,
    SourceResponse,
)
from app.services.audit import AuditService

router = APIRouter(prefix="/events", tags=["Events"])


@router.get("", response_model=ApiResponse[list[EventResponse]])
async def list_events(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    country: str | None = None,
    language: str | None = None,
    status: EventStatus | None = None,
    min_trend_score: float | None = Query(default=None, ge=0.0, le=100.0),
    min_confidence: float | None = Query(default=None, ge=0.0, le=100.0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[list[EventResponse]]:
    """List event clusters with multi-criteria filtering."""
    query = select(Event).order_by(desc(Event.trend_score), desc(Event.last_seen_at))

    if category:
        query = query.where(Event.primary_category == category)
    if country:
        query = query.where(Event.country == country)
    if language:
        query = query.where(Event.language == language)
    if status:
        query = query.where(Event.status == status)
    if min_trend_score is not None:
        query = query.where(Event.trend_score >= min_trend_score)
    if min_confidence is not None:
        query = query.where(Event.confidence_score >= min_confidence)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    events = list(result.scalars().all())

    return ApiResponse(
        success=True,
        data=[EventResponse.model_validate(e) for e in events],
    )


@router.get("/trending", response_model=ApiResponse[list[EventResponse]])
async def get_trending_events(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[EventResponse]]:
    """Get top trending events with high momentum & velocity."""
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
    )
    if category:
        query = query.where(Event.primary_category == category)
    query = query.limit(limit)

    result = await db.execute(query)
    events = list(result.scalars().all())
    return ApiResponse(success=True, data=[EventResponse.model_validate(e) for e in events])


@router.get("/emerging", response_model=ApiResponse[list[EventResponse]])
async def get_emerging_events(
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[EventResponse]]:
    """Get newly emerging events (recently discovered, rising velocity)."""
    query = (
        select(Event)
        .where(
            Event.status.in_(
                [
                    EventStatus.EMERGING,
                    EventStatus.ACCELERATING,
                ]
            )
        )
        .order_by(desc(Event.velocity_score), desc(Event.first_seen_at))
        .limit(limit)
    )
    result = await db.execute(query)
    events = list(result.scalars().all())
    return ApiResponse(success=True, data=[EventResponse.model_validate(e) for e in events])


@router.get("/{event_id}", response_model=ApiResponse[EventDetailResponse])
async def get_event_detail(
    event_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[EventDetailResponse]:
    """Get comprehensive event detail including associated documents and entities."""
    stmt = (
        select(Event)
        .options(
            selectinload(Event.event_documents).selectinload(EventDocument.document),
        )
        .where(Event.id == event_id)
    )
    res = await db.execute(stmt)
    event = res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Map documents
    doc_responses = []
    doc_ids = []
    for ed in event.event_documents:
        doc_ids.append(ed.document_id)
        doc_responses.append(
            EventDocumentResponse(
                document_id=ed.document_id,
                title=ed.document.title if ed.document else "",
                url=ed.document.url if ed.document else "",
                similarity_score=ed.similarity_score,
                relevance_score=ed.relevance_score,
                is_primary_source=ed.is_primary_source,
                is_original_report=ed.is_original_report,
                created_at=ed.created_at,
            )
        )

    # Fetch entities associated with these documents
    entities: list[EntityResponse] = []
    if doc_ids:
        ent_stmt = (
            select(Entity)
            .join(DocumentEntity, DocumentEntity.entity_id == Entity.id)
            .where(DocumentEntity.document_id.in_(doc_ids))
            .distinct()
        )
        ent_res = await db.execute(ent_stmt)
        entities = [EntityResponse.model_validate(e) for e in ent_res.scalars().all()]

    detail = EventDetailResponse(
        **EventResponse.model_validate(event).model_dump(),
        primary_source_document_id=event.primary_source_document_id,
        contradiction_notes=event.contradiction_notes,
        documents=doc_responses,
        entities=entities,
    )
    return ApiResponse(success=True, data=detail)


@router.get("/{event_id}/documents", response_model=ApiResponse[list[EventDocumentResponse]])
async def get_event_documents(
    event_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[EventDocumentResponse]]:
    """List all documents attached to this event cluster."""
    stmt = (
        select(EventDocument)
        .options(selectinload(EventDocument.document))
        .where(EventDocument.event_id == event_id)
        .order_by(desc(EventDocument.is_primary_source), desc(EventDocument.similarity_score))
    )
    res = await db.execute(stmt)
    eds = list(res.scalars().all())

    data = [
        EventDocumentResponse(
            document_id=ed.document_id,
            title=ed.document.title if ed.document else "",
            url=ed.document.url if ed.document else "",
            similarity_score=ed.similarity_score,
            relevance_score=ed.relevance_score,
            is_primary_source=ed.is_primary_source,
            is_original_report=ed.is_original_report,
            created_at=ed.created_at,
        )
        for ed in eds
    ]
    return ApiResponse(success=True, data=data)


@router.get("/{event_id}/sources", response_model=ApiResponse[list[SourceResponse]])
async def get_event_sources(
    event_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[SourceResponse]]:
    """List all distinct sources reporting on this event."""
    stmt = (
        select(Source)
        .join(SourceDocument, SourceDocument.source_id == Source.id)
        .join(EventDocument, EventDocument.document_id == SourceDocument.id)
        .where(EventDocument.event_id == event_id)
        .distinct()
    )
    res = await db.execute(stmt)
    sources = list(res.scalars().all())
    return ApiResponse(success=True, data=[SourceResponse.model_validate(s) for s in sources])


@router.get("/{event_id}/entities", response_model=ApiResponse[list[EntityResponse]])
async def get_event_entities(
    event_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[list[EntityResponse]]:
    """List extracted entities mentioned in this event cluster."""
    stmt = (
        select(Entity)
        .join(DocumentEntity, DocumentEntity.entity_id == Entity.id)
        .join(EventDocument, EventDocument.document_id == DocumentEntity.document_id)
        .where(EventDocument.event_id == event_id)
        .distinct()
    )
    res = await db.execute(stmt)
    entities = list(res.scalars().all())
    return ApiResponse(success=True, data=[EntityResponse.model_validate(e) for e in entities])


@router.get("/{event_id}/snapshots", response_model=ApiResponse[list[EventSnapshotResponse]])
async def get_event_snapshots(
    event_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
) -> ApiResponse[list[EventSnapshotResponse]]:
    """Retrieve temporal progression snapshots of velocity, momentum and trend."""
    stmt = (
        select(EventSnapshot)
        .where(EventSnapshot.event_id == event_id)
        .order_by(EventSnapshot.timestamp.asc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    snapshots = list(res.scalars().all())
    return ApiResponse(
        success=True,
        data=[EventSnapshotResponse.model_validate(s) for s in snapshots],
    )


@router.post("/merge", response_model=ApiResponse[EventResponse])
async def merge_events_endpoint(
    payload: EventMergeRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[EventResponse]:
    """Administrative override: merge two related event clusters with full audit trail."""
    target_event = await merge_events(
        db=db,
        source_event_id=payload.source_event_id,
        target_event_id=payload.target_event_id,
        reason=payload.reason,
        actor_id=_token.get("sub"),
    )
    return ApiResponse(
        success=True,
        data=EventResponse.model_validate(target_event),
        message=f"Merged event {payload.source_event_id} into {payload.target_event_id}",
    )


@router.post("/{event_id}/split", response_model=ApiResponse[EventResponse])
async def split_event_endpoint(
    event_id: UUID,
    payload: EventSplitRequest,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[EventResponse]:
    """Administrative override: split incorrectly clustered documents into a new event."""
    new_event = await split_event(
        db=db,
        parent_event_id=event_id,
        document_ids=payload.document_ids,
        new_event_title=payload.new_event_title,
        reason=payload.reason,
        actor_id=_token.get("sub"),
    )
    return ApiResponse(
        success=True,
        data=EventResponse.model_validate(new_event),
        message="Created split event successfully",
    )


@router.post("/{event_id}/reject", response_model=ApiResponse[EventResponse])
async def reject_event(
    event_id: UUID,
    reason: str,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[EventResponse]:
    """Reject an event cluster (spam, irrelevant, false claim)."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    event.status = EventStatus.REJECTED
    event.is_qualified_for_opportunity = False
    event.metadata_json = dict(event.metadata_json or {})
    event.metadata_json["rejection_reason"] = reason

    await AuditService.log_action(
        db=db,
        action="EVENT_REJECTED",
        entity_type="event",
        entity_id=str(event.id),
        actor_id=_token.get("sub"),
        changes={"reason": reason},
    )
    await db.commit()
    await db.refresh(event)
    return ApiResponse(
        success=True,
        data=EventResponse.model_validate(event),
        message="Event rejected",
    )


@router.post("/{event_id}/restore", response_model=ApiResponse[EventResponse])
async def restore_event(
    event_id: UUID,
    _token: Annotated[dict, Depends(require_admin_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse[EventResponse]:
    """Restore a previously rejected event."""
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    event.status = EventStatus.ACTIVE
    await AuditService.log_action(
        db=db,
        action="EVENT_RESTORED",
        entity_type="event",
        entity_id=str(event.id),
        actor_id=_token.get("sub"),
    )
    await db.commit()
    await db.refresh(event)
    return ApiResponse(
        success=True,
        data=EventResponse.model_validate(event),
        message="Event restored",
    )
