"""
Zohra — Base agent contract.

Every future agent (Scout, Researcher, Writer, Verifier, Editor, SEO)
inherits from BaseAgent and gets automatic:
  - agent_runs recording
  - structured logging
  - timing
  - retry metadata
  - token/cost tracking
  - error handling

Part 1 defines the interface only. No concrete agents are implemented yet.
"""

from __future__ import annotations

import abc
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AgentRunStatus
from app.core.exceptions import AgentExecutionError
from app.core.logging import get_logger
from app.db.models.agent_runs import AgentRun

logger = get_logger(__name__, component="agent")


class AgentResult:
    """Normalized result from any agent execution."""

    def __init__(
        self,
        success: bool,
        output: Any = None,
        output_summary: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ):
        self.success = success
        self.output = output
        self.output_summary = output_summary
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.estimated_cost = estimated_cost
        self.metadata = metadata or {}


class BaseAgent(abc.ABC):
    """
    Abstract base for all Zohra AI agents.

    Subclasses must implement:
      - validate_input()
      - execute()
      - validate_output()

    The run() method orchestrates the full lifecycle with
    observability and error handling.
    """

    name: str = "base_agent"
    version: str = "0.1.0"

    @abc.abstractmethod
    async def validate_input(self, input_data: Any) -> bool:
        """Validate input before execution. Raise ValidationError if invalid."""
        ...

    @abc.abstractmethod
    async def execute(self, input_data: Any, **kwargs: Any) -> AgentResult:
        """Execute the agent's core logic. Return AgentResult."""
        ...

    @abc.abstractmethod
    async def validate_output(self, result: AgentResult) -> bool:
        """Validate output after execution. Raise ValidationError if invalid."""
        ...

    async def run(
        self,
        db: AsyncSession,
        input_data: Any,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> AgentResult:
        """
        Full agent lifecycle:
          1. Create agent_run record (status=running)
          2. Validate input
          3. Execute
          4. Validate output
          5. Update agent_run (status=completed/failed, timing, tokens, cost)
        """
        run_record = AgentRun(
            agent_name=self.name,
            agent_version=self.version,
            task_type=kwargs.get("task_type", "default"),
            entity_type=entity_type,
            entity_id=entity_id,
            status=AgentRunStatus.RUNNING.value,
            started_at=datetime.now(UTC),
            input_summary=str(input_data)[:500] if input_data else None,
        )
        db.add(run_record)
        await db.flush()

        logger.info(
            "Agent %s v%s starting run %s",
            self.name,
            self.version,
            run_record.id,
            extra={"agent_run_id": str(run_record.id)},
        )

        try:
            # Step 1: Validate input
            await self.validate_input(input_data)

            # Step 2: Execute
            result = await self.execute(input_data, **kwargs)

            # Step 3: Validate output
            await self.validate_output(result)

            # Step 4: Record success
            completed_at = datetime.now(UTC)
            run_record.status = AgentRunStatus.COMPLETED.value
            run_record.completed_at = completed_at
            run_record.duration_ms = int(
                (completed_at - run_record.started_at).total_seconds() * 1000
            )
            run_record.output_summary = result.output_summary
            run_record.provider = result.provider
            run_record.model = result.model
            run_record.input_tokens = result.input_tokens
            run_record.output_tokens = result.output_tokens
            run_record.estimated_cost = result.estimated_cost

            logger.info(
                "Agent %s completed run %s in %dms",
                self.name,
                run_record.id,
                run_record.duration_ms,
                extra={"agent_run_id": str(run_record.id)},
            )

            return result

        except Exception as exc:
            completed_at = datetime.now(UTC)
            run_record.status = AgentRunStatus.FAILED.value
            run_record.completed_at = completed_at
            run_record.duration_ms = int(
                (completed_at - run_record.started_at).total_seconds() * 1000
            )
            run_record.error_code = type(exc).__name__
            run_record.error_message = str(exc)[:1000]

            logger.error(
                "Agent %s failed run %s: %s",
                self.name,
                run_record.id,
                exc,
                extra={"agent_run_id": str(run_record.id)},
                exc_info=True,
            )

            raise AgentExecutionError(f"Agent '{self.name}' failed: {exc}") from exc
