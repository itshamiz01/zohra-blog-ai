"""
Zohra — Part 9 Pydantic API Schemas: Optimization, Experiments & Learning.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OptimizationPolicyCreate(BaseModel):
    site_id: uuid.UUID
    optimization_type: str = "ALL"
    enabled: bool = True
    risk_class: str = "CLASS_A"
    minimum_confidence: float = 0.70
    minimum_impressions: int = 500
    minimum_clicks: int = 20
    minimum_article_age_days: int = 14
    minimum_measurement_days: int = 14
    human_approval_required: bool = False
    experiment_required: bool = False
    auto_execute_allowed: bool = False
    rollback_enabled: bool = True
    cooldown_days: int = 14
    max_changes_per_article_per_month: int = 2


class OptimizationPolicyResponse(OptimizationPolicyCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationCandidateCreate(BaseModel):
    site_id: uuid.UUID
    article_id: uuid.UUID
    candidate_type: str
    source_diagnostic_id: str | None = None
    priority_score: float = 50.0
    confidence: float = 0.75
    risk_class: str = "CLASS_A"
    observed_problem: str
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    current_metrics_json: dict[str, Any] = Field(default_factory=dict)
    comparison_metrics_json: dict[str, Any] = Field(default_factory=dict)
    affected_queries_json: list[str] = Field(default_factory=list)
    possible_causes_json: list[str] = Field(default_factory=list)
    fingerprint: str = ""


class OptimizationCandidateResponse(OptimizationCandidateCreate):
    id: uuid.UUID
    status: str
    cooldown_until: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationPlanResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    article_id: uuid.UUID
    site_id: uuid.UUID
    optimization_type: str
    current_state_json: dict[str, Any]
    proposed_state_json: dict[str, Any]
    hypothesis_json: dict[str, Any]
    expected_mechanism: str
    primary_metric: str
    secondary_metrics_json: list[str]
    guardrail_metrics_json: list[str]
    baseline_period_start: datetime | None = None
    baseline_period_end: datetime | None = None
    measurement_period_days: int
    minimum_sample: int
    success_criteria_json: dict[str, Any]
    failure_criteria_json: dict[str, Any]
    rollback_criteria_json: dict[str, Any]
    risk_class: str
    approval_requirement: str
    estimated_cost: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApprovalActionRequest(BaseModel):
    decision: str  # APPROVE, REJECT
    notes: str | None = None


class ExecutionRequest(BaseModel):
    override_human_lock: bool = False
    operator_id: str = "API_USER"


class RollbackRequest(BaseModel):
    reason: str
    operator_id: str = "API_USER"


class ExperimentCreate(BaseModel):
    site_id: uuid.UUID
    article_id: uuid.UUID
    optimization_plan_id: uuid.UUID | None = None
    experiment_type: str
    hypothesis: str
    control_state_json: dict[str, Any] = Field(default_factory=dict)
    treatment_state_json: dict[str, Any] = Field(default_factory=dict)
    primary_metric: str = "search_console_ctr"
    secondary_metrics_json: list[str] = Field(default_factory=list)
    guardrail_metrics_json: list[str] = Field(default_factory=list)
    minimum_sample: int = 500
    success_threshold: float = 0.10
    rollback_threshold: float = -0.15


class ExperimentResponse(ExperimentCreate):
    id: uuid.UUID
    status: str
    baseline_start: datetime | None = None
    baseline_end: datetime | None = None
    treatment_start: datetime | None = None
    treatment_end: datetime | None = None
    result_summary_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyMemoryResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID | None = None
    scope: str
    memory_type: str
    subject: str
    observation: str
    evidence_json: dict[str, Any]
    sample_size: int
    confidence: float
    status: str
    contradicting_evidence_json: list[Any]
    version: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StrategyParameterResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID | None = None
    parameter_name: str
    category: str
    default_value: float
    current_value: float
    minimum_value: float
    maximum_value: float
    previous_value: float | None = None
    confidence: float
    last_changed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class StrategyParameterUpdate(BaseModel):
    proposed_value: float
    reason: str
    confidence: float = 0.75


class OptimizationHealthResponse(BaseModel):
    status: str
    optimization_enabled: bool
    auto_optimization_enabled: bool
    pending_approvals: int = 0
    active_experiments: int = 0
    daily_ai_cost_used: float = 0.0
    daily_ai_cost_limit: float = 20.0
    version: str = "part-9-v1"


class LearningHealthResponse(BaseModel):
    status: str
    total_memories: int = 0
    strong_memories: int = 0
    contradicted_memories: int = 0
    calibration_status: str = "CALIBRATED"
    active_strategy_version: str = "v1.0"
