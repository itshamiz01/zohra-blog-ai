"""
Zohra — Event Merge & Split Operations.

Supports administrative and automated event reorganization:
- Merging Event A into Event B (preserves document provenance, generates audit log)
- Splitting an Event (moves specific documents to a new event, preserves audit trail)
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.db.models.audit_logs import AuditLog
from app.db.models.event_documents import EventDocument
from app.db.models.events import Event

logger = get_logger("discovery.clustering.operations")


class EventOperationError(ZohraError):
    """Raised when an event merge or split fails."""

    def __init__(self, message: str):
        super().__init__(message, code="EVENT_OP_FAILED")


async def merge_events(
    session: AsyncSession,
    source_event_id: uuid.UUID,
    target_event_id: uuid.UUID,
    actor_id: str = "system",
    reason: str = "Duplicate event cluster detected",
) -> Event:
    """
    Merges source_event into target_event:
    1. Re-points all EventDocument rows from source_event to target_event.
    2. Marks source_event as merged_into_event_id and status='archived'.
    3. Updates document_count and source_count on target_event.
    4. Writes an AuditLog entry.
    """
    if source_event_id == target_event_id:
        raise EventOperationError("Cannot merge an event into itself")

    # Fetch both events
    res_source = await session.execute(select(Event).where(Event.id == source_event_id))
    source_event = res_source.scalar_one_or_none()
    if not source_event:
        raise EventOperationError(f"Source event {source_event_id} not found")

    res_target = await session.execute(select(Event).where(Event.id == target_event_id))
    target_event = res_target.scalar_one_or_none()
    if not target_event:
        raise EventOperationError(f"Target event {target_event_id} not found")

    # Fetch existing target documents to avoid unique constraint collisions
    res_existing = await session.execute(
        select(EventDocument.document_id).where(EventDocument.event_id == target_event_id)
    )
    target_doc_ids = set(res_existing.scalars().all())

    # Get source event documents
    res_source_docs = await session.execute(
        select(EventDocument).where(EventDocument.event_id == source_event_id)
    )
    source_docs = res_source_docs.scalars().all()

    for ed in source_docs:
        if ed.document_id in target_doc_ids:
            # Document is already in target event -> remove duplicate association
            await session.delete(ed)
        else:
            # Reassign to target event
            ed.event_id = target_event_id

    # Update source event status
    source_event.status = "archived"
    source_event.merged_into_event_id = target_event_id
    source_event.rejection_reason = f"Merged into {target_event_id}: {reason}"

    # Recalculate counts on target event
    target_event.document_count += len(source_docs)
    target_event.last_seen_at = max(target_event.last_seen_at, source_event.last_seen_at)
    target_event.first_seen_at = min(target_event.first_seen_at, source_event.first_seen_at)

    # Record Audit Log
    audit = AuditLog(
        actor_type="agent" if actor_id == "system" else "human",
        actor_id=actor_id,
        action="merge_events",
        entity_type="event",
        entity_id=target_event_id,
        previous_state=f"source={source_event_id}",
        new_state=f"target={target_event_id}; docs_moved={len(source_docs)}",
        metadata_json={"source_title": source_event.canonical_title, "reason": reason},
    )
    session.add(audit)
    await session.flush()

    logger.info(
        "Merged events",
        source_id=str(source_event_id),
        target_id=str(target_event_id),
        documents_reassigned=len(source_docs),
    )
    return target_event


async def split_event(
    session: AsyncSession,
    source_event_id: uuid.UUID,
    document_ids_to_split: list[uuid.UUID],
    new_event_title: str,
    actor_id: str = "system",
    reason: str = "Incorrect event cluster split",
) -> Event:
    """
    Splits specified document_ids from source_event into a brand new Event.
    """
    if not document_ids_to_split:
        raise EventOperationError("No document IDs provided to split")

    res_source = await session.execute(select(Event).where(Event.id == source_event_id))
    source_event = res_source.scalar_one_or_none()
    if not source_event:
        raise EventOperationError(f"Source event {source_event_id} not found")

    # Create new event cluster
    new_event = Event(
        canonical_title=new_event_title,
        summary=f"Split from event {source_event.canonical_title}",
        primary_category=source_event.primary_category,
        event_type=source_event.event_type,
        first_seen_at=source_event.first_seen_at,
        last_seen_at=source_event.last_seen_at,
        status="emerging",
        document_count=len(document_ids_to_split),
        source_count=1,
        language=source_event.language,
        country=source_event.country,
    )
    session.add(new_event)
    await session.flush()

    # Reassign EventDocument records
    await session.execute(
        update(EventDocument)
        .where(
            EventDocument.event_id == source_event_id,
            EventDocument.document_id.in_(document_ids_to_split),
        )
        .values(event_id=new_event.id)
    )

    # Decrement source event doc count
    source_event.document_count = max(1, source_event.document_count - len(document_ids_to_split))

    # Audit log
    audit = AuditLog(
        actor_type="agent" if actor_id == "system" else "human",
        actor_id=actor_id,
        action="split_event",
        entity_type="event",
        entity_id=new_event.id,
        previous_state=f"source_event={source_event_id}",
        new_state=f"new_event={new_event.id}; docs_moved={len(document_ids_to_split)}",
        metadata_json={"source_id": str(source_event_id), "reason": reason},
    )
    session.add(audit)
    await session.flush()

    logger.info(
        "Split event",
        source_id=str(source_event_id),
        new_event_id=str(new_event.id),
        documents_split=len(document_ids_to_split),
    )
    return new_event
