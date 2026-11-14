"""
Tests for BaseAgent contract — verifies automatic observability recording.
"""

from typing import Any

import pytest

from app.agents.base import AgentResult, BaseAgent
from app.core.exceptions import AgentExecutionError


class MockAgent(BaseAgent):
    """A concrete test agent that exercises the base contract."""

    name = "mock_agent"
    version = "1.0.0"

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def validate_input(self, input_data: Any) -> bool:
        if input_data is None:
            raise ValueError("Input cannot be None")
        return True

    async def execute(self, input_data: Any, **kwargs: Any) -> AgentResult:
        if self.should_fail:
            raise RuntimeError("Agent execution failed intentionally")
        return AgentResult(
            success=True,
            output={"result": "processed"},
            output_summary="Processed input successfully",
            provider="mock",
            model="mock-model",
            input_tokens=10,
            output_tokens=20,
            estimated_cost=0.001,
        )

    async def validate_output(self, result: AgentResult) -> bool:
        return True


class TestBaseAgent:
    """Base agent contract tests."""

    @pytest.mark.asyncio
    async def test_successful_run_records_agent_run(self, db_session):
        """Successful agent run creates a completed agent_run record."""
        agent = MockAgent()
        result = await agent.run(
            db=db_session,
            input_data="test input",
            task_type="test_task",
        )
        await db_session.flush()

        assert result.success is True
        assert result.output_summary == "Processed input successfully"
        assert result.provider == "mock"
        assert result.estimated_cost == 0.001

    @pytest.mark.asyncio
    async def test_failed_run_records_error(self, db_session):
        """Failed agent run records error details."""
        agent = MockAgent(should_fail=True)

        with pytest.raises(AgentExecutionError):
            await agent.run(
                db=db_session,
                input_data="test input",
                task_type="test_task",
            )

    @pytest.mark.asyncio
    async def test_invalid_input_raises(self, db_session):
        """None input triggers validation error."""
        agent = MockAgent()

        with pytest.raises(AgentExecutionError):
            await agent.run(
                db=db_session,
                input_data=None,
                task_type="test_task",
            )

    def test_agent_result_defaults(self):
        """AgentResult has sensible defaults."""
        result = AgentResult(success=True)
        assert result.input_tokens == 0
        assert result.output_tokens == 0
        assert result.estimated_cost == 0.0
        assert result.metadata == {}
