"""
Zohra Part 3 — Celery tasks for Content Opportunity Scoring & Intelligence Engine.

Queues:
- opportunity: event processing, opportunity evaluation, scoring
- seo_analysis: SERP retrieval, keyword clustering, content gap analysis
- maintenance: watchlist re-evaluation, retention cleanup
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from celery.utils.log import get_task_logger
from sqlalchemy import delete, select

from app.db.models.content_opportunities import ContentOpportunity
from app.db.models.opportunity_snapshots import OpportunityWatchlist
from app.db.models.serp import SERPSnapshot
from app.db.session import get_session_factory
from app.discovery.handoff import build_event_handoff
from app.opportunity.pipeline import OpportunityPipeline
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


@celery_app.task(name="opportunity.process_event", bind=True, max_retries=3, queue="opportunity")
def process_event_task(self, event_id: str, site_id: str | None = None) -> dict:
    """Processes a qualified discovered event through the Content Opportunity Pipeline."""

    async def _process():
        session_factory = get_session_factory()
        async with session_factory() as session:
            ev_uuid = UUID(event_id)
            site_uuid = UUID(site_id) if site_id else None

            handoff = await build_event_handoff(session, ev_uuid)
            if not handoff:
                logger.warning("event_handoff_not_found_or_not_qualified", event_id=event_id)
                return {"status": "skipped", "reason": "event_not_found"}

            pipeline = OpportunityPipeline()
            packages = await pipeline.process_event(
                session=session,
                event_handoff=handoff,
                site_id=site_uuid,
            )

            return {
                "status": "completed",
                "event_id": event_id,
                "opportunities_count": len(packages),
                "packages": [p.model_dump() for p in packages],
            }

    try:
        return _run_async(_process())
    except Exception as exc:
        logger.error("opportunity_process_event_failed", event_id=event_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(name="opportunity.reevaluate_watchlist", queue="maintenance")
def reevaluate_watchlist_task() -> dict:
    """Periodically checks watchlist entries and re-evaluates active opportunities."""

    async def _reevaluate():
        session_factory = get_session_factory()
        now = datetime.now(UTC)
        async with session_factory() as session:
            stmt = (
                select(OpportunityWatchlist)
                .where(
                    OpportunityWatchlist.is_active.is_(True),
                    OpportunityWatchlist.recheck_after <= now,
                )
                .limit(20)
            )
            res = await session.execute(stmt)
            entries = list(res.scalars().all())

            reevaluated = 0
            for entry in entries:
                opp = await session.get(ContentOpportunity, entry.opportunity_id)
                if not opp:
                    entry.is_active = False
                    continue

                # Increment check count and update last_checked_at
                entry.recheck_count += 1
                entry.last_checked_at = now

                # If checked more than 4 times without qualifying, archive
                if entry.recheck_count >= 4:
                    entry.is_active = False
                    opp.status = "expired"

                reevaluated += 1

            await session.commit()
            return {"reevaluated_count": reevaluated}

    return _run_async(_reevaluate())


@celery_app.task(name="serp.cleanup_expired_snapshots", queue="maintenance")
def cleanup_expired_snapshots_task() -> dict:
    """Removes expired SERP snapshots based on retention policies."""

    async def _cleanup():
        session_factory = get_session_factory()
        now = datetime.now(UTC)
        async with session_factory() as session:
            stmt = delete(SERPSnapshot).where(SERPSnapshot.expires_at <= now)
            res = await session.execute(stmt)
            await session.commit()
            return {"deleted_snapshots": res.rowcount}

    return _run_async(_cleanup())
