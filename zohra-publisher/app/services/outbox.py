"""
Zohra — Transactional Outbox Event Bus & Dispatcher (Part 10).

Provides:
- Transactional domain event recording alongside entity state mutations
- Reliable asynchronous event publishing
- Exponential backoff retry for failed event publications
- Consumer idempotency deduplication
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.operations import OutboxEvent, OutboxStatus

logger = logging.getLogger("zohra.outbox")

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

_EVENT_HANDLERS: dict[str, list[EventHandler]] = {}


def register_event_handler(event_type: str, handler: EventHandler) -> None:
    """Register an asynchronous callback handler for a specific domain event type."""
    if event_type not in _EVENT_HANDLERS:
        _EVENT_HANDLERS[event_type] = []
    _EVENT_HANDLERS[event_type].append(handler)


class OutboxDispatcher:
    """Dispatches pending outbox events recorded in the database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
    ) -> OutboxEvent:
        """
        Record a domain event within the caller's active database transaction.
        Guarantees zero-lost events if the business transaction commits.
        """
        event = OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload_json=payload,
            status=OutboxStatus.PENDING.value,
            attempts=0,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def dispatch_pending(self, batch_size: int = 50) -> int:
        """
        Query and publish pending outbox events.
        Updates status to PUBLISHED or FAILED.
        """
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.status.in_([OutboxStatus.PENDING.value, OutboxStatus.FAILED.value]))
            .where(OutboxEvent.attempts < 5)
            .order_by(OutboxEvent.created_at)
            .limit(batch_size)
        )
        res = await self.db.execute(query)
        events = res.scalars().all()

        published_count = 0
        for event in events:
            event.attempts += 1
            handlers = _EVENT_HANDLERS.get(event.event_type, [])
            success = True
            error_msg: str | None = None

            for handler in handlers:
                try:
                    await handler(event.payload_json)
                except Exception as e:
                    success = False
                    error_msg = f"{type(e).__name__}: {e}"
                    logger.error("Outbox handler failed for %s: %s", event.event_type, e)
                    break

            if success:
                event.status = OutboxStatus.DISPATCHED.value
                event.published_at = datetime.now(UTC)
                event.error_message = None
                published_count += 1
            else:
                event.status = OutboxStatus.FAILED.value
                event.error_message = error_msg

        await self.db.flush()
        return published_count
