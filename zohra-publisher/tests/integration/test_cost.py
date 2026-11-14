"""
Tests for CostService — budget enforcement and spend tracking.
"""

import pytest

from app.core.exceptions import BudgetExceededError
from app.db.models.model_usage import ModelUsage
from app.services.cost import CostService


class TestCostService:
    """Cost tracking and budget enforcement tests."""

    @pytest.mark.asyncio
    async def test_empty_spend(self, db_session):
        """No usage records → zero spend."""
        daily = await CostService.get_daily_spend(db_session)
        assert daily == 0.0

        monthly = await CostService.get_monthly_spend(db_session)
        assert monthly == 0.0

    @pytest.mark.asyncio
    async def test_record_and_query_usage(self, db_session):
        """Recording usage updates spend calculations."""
        await CostService.record_usage(
            db=db_session,
            provider="openai",
            model="gpt-4",
            input_tokens=100,
            output_tokens=200,
            estimated_input_cost=0.01,
            estimated_output_cost=0.02,
            operation="test",
        )
        await db_session.flush()

        daily = await CostService.get_daily_spend(db_session)
        assert daily == pytest.approx(0.03)

    @pytest.mark.asyncio
    async def test_budget_check_passes_when_under(self, db_session):
        """Budget check passes when spend is under limit."""
        result = await CostService.check_budget(db_session)
        assert result is True

    @pytest.mark.asyncio
    async def test_budget_check_fails_when_daily_exceeded(self, db_session):
        """Budget check raises BudgetExceededError when daily limit hit."""
        # Record $101 of usage (exceeds the $100 test budget)
        usage = ModelUsage(
            provider="openai",
            model="gpt-4",
            input_tokens=10000,
            output_tokens=20000,
            total_tokens=30000,
            estimated_input_cost=50.0,
            estimated_output_cost=51.0,
            estimated_total_cost=101.0,
        )
        db_session.add(usage)
        await db_session.flush()

        with pytest.raises(BudgetExceededError):
            await CostService.check_budget(db_session)

    @pytest.mark.asyncio
    async def test_critical_operations_bypass_budget(self, db_session):
        """Critical operations bypass budget limits."""
        usage = ModelUsage(
            provider="openai",
            model="gpt-4",
            input_tokens=10000,
            output_tokens=20000,
            total_tokens=30000,
            estimated_input_cost=50.0,
            estimated_output_cost=51.0,
            estimated_total_cost=101.0,
        )
        db_session.add(usage)
        await db_session.flush()

        # Critical operations bypass the check
        result = await CostService.check_budget(db_session, is_critical=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_cost_summary(self, db_session):
        """Cost summary returns complete structure."""
        summary = await CostService.get_cost_summary(db_session)
        assert summary.daily_total == 0.0
        assert summary.daily_budget == 100.0
        assert summary.monthly_budget == 1000.0
        assert summary.currency == "USD"
        assert isinstance(summary.by_provider, dict)

    @pytest.mark.asyncio
    async def test_spend_by_provider(self, db_session):
        """Spend breakdown by provider works."""
        for provider, cost in [("openai", 0.05), ("anthropic", 0.03)]:
            usage = ModelUsage(
                provider=provider,
                model="test",
                input_tokens=10,
                output_tokens=20,
                total_tokens=30,
                estimated_input_cost=cost / 2,
                estimated_output_cost=cost / 2,
                estimated_total_cost=cost,
            )
            db_session.add(usage)
        await db_session.flush()

        by_provider = await CostService.get_spend_by_provider(db_session)
        assert "openai" in by_provider
        assert "anthropic" in by_provider
