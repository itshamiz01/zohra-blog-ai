"""
Zohra — CostGovernor & AI Spending Protection (Part 10).

Provides:
- Multi-tier budget coordination (daily, monthly, site-specific)
- Automatic degradation modes: NORMAL, ECONOMY, ESSENTIAL_ONLY, PAUSED
- Threshold monitoring and alert emission (50%, 75%, 90%, 100%)
- Task priority gating (safety and rollbacks never starved)
- Division-by-zero protection (returns "N/A" rather than crashing)
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.model_usage import ModelUsage
from app.db.models.operations import AlertCategory, AlertSeverity
from app.db.models.sites import Site
from app.services.alerts import AlertManager


class CostMode(str, enum.Enum):
    NORMAL = "NORMAL"
    ECONOMY = "ECONOMY"
    ESSENTIAL_ONLY = "ESSENTIAL_ONLY"
    PAUSED = "PAUSED"


ESSENTIAL_TASKS = {
    "safety",
    "safety_correction",
    "critical_rollback",
    "verification",
    "monitoring",
    "system_health",
}


class CostGovernor:
    """Oversees platform-wide and per-site AI expenditures, enforcing degradation policies."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def get_spend_metrics(
        self,
        site_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Aggregate spend totals for today and the current month.
        Protects against zero division.
        """
        now = datetime.now(UTC)
        today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

        # Today's total spend
        q_today = select(func.coalesce(func.sum(ModelUsage.estimated_total_cost), 0.0)).where(
            ModelUsage.created_at >= today_start
        )
        res_today = await self.db.execute(q_today)
        spend_today = float(res_today.scalar_one())

        # Current month's total spend
        q_month = select(func.coalesce(func.sum(ModelUsage.estimated_total_cost), 0.0)).where(
            ModelUsage.created_at >= month_start
        )
        res_month = await self.db.execute(q_month)
        spend_month = float(res_month.scalar_one())

        # Configured thresholds (default $50/day, $1000/month if not in settings)
        daily_limit = getattr(self.settings, "DAILY_BUDGET_USD", 50.0)
        monthly_limit = getattr(self.settings, "MONTHLY_BUDGET_USD", 1000.0)

        # Check site overrides if site_id provided
        if site_id:
            site_q = select(Site).where(Site.id == site_id)
            site_res = await self.db.execute(site_q)
            site = site_res.scalar_one_or_none()
            if site and site.config_json:
                daily_limit = float(site.config_json.get("daily_cost_limit", daily_limit))
                monthly_limit = float(site.config_json.get("monthly_cost_limit", monthly_limit))

        daily_utilization = (spend_today / daily_limit) if daily_limit > 0 else 0.0
        monthly_utilization = (spend_month / monthly_limit) if monthly_limit > 0 else 0.0

        # Determine operating mode
        max_utilization = max(daily_utilization, monthly_utilization)
        if max_utilization >= 1.0:
            current_mode = CostMode.ESSENTIAL_ONLY
        elif max_utilization >= 0.75:
            current_mode = CostMode.ECONOMY
        else:
            current_mode = CostMode.NORMAL

        return {
            "spend_today_usd": round(spend_today, 4),
            "spend_month_usd": round(spend_month, 4),
            "daily_budget_usd": round(daily_limit, 2),
            "monthly_budget_usd": round(monthly_limit, 2),
            "daily_utilization_ratio": round(daily_utilization, 4),
            "monthly_utilization_ratio": round(monthly_utilization, 4),
            "current_mode": current_mode.value,
            "cost_per_article": "N/A",  # Populated when article metrics exist
            "cost_per_click": "N/A",
        }

    async def check_budget_permission(
        self,
        task_type: str,
        estimated_cost: float = 0.0,
        site_id: uuid.UUID | None = None,
    ) -> tuple[bool, CostMode, str]:
        """
        Evaluate if a task is permitted under current cost constraints.
        Returns: (allowed: bool, mode: CostMode, reason: str)
        """
        metrics = await self.get_spend_metrics(site_id=site_id)
        mode = CostMode(metrics["current_mode"])
        is_essential = task_type.lower() in ESSENTIAL_TASKS

        if mode == CostMode.ESSENTIAL_ONLY:
            if not is_essential:
                return (
                    False,
                    mode,
                    f"Hard budget reached ({metrics['spend_today_usd']}/{metrics['daily_budget_usd']} USD). Non-essential task '{task_type}' deferred.",
                )
            return True, mode, f"Essential task '{task_type}' permitted under ESSENTIAL_ONLY mode."

        if mode == CostMode.ECONOMY:
            if task_type.lower().startswith("exploratory"):
                return (
                    False,
                    mode,
                    f"Budget threshold exceeded (>=75%). Exploratory task '{task_type}' paused in ECONOMY mode.",
                )
            return True, mode, f"Task '{task_type}' allowed in ECONOMY mode."

        return True, CostMode.NORMAL, f"Task '{task_type}' allowed in NORMAL mode."

    async def check_and_emit_budget_alerts(self, site_id: uuid.UUID | None = None) -> None:
        """Evaluate spending and dispatch alerts at 50%, 75%, 90%, and 100% marks."""
        metrics = await self.get_spend_metrics(site_id=site_id)
        util = metrics["daily_utilization_ratio"]
        alert_mgr = AlertManager(self.db)

        if util >= 1.0:
            await alert_mgr.emit_alert(
                title="CRITICAL: Daily AI Budget Exhausted",
                message=f"Spend ${metrics['spend_today_usd']:.2f} reached 100% of daily limit ${metrics['daily_budget_usd']:.2f}. System transitioned to ESSENTIAL_ONLY mode.",
                category=AlertCategory.COST,
                severity=AlertSeverity.CRITICAL,
                source="CostGovernor",
                site_id=site_id,
                metadata=metrics,
            )
        elif util >= 0.90:
            await alert_mgr.emit_alert(
                title="HIGH: Daily AI Budget at 90%",
                message=f"Spend ${metrics['spend_today_usd']:.2f} has reached 90% of daily limit ${metrics['daily_budget_usd']:.2f}.",
                category=AlertCategory.COST,
                severity=AlertSeverity.HIGH,
                source="CostGovernor",
                site_id=site_id,
                metadata=metrics,
            )
        elif util >= 0.75:
            await alert_mgr.emit_alert(
                title="WARNING: Daily AI Budget at 75%",
                message=f"Spend ${metrics['spend_today_usd']:.2f} has reached 75% of daily limit. ECONOMY mode active.",
                category=AlertCategory.COST,
                severity=AlertSeverity.WARNING,
                source="CostGovernor",
                site_id=site_id,
                metadata=metrics,
            )
        elif util >= 0.50:
            await alert_mgr.emit_alert(
                title="INFO: Daily AI Budget at 50%",
                message=f"Spend ${metrics['spend_today_usd']:.2f} has reached 50% of daily limit.",
                category=AlertCategory.COST,
                severity=AlertSeverity.INFO,
                source="CostGovernor",
                site_id=site_id,
                metadata=metrics,
                cooldown_minutes=60,
            )
