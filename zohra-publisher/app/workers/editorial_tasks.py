"""
Zohra — Editorial Celery Tasks (Part 5).

Asynchronous workers for autonomous editorial drafting, blueprinting,
section rendering, quality review, and editorial package assembly.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.editorial.pipeline import EditorialPipeline
from app.utils.redis import distributed_lock
from app.workers.celery_app import celery_app

logger = get_logger("workers.editorial")


@celery_app.task(name="editorial.start_draft", bind=True, max_retries=2, default_retry_delay=30)
def task_start_editorial_draft(
    self,
    draft_project_id: str,
    brand_voice_id: str | None = None,
    existing_site_content: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Celery task to run the autonomous editorial drafting pipeline."""
    lock_resource = f"draft:project:{draft_project_id}"

    with distributed_lock(lock_resource, ttl_seconds=600):
        async def _run():
            async with async_session_factory() as session:
                proj_uuid = uuid.UUID(draft_project_id)
                bv_uuid = uuid.UUID(brand_voice_id) if brand_voice_id else None

                pipeline = EditorialPipeline(session)
                pkg = await pipeline.execute_draft_project(
                    draft_project_id=proj_uuid,
                    brand_voice_id=bv_uuid,
                    existing_site_content=existing_site_content,
                )
                if pkg:
                    return pkg.dict()
                return None

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
