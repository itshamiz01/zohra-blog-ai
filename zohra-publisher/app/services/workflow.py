"""
Zohra — Workflow state machine engine.

Validates state transitions against the VALID_TRANSITIONS map.
Records every transition as an audit event.
Rejects illegal jumps (e.g. DISCOVERED → PUBLISHED).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import VALID_TRANSITIONS, ActorType, WorkflowState
from app.core.exceptions import WorkflowError
from app.core.logging import get_logger
from app.db.models.audit_logs import AuditLog

logger = get_logger(__name__, component="workflow")


class WorkflowEngine:
    """
    Stateless service that validates and records content-workflow transitions.
    Business modules call this when moving content through the pipeline.
    """

    @staticmethod
    def validate_transition(current: WorkflowState, target: WorkflowState) -> bool:
        """Check whether a transition is legal. Returns True or raises WorkflowError."""
        allowed = VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise WorkflowError(
                f"Invalid transition: {current.value} → {target.value}. "
                f"Allowed targets: {', '.join(s.value for s in allowed) or 'none (terminal state)'}"
            )
        return True

    @staticmethod
    async def transition(
        db: AsyncSession,
        entity_type: str,
        entity_id: uuid.UUID,
        current_state: WorkflowState,
        target_state: WorkflowState,
        actor_type: ActorType = ActorType.SYSTEM,
        actor_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """
        Validate a transition and record it as an audit event.
        Raises WorkflowError if the transition is illegal.
        """
        WorkflowEngine.validate_transition(current_state, target_state)

        audit = AuditLog(
            actor_type=actor_type.value,
            actor_id=actor_id,
            action="workflow_transition",
            entity_type=entity_type,
            entity_id=entity_id,
            previous_state=current_state.value,
            new_state=target_state.value,
            metadata_json=metadata,
        )
        db.add(audit)

        logger.info(
            "Workflow transition: %s → %s for %s/%s",
            current_state.value,
            target_state.value,
            entity_type,
            entity_id,
        )

        return audit

    @staticmethod
    def get_allowed_transitions(state: WorkflowState) -> list[str]:
        """Return the list of states reachable from the given state."""
        return [s.value for s in VALID_TRANSITIONS.get(state, set())]
