"""
Zohra — Cost tracking and budget enforcement service.

Calculates daily/monthly AI spend from model_usage records.
Blocks non-critical AI operations when budget thresholds are exceeded.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BudgetExceededError
from app.core.logging import get_logger
from app.db.models.model_usage import ModelUsage
from app.schemas.api import CostSummary

logger = get_logger(__name__, component="cost")


class CostService:
    """Budget tracking and enforcement."""

    @staticmethod
    async def get_daily_spend(db: AsyncSession) -> float:
        """Total AI cost for today (UTC)."""
        today_start = datetime.now(UTC).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        result = await db.execute(
            select(func.coalesce(func.sum(ModelUsage.estimated_total_cost), 0.0)).where(
                ModelUsage.created_at >= today_start,
            )
        )
        return float(result.scalar_one())

    @staticmethod
    async def get_monthly_spend(db: AsyncSession) -> float:
        """Total AI cost for this calendar month (UTC)."""
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.coalesce(func.sum(ModelUsage.estimated_total_cost), 0.0)).where(
                ModelUsage.created_at >= month_start,
            )
        )
        return float(result.scalar_one())

    @staticmethod
    async def get_spend_by_provider(db: AsyncSession, days: int = 30) -> dict[str, float]:
        """Cost breakdown by provider for the last N days."""
        since = datetime.now(UTC) - timedelta(days=days)
        result = await db.execute(
            select(
                ModelUsage.provider,
                func.coalesce(func.sum(ModelUsage.estimated_total_cost), 0.0),
            )
            .where(ModelUsage.created_at >= since)
            .group_by(ModelUsage.provider)
        )
        return {row[0]: float(row[1]) for row in result.all()}

    @staticmethod
    async def get_spend_by_model(db: AsyncSession, days: int = 30) -> dict[str, float]:
        """Cost breakdown by model for the last N days."""
        since = datetime.now(UTC) - timedelta(days=days)
        result = await db.execute(
            select(
                ModelUsage.model,
                func.coalesce(func.sum(ModelUsage.estimated_total_cost), 0.0),
            )
            .where(ModelUsage.created_at >= since)
            .group_by(ModelUsage.model)
        )
        return {row[0]: float(row[1]) for row in result.all()}

    @staticmethod
    async def get_cost_summary(db: AsyncSession) -> CostSummary:
        """Full cost summary for dashboard / status API."""
        settings = get_settings()
        daily = await CostService.get_daily_spend(db)
        monthly = await CostService.get_monthly_spend(db)
        by_provider = await CostService.get_spend_by_provider(db)
        by_model = await CostService.get_spend_by_model(db)

        return CostSummary(
            daily_total=daily,
            monthly_total=monthly,
            daily_budget=settings.LLM_DAILY_BUDGET,
            monthly_budget=settings.LLM_MONTHLY_BUDGET,
            daily_remaining=max(0, settings.LLM_DAILY_BUDGET - daily),
            monthly_remaining=max(0, settings.LLM_MONTHLY_BUDGET - monthly),
            currency="USD",
            by_provider=by_provider,
            by_model=by_model,
        )

    @staticmethod
    async def check_budget(db: AsyncSession, is_critical: bool = False) -> bool:
        """
        Check if AI operations should proceed.
        Critical operations (e.g. fact-checking) bypass budget limits.
        Non-critical operations are blocked when budget is exceeded.
        Raises BudgetExceededError if blocked.
        """
        if is_critical:
            return True

        settings = get_settings()
        daily = await CostService.get_daily_spend(db)
        monthly = await CostService.get_monthly_spend(db)

        if daily >= settings.LLM_DAILY_BUDGET:
            logger.warning(
                "Daily AI budget exceeded: $%.2f / $%.2f",
                daily,
                settings.LLM_DAILY_BUDGET,
            )
            raise BudgetExceededError(
                f"Daily AI budget exceeded: ${daily:.2f} / ${settings.LLM_DAILY_BUDGET:.2f}"
            )

        if monthly >= settings.LLM_MONTHLY_BUDGET:
            logger.warning(
                "Monthly AI budget exceeded: $%.2f / $%.2f",
                monthly,
                settings.LLM_MONTHLY_BUDGET,
            )
            raise BudgetExceededError(
                f"Monthly AI budget exceeded: ${monthly:.2f} / ${settings.LLM_MONTHLY_BUDGET:.2f}"
            )

        return True

    @staticmethod
    async def record_usage(
        db: AsyncSession,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        estimated_input_cost: float,
        estimated_output_cost: float,
        agent_run_id: str | None = None,
        operation: str | None = None,
    ) -> ModelUsage:
        """Record a single LLM usage event."""
        import uuid as _uuid

        usage = ModelUsage(
            agent_run_id=_uuid.UUID(agent_run_id) if agent_run_id else None,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_input_cost=estimated_input_cost,
            estimated_output_cost=estimated_output_cost,
            estimated_total_cost=estimated_input_cost + estimated_output_cost,
            operation=operation,
        )
        db.add(usage)
        return usage
