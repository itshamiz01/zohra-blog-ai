"""
Zohra — Celery Background Tasks for Part 7 Publishing Engine.

Defines asynchronous workers for:
- publication.start_job: Executes validation, media preparation, link resolution, and rendering.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.draft_projects import DraftProject
from app.db.models.final_audit_packages import FinalAuditPackage
from app.db.models.publication_jobs import PublicationEvent, PublicationJob
from app.db.models.sites import Site
from app.db.session import async_session_factory
from app.publishing.pipeline import PublishingPipeline
from app.schemas.publishing import PublicationMode
from app.utils.redis import distributed_lock
from app.workers.celery_app import celery_app

logger = get_logger("workers.publishing_tasks")


@celery_app.task(
    name="publication.start_job",
    bind=True,
    max_retries=2,
    default_retry_delay=15,
)
def start_publication_job(self: Any, job_id_str: str) -> dict[str, Any]:
    """Celery background worker entrypoint for starting a publication job."""
    return asyncio.run(_async_start_publication_job(job_id_str))


async def _async_start_publication_job(job_id_str: str) -> dict[str, Any]:
    job_id = uuid.UUID(job_id_str)

    async with (
        distributed_lock(f"publish:job:{job_id_str}", expire_seconds=300),
        async_session_factory() as session,
    ):
        job = await session.get(PublicationJob, job_id)
        if not job:
            logger.error("Publication job not found", job_id=job_id_str)
            return {"error": "Job not found"}

        site = await session.get(Site, job.site_id)
        if not site:
            job.status = "FAILED"
            job.last_error = "Target site profile not found"
            await session.commit()
            return {"error": "Site not found"}

        # Fetch FinalAuditPackage
        res = await session.execute(
            select(FinalAuditPackage).where(FinalAuditPackage.audit_project_id == job.audit_id)
        )
        fap = res.scalar_one_or_none()
        if not fap:
            job.status = "FAILED"
            job.last_error = "Audit package missing"
            await session.commit()
            return {"error": "Audit package missing"}

        # Fetch DraftProject
        draft_proj = await session.get(DraftProject, fap.draft_project_id)
        if not draft_proj:
            job.status = "FAILED"
            job.last_error = "Draft project missing"
            await session.commit()
            return {"error": "Draft project missing"}

        # Transition state to VALIDATING
        job.status = "VALIDATING"
        job.started_at = datetime.now(UTC)
        session.add(
            PublicationEvent(
                publication_job_id=job.id,
                event_type="VALIDATION_STARTED",
                previous_state="CREATED",
                new_state="VALIDATING",
            )
        )
        await session.commit()

        try:
            # Prepare payload (Media, Links, SEO, HTML Rendering)
            draft_data = {
                "id": draft_proj.id,
                "version_id": job.draft_version_id,
                "title": draft_proj.title,
                "full_text": draft_proj.final_text or draft_proj.outline_json.get("text", ""),
                "sections": draft_proj.outline_json.get("sections", []),
                "faqs": draft_proj.outline_json.get("faqs", []),
                "tables": draft_proj.outline_json.get("tables", []),
                "meta_description": draft_proj.meta_description,
                "primary_keyword": draft_proj.primary_keyword,
                "primary_topic": draft_proj.primary_topic,
            }
            site_data = {
                "id": site.id,
                "domain": site.domain,
                "niche": site.niche,
                "wordpress_base_url": site.wordpress_base_url,
                "wordpress_api_url": site.wordpress_api_url,
                "credential_ref": site.credential_ref,
                "max_posts_per_day": site.max_posts_per_day,
                "minimum_publish_interval_minutes": site.minimum_publish_interval_minutes,
                "publishing_enabled": site.publishing_enabled,
                "autonomous_publishing_enabled": site.autonomous_publishing_enabled,
                "default_category_id": site.default_category_id,
                "default_author_id": site.default_author_id,
            }
            fap_data = {
                "audit_id": fap.audit_project_id,
                "decision": fap.decision,
                "eligible_for_part7": fap.eligible_for_part7,
                "content_hash": fap.content_hash,
                "audit_token": fap.audit_token,
                "audit_fingerprint": fap.audit_fingerprint,
            }

            mode = PublicationMode[job.publication_mode] if job.publication_mode in PublicationMode.__members__ else PublicationMode.DRAFT
            prepared = await PublishingPipeline.prepare_publication_payload(
                final_audit_package_data=fap_data,
                draft_project_data=draft_data,
                site_data=site_data,
                publication_mode=mode,
                scheduled_for=job.scheduled_for,
            )

            job.payload_hash = prepared["payload_hash"]
            job.rendered_html = prepared["rendered_html"]
            job.preview_json = {
                "title": prepared["title"],
                "slug": prepared["slug"],
                "canonical_url": prepared["seo_package"].canonical_url,
                "schema_types": prepared["schema_package"].get("@graph", []),
            }

            # If DRAFT mode, create WordPress draft immediately or await approval
            if mode == PublicationMode.DRAFT:
                job.status = "PREVIEW_READY"
            else:
                job.status = "APPROVED_FOR_PUBLICATION"

            session.add(
                PublicationEvent(
                    publication_job_id=job.id,
                    event_type="PAYLOAD_PREPARED",
                    previous_state="VALIDATING",
                    new_state=job.status,
                    payload_hash=job.payload_hash,
                )
            )
            await session.commit()
            return {"job_id": job_id_str, "status": job.status, "payload_hash": job.payload_hash}

        except Exception as exc:
            logger.error("Publication job preparation failed", error=str(exc))
            job.status = "FAILED"
            job.last_error = str(exc)
            session.add(
                PublicationEvent(
                    publication_job_id=job.id,
                    event_type="JOB_FAILED",
                    previous_state="VALIDATING",
                    new_state="FAILED",
                    metadata_json={"error": str(exc)},
                )
            )
            await session.commit()
            return {"job_id": job_id_str, "status": "FAILED", "error": str(exc)}
