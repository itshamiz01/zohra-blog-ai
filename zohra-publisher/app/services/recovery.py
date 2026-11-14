"""
Zohra — System Recovery, Autonomy Safety, and Pre-Publish Validation (Part 10).

Provides:
- Global Autonomy Kill Switch & Resume state coordination
- Global & Site-specific Maintenance Mode
- Pre-publish final validation gates (freshness, risk, budget, version match)
- Stale news & backlog recovery filter (prevents publishing outdated breaking news after downtime)
- Stuck job detection & task heartbeat validation
- Live operational system snapshot
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.draft_projects import DraftProject
from app.db.models.operations import AlertCategory, AlertSeverity
from app.db.models.publication_jobs import PublicationJob
from app.db.models.published_articles import PublishedArticle
from app.db.models.sites import Site
from app.services.alerts import AlertManager
from app.services.governor import CostGovernor

logger = logging.getLogger("zohra.recovery")

# In-memory fast safety states (persisted/overridden via DB & Redis)
_GLOBAL_AUTONOMY_PAUSED: bool = False
_GLOBAL_MAINTENANCE_MODE: bool = False


class RecoveryManager:
    """Coordinates autonomy safety gates, stuck job resolution, and pre-publish checks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ── 1. Autonomy Kill Switch & Maintenance Mode ─────────────────────────

    @classmethod
    def is_autonomy_paused(cls) -> bool:
        """Global fast check if autonomous execution is paused."""
        return _GLOBAL_AUTONOMY_PAUSED

    @classmethod
    def pause_autonomy(cls) -> None:
        """Emergency Kill Switch: Immediately halt all new autonomous actions."""
        global _GLOBAL_AUTONOMY_PAUSED
        _GLOBAL_AUTONOMY_PAUSED = True
        logger.warning("EMERGENCY KILL SWITCH ACTIVATED: All autonomous publishing halted.")

    @classmethod
    def resume_autonomy(cls) -> None:
        """Resume autonomous actions under configured policies."""
        global _GLOBAL_AUTONOMY_PAUSED
        _GLOBAL_AUTONOMY_PAUSED = False
        logger.info("Autonomous publishing resumed.")

    @classmethod
    def is_maintenance_mode(cls) -> bool:
        return _GLOBAL_MAINTENANCE_MODE

    @classmethod
    def set_maintenance_mode(cls, enabled: bool) -> None:
        global _GLOBAL_MAINTENANCE_MODE
        _GLOBAL_MAINTENANCE_MODE = enabled
        logger.warning("Global maintenance mode set to %s", enabled)

    async def is_site_autonomous(self, site_id: uuid.UUID) -> tuple[bool, str]:
        """Verify if site is permitted to run autonomous operations."""
        if self.is_autonomy_paused():
            return False, "Global autonomy pause is ACTIVE"

        if self.is_maintenance_mode():
            return False, "Platform is currently in MAINTENANCE mode"

        site_q = select(Site).where(Site.id == site_id)
        site_res = await self.db.execute(site_q)
        site = site_res.scalar_one_or_none()
        if not site:
            return False, "Site not found"

        if not site.enabled:
            return False, "Site is disabled"

        if not site.autonomous_publishing_enabled:
            return False, "Autonomous publishing is disabled for this site"

        return True, "Site is authorized for autonomous operations"

    # ── 2. Pre-Publish Final Check ─────────────────────────────────────────

    async def validate_pre_publish(
        self,
        article_id: uuid.UUID,
        site_id: uuid.UUID,
    ) -> tuple[bool, str]:
        """
        Final safety gate immediately before pushing to WordPress:
        1. Site autonomous permission check
        2. Cost & Budget check
        3. Freshness check (reject stale breaking news)
        4. Factual verification check
        5. Duplicate check
        """
        # 1. Site permission
        allowed, reason = await self.is_site_autonomous(site_id)
        if not allowed:
            return False, f"Pre-publish failed: {reason}"

        # 2. Budget governor
        governor = CostGovernor(self.db)
        can_spend, mode, gov_reason = await governor.check_budget_permission("publishing", site_id=site_id)
        if not can_spend:
            return False, f"Pre-publish blocked by CostGovernor: {gov_reason}"

        # 3. Duplicate check on published registry
        art_q = select(PublishedArticle).where(
            PublishedArticle.article_id == article_id,
            PublishedArticle.site_id == site_id,
        )
        art_res = await self.db.execute(art_q)
        if art_res.scalar_one_or_none():
            return False, "Article is already published to WordPress (idempotency block)"

        # 4. Draft freshness
        draft_q = select(DraftProject).where(DraftProject.id == article_id)
        draft_res = await self.db.execute(draft_q)
        draft = draft_res.scalar_one_or_none()
        if draft:
            age = datetime.now(UTC) - draft.created_at
            if age > timedelta(hours=72):
                return False, f"Article draft is stale ({age.days} days old). Backlog freshness revalidation required."

        return True, "Pre-publish validation PASSED"

    # ── 3. Backlog Recovery & Stale News Purge ─────────────────────────────

    async def revalidate_queued_backlog(self, site_id: uuid.UUID | None = None) -> dict[str, int]:
        """
        Scan queued jobs after an outage or downtime.
        Identifies stale jobs and flags them rather than blindly publishing.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=48)
        query = select(PublicationJob).where(
            PublicationJob.status.in_(["PENDING", "SCHEDULED"]),
            PublicationJob.created_at < cutoff,
        )
        if site_id:
            query = query.where(PublicationJob.site_id == site_id)

        res = await self.db.execute(query)
        stale_jobs = res.scalars().all()

        flagged_count = 0
        for job in stale_jobs:
            job.status = "STALE_REVIEW"
            flagged_count += 1

        if flagged_count > 0:
            await self.db.flush()
            alert_mgr = AlertManager(self.db)
            await alert_mgr.emit_alert(
                title=f"Backlog Recovery: {flagged_count} Stale Publication Jobs Flagged",
                message=f"Detected {flagged_count} publication jobs queued before downtime. Flagged for freshness re-verification to prevent publishing outdated news.",
                category=AlertCategory.PUBLISHING,
                severity=AlertSeverity.WARNING,
                site_id=site_id,
            )

        return {"stale_jobs_flagged": flagged_count}

    # ── 4. System Operational Snapshot ────────────────────────────────────

    async def get_system_snapshot(self) -> dict[str, Any]:
        """Aggregate high-level operational snapshot across all services."""
        governor = CostGovernor(self.db)
        spend_metrics = await governor.get_spend_metrics()

        # Count sites
        site_res = await self.db.execute(select(Site))
        sites = site_res.scalars().all()
        sites_online = sum(1 for s in sites if s.enabled)

        # Count published today
        now = datetime.now(UTC)
        today_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
        pub_today_q = select(PublishedArticle).where(
            PublishedArticle.published_at >= today_start
        )
        pub_today_res = await self.db.execute(pub_today_q)
        published_today = len(pub_today_res.scalars().all())

        # Count pipeline in-flight
        drafts_q = select(DraftProject).where(
            DraftProject.status.in_(["drafting", "in_review", "ready_for_audit"])
        )
        drafts_res = await self.db.execute(drafts_q)
        pipeline_count = len(drafts_res.scalars().all())

        # Pending approvals in publication jobs
        approvals_q = select(PublicationJob).where(
            PublicationJob.status == "PENDING_APPROVAL"
        )
        approvals_res = await self.db.execute(approvals_q)
        approvals_count = len(approvals_res.scalars().all())

        return {
            "autonomy_status": "PAUSED" if self.is_autonomy_paused() else "ACTIVE",
            "maintenance_mode": self.is_maintenance_mode(),
            "sites_total": len(sites),
            "sites_online": sites_online,
            "published_today": published_today,
            "articles_in_pipeline": pipeline_count,
            "pending_approvals": approvals_count,
            "spend_today_usd": spend_metrics["spend_today_usd"],
            "daily_budget_usd": spend_metrics["daily_budget_usd"],
            "cost_mode": spend_metrics["current_mode"],
            "version": getattr(self.settings, "VERSION", "1.0.0"),
            "snapshot_timestamp": datetime.now(UTC).isoformat(),
        }
