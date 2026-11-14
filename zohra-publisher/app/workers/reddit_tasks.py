"""
Zohra — Celery Background Tasks for Reddit Opportunity & Referral Engine.

Handles asynchronous scheduled discovery cycles, question clustering,
opportunity evaluation, research engine handoff, and publication health checks.
"""

from __future__ import annotations

import asyncio
from typing import Any
import uuid

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db_context
from app.reddit.service import RedditEngineService
from app.workers.celery_app import celery_app

logger = get_logger("workers.reddit")


def _run_async(coro):
    """Executes an async coroutine synchronously within Celery worker process."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="reddit.scheduled_discovery_cycle", bind=True, max_retries=2)
def scheduled_reddit_discovery(self, site_id_str: str) -> dict[str, Any]:
    """Runs a periodic Reddit discovery scan for a site's monitored subreddits."""
    settings = get_settings()
    if not getattr(settings, "REDDIT_ENABLED", False) and not getattr(settings, "REDDIT_DISCOVERY_ENABLED", True):
        logger.info("Reddit discovery is disabled in configuration.")
        return {"status": "skipped", "reason": "discovery_disabled"}

    site_id = uuid.UUID(site_id_str)

    async def _execute():
        async with get_db_context() as db:
            service = RedditEngineService(db)
            discovered = await service.run_discovery_cycle(site_id=site_id)
            scored = await service.cluster_and_score_pending_questions(site_id=site_id)
            return {
                "status": "completed",
                "site_id": str(site_id),
                "questions_discovered": len(discovered),
                "opportunities_scored": len(scored),
            }

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.error("Reddit discovery task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="reddit.cluster_and_score_pending", bind=True, max_retries=2)
def cluster_and_score_pending(self, site_id_str: str) -> dict[str, Any]:
    """Clusters discovered questions and resolves them into content opportunities."""
    site_id = uuid.UUID(site_id_str)

    async def _execute():
        async with get_db_context() as db:
            service = RedditEngineService(db)
            scored = await service.cluster_and_score_pending_questions(site_id=site_id)
            return {
                "status": "completed",
                "site_id": str(site_id),
                "opportunities_scored": len(scored),
            }

    try:
        return _run_async(_execute())
    except Exception as exc:
        logger.error("Reddit clustering task failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc, countdown=60)
