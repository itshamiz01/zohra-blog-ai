"""Zohra Part 2 — Celery tasks for Global Discovery & Trend Intelligence.

Queues:
- discovery: source polling, RSS fetching, query execution
- processing: document normalization, entity extraction, clustering
- maintenance: trend score re-evaluation, retention cleanup
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.constants import CircuitBreakerState, EventStatus
from app.db.models.event_documents import EventDocument
from app.db.models.event_snapshots import EventSnapshot
from app.db.models.events import Event
from app.db.models.source_documents import SourceDocument
from app.db.models.sources import Source
from app.db.session import get_session_factory
from app.discovery.pipeline import DiscoveryPipeline
from app.discovery.scoring.lifecycle import evaluate_event_lifecycle
from app.discovery.scoring.trend import calculate_event_trend
from app.workers.celery_app import celery_app

logger = get_task_logger(__name__)


def _run_async(coro):
    """Run an async coroutine inside Celery task."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(name="discovery.poll_source", bind=True, max_retries=3, queue="discovery")
def poll_source_task(self, source_id_str: str) -> dict:
    """Poll a single discovery source and run it through pipeline."""

    async def _async_task():
        source_id = UUID(source_id_str)
        session_factory = get_session_factory()
        async with session_factory() as db:
            pipeline = DiscoveryPipeline(db=db)
            result = await pipeline.poll_source(source_id)
            await db.commit()
            return result

    try:
        return _run_async(_async_task())
    except Exception as exc:
        logger.error(f"Failed to poll source {source_id_str}: {exc}")
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(name="discovery.poll_all_due_sources", bind=True, queue="discovery")
def poll_all_due_sources_task(self) -> dict:
    """Check all enabled sources due for polling and execute discovery cycle."""

    async def _async_task():
        settings = get_settings()
        if not settings.AUTONOMY_ENABLED or not settings.ENABLE_DISCOVERY:
            return {"status": "skipped", "reason": "autonomy_or_discovery_disabled"}

        session_factory = get_session_factory()
        async with session_factory() as db:
            now = datetime.now(UTC)
            # Find enabled sources that are not circuit-breaker OPEN
            stmt = select(Source).where(
                Source.is_enabled.is_(True),
                Source.circuit_breaker_state != CircuitBreakerState.OPEN.value,
            )
            res = await db.execute(stmt)
            sources = list(res.scalars().all())

            due_source_ids = []
            for src in sources:
                if not src.last_checked_at:
                    due_source_ids.append(src.id)
                else:
                    elapsed_min = (now - src.last_checked_at).total_seconds() / 60.0
                    if elapsed_min >= src.polling_interval_minutes:
                        due_source_ids.append(src.id)

            if not due_source_ids:
                return {"status": "noop", "due_count": 0}

            pipeline = DiscoveryPipeline(db=db)
            cycle_res = await pipeline.run_cycle(source_ids=due_source_ids)
            await db.commit()
            return cycle_res

    return _run_async(_async_task())


@celery_app.task(name="discovery.calculate_trend", bind=True, queue="maintenance")
def calculate_trend_task(self) -> dict:
    """Periodic task: re-evaluates velocity, momentum, trend score, lifecycle for active events."""

    async def _async_task():
        session_factory = get_session_factory()
        async with session_factory() as db:
            stmt = (
                select(Event)
                .options(
                    selectinload(Event.event_documents)
                    .selectinload(EventDocument.document)
                    .selectinload(SourceDocument.source)
                )
                .where(
                    Event.status.in_(
                        [
                            EventStatus.EMERGING,
                            EventStatus.ACTIVE,
                            EventStatus.ACCELERATING,
                            EventStatus.PEAKING,
                            EventStatus.STABLE,
                            EventStatus.DECLINING,
                        ]
                    )
                )
            )
            res = await db.execute(stmt)
            events = list(res.scalars().all())
            updated_count = 0

            for ev in events:
                docs = [ed.document for ed in ev.event_documents if ed.document]
                if not docs:
                    continue

                sources = [d.source for d in docs if d.source]
                trend_res = calculate_event_trend(event=ev, documents=docs, sources=sources)

                ev.velocity_score = trend_res["velocity_score"]
                ev.momentum_score = trend_res["momentum_score"]
                ev.source_diversity_score = trend_res["source_diversity_score"]
                ev.freshness_score = trend_res["freshness_score"]
                ev.authority_score = trend_res["authority_score"]
                ev.confidence_score = trend_res["confidence_score"]
                ev.trend_score = trend_res["trend_score"]
                ev.trend_classification = trend_res["classification"]
                ev.trend_reasons = trend_res["reasons"]
                ev.is_qualified_for_opportunity = trend_res["is_qualified"]

                # Lifecycle evaluation
                new_status = evaluate_event_lifecycle(ev)
                ev.status = new_status

                # Snapshot
                snap = EventSnapshot(
                    event_id=ev.id,
                    timestamp=datetime.now(UTC),
                    document_count=ev.document_count,
                    source_count=ev.source_count,
                    velocity_score=ev.velocity_score,
                    momentum_score=ev.momentum_score,
                    trend_score=ev.trend_score,
                    confidence_score=ev.confidence_score,
                    status=ev.status,
                )
                db.add(snap)
                updated_count += 1

            await db.commit()
            return {"status": "ok", "events_updated": updated_count}

    return _run_async(_async_task())


@celery_app.task(name="discovery.cleanup_old_data", bind=True, queue="maintenance")
def cleanup_old_data_task(self) -> dict:
    """Data retention: removes old raw responses and archives dormant events beyond retention threshold."""

    async def _async_task():
        settings = get_settings()
        retention_days = settings.RAW_CONTENT_RETENTION_DAYS
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)

        session_factory = get_session_factory()
        async with session_factory() as db:
            # 1. Clean raw text in old documents to save database space while preserving normalized metadata
            stmt = select(SourceDocument).where(
                SourceDocument.discovered_at < cutoff,
                SourceDocument.content_text.isnot(None),
            )
            res = await db.execute(stmt)
            docs = list(res.scalars().all())
            cleaned_docs = 0
            for d in docs:
                # Retain summary, truncate full text if older than retention days
                if len(d.content_text) > 1000:
                    d.content_text = d.content_text[:1000]
                    cleaned_docs += 1

            # 2. Transition dormant events older than 30 days to archived
            dormant_cutoff = datetime.now(UTC) - timedelta(days=30)
            dormant_stmt = select(Event).where(
                Event.status == EventStatus.DORMANT,
                Event.last_seen_at < dormant_cutoff,
            )
            dormant_res = await db.execute(dormant_stmt)
            dormant_events = list(dormant_res.scalars().all())
            archived_count = 0
            for ev in dormant_events:
                ev.status = EventStatus.ARCHIVED
                archived_count += 1

            await db.commit()
            return {
                "status": "ok",
                "docs_compressed": cleaned_docs,
                "events_archived": archived_count,
            }

    return _run_async(_async_task())
