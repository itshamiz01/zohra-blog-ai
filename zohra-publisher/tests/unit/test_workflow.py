"""
Tests for workflow state machine, constants, and exceptions.
"""

import pytest

from app.core.constants import VALID_TRANSITIONS, AgentRunStatus, JobStatus, WorkflowState
from app.core.exceptions import (
    AuthenticationError,
    BudgetExceededError,
    DuplicateOperationError,
    FeatureDisabledError,
    WorkflowError,
    ZohraError,
)
from app.services.workflow import WorkflowEngine


class TestWorkflowStateMachine:
    """Workflow transition validation tests."""

    def test_valid_transition_discovered_to_filtered(self):
        """DISCOVERED → FILTERED is legal."""
        assert (
            WorkflowEngine.validate_transition(WorkflowState.DISCOVERED, WorkflowState.FILTERED)
            is True
        )

    def test_valid_transition_filtered_to_researching(self):
        """FILTERED → RESEARCHING is legal."""
        assert (
            WorkflowEngine.validate_transition(WorkflowState.FILTERED, WorkflowState.RESEARCHING)
            is True
        )

    def test_valid_transition_approved_to_published(self):
        """APPROVED → PUBLISHED is legal."""
        assert (
            WorkflowEngine.validate_transition(WorkflowState.APPROVED, WorkflowState.PUBLISHED)
            is True
        )

    def test_invalid_transition_discovered_to_published(self):
        """DISCOVERED → PUBLISHED must be rejected (skips entire pipeline)."""
        with pytest.raises(WorkflowError):
            WorkflowEngine.validate_transition(WorkflowState.DISCOVERED, WorkflowState.PUBLISHED)

    def test_invalid_transition_published_to_discovered(self):
        """PUBLISHED → DISCOVERED must be rejected."""
        with pytest.raises(WorkflowError):
            WorkflowEngine.validate_transition(WorkflowState.PUBLISHED, WorkflowState.DISCOVERED)

    def test_archived_is_terminal(self):
        """ARCHIVED has no valid transitions — it's terminal."""
        allowed = WorkflowEngine.get_allowed_transitions(WorkflowState.ARCHIVED)
        assert allowed == []

    def test_failed_can_retry_from_discovered(self):
        """FAILED → DISCOVERED allows retry from start."""
        assert (
            WorkflowEngine.validate_transition(WorkflowState.FAILED, WorkflowState.DISCOVERED)
            is True
        )

    def test_any_state_can_reach_failed(self):
        """Most active states should be able to transition to FAILED."""
        for state in [
            WorkflowState.DISCOVERED,
            WorkflowState.FILTERED,
            WorkflowState.RESEARCHING,
            WorkflowState.DRAFTED,
        ]:
            assert WorkflowState.FAILED in VALID_TRANSITIONS[state]

    def test_get_allowed_transitions_returns_list(self):
        """get_allowed_transitions returns a list of strings."""
        allowed = WorkflowEngine.get_allowed_transitions(WorkflowState.DISCOVERED)
        assert isinstance(allowed, list)
        assert "filtered" in allowed
        assert "failed" in allowed


class TestExceptions:
    """Exception hierarchy tests."""

    def test_zohra_error_has_code(self):
        err = ZohraError("test", code="TEST")
        assert err.code == "TEST"
        assert err.message == "test"

    def test_workflow_error_inherits(self):
        err = WorkflowError("bad transition")
        assert isinstance(err, ZohraError)
        assert err.code == "WORKFLOW_ERROR"

    def test_budget_error(self):
        err = BudgetExceededError()
        assert err.code == "BUDGET_EXCEEDED"

    def test_duplicate_operation_error(self):
        err = DuplicateOperationError()
        assert err.code == "DUPLICATE_OPERATION"

    def test_feature_disabled_error(self):
        err = FeatureDisabledError("discovery")
        assert "discovery" in err.message
        assert err.feature == "discovery"

    def test_authentication_error(self):
        err = AuthenticationError()
        assert err.code == "AUTHENTICATION_ERROR"


class TestEnums:
    """Enum completeness tests."""

    def test_job_statuses(self):
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.DEAD_LETTER.value == "dead_letter"
        assert len(JobStatus) == 7

    def test_agent_run_statuses(self):
        assert AgentRunStatus.QUEUED.value == "queued"
        assert len(AgentRunStatus) == 6

    def test_all_workflow_states_have_transitions(self):
        """Every WorkflowState must appear in VALID_TRANSITIONS."""
        for state in WorkflowState:
            assert state in VALID_TRANSITIONS
