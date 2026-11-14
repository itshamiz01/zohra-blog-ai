"""
Zohra — Research Celery Tasks.

Asynchronous tasks for autonomous deep research execution, question planning,
evidence acquisition, and handoff package generation.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.content_opportunities import ContentOpportunity
from app.db.session import async_session_factory
from app.opportunity.handoff import build_opportunity_package
from app.research.pipeline import ResearchPipeline
from app.schemas.research import ResearchDepth
from app.utils.redis import distributed_lock
from app.workers.celery_app import celery_app

logger = get_logger("workers.research")


@celery_app.task(name="research.start_project", bind=True, max_retries=2, default_retry_delay=30)
def task_start_research_project(
    self,
    opportunity_id: str,
    research_depth: str = "STANDARD",
    mock_sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Celery task to run autonomous deep research for a given opportunity."""
    lock_resource = f"research:opp:{opportunity_id}"

    with distributed_lock(lock_resource, ttl_seconds=600):
        async def _run():
            async with async_session_factory() as session:
                opp_uuid = uuid.UUID(opportunity_id)
                stmt = select(ContentOpportunity).where(ContentOpportunity.id == opp_uuid)
                res = await session.execute(stmt)
                opp = res.scalars().first()

                if not opp:
                    raise ValueError(f"ContentOpportunity {opportunity_id} not found")

                package = build_opportunity_package(opp)
                depth_enum = ResearchDepth(research_depth.upper())

                pipeline = ResearchPipeline(session)
                final_pkg = await pipeline.run_research(
                    package=package,
                    research_depth=depth_enum,
                    mock_source_data=mock_sources,
                )
                return final_pkg.model_dump(mode="json")

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
