"""
Zohra — Part 9 Database Models: Learning, Content Refresh, Controlled Optimization,
Experimentation, Strategy Memory, and Safe Self-Improvement.

Tables:
- optimization_policies: Site policy rules, risk classification, approval gates, cooldowns.
- optimization_candidates: Ingested Part 8 diagnostic opportunities with deduplication & lifecycle.
- optimization_plans: Auditable before/after plans, hypotheses, metrics, and criteria.
- content_snapshots: Immutable versioned content snapshots for diffs and rollback.
- optimization_changesets: Exact diffs of applied changes with rollback availability.
- optimization_approvals: Human approval queue with role-based governance.
- experiments: Controlled before/after and cohort experiments with guardrails.
- prediction_outcomes: Predicted vs actual 28-day performance for calibration.
- strategy_memories: Evidence-backed institutional memory with confidence decay & contradiction.
- strategy_parameters: Bounded strategy configuration parameters with safety clamps.
- strategy_versions: Versioned strategy configurations with shadow mode and rollback.
- freshness_policies: Content-type and claim staleness review policies.
- refresh_schedule: Calendar of proactive refresh dates.
- article_refresh_history: Log of historical article refreshes and fatigue tracking.
- optimization_events: Audit log for all Part 9 optimization and learning lifecycle actions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import JSON_FIELD, ZohraBase

# ── Enums ─────────────────────────────────────────────────────────────

class RiskClass(str, Enum):
    CLASS_A = "CLASS_A"  # Low risk (meta descriptions, non-factual titles, image alt, formatting)
    CLASS_B = "CLASS_B"  # Medium risk (substantial title change, new section, keyword repositioning)
    CLASS_C = "CLASS_C"  # High risk (major factual rewrite, merging, redirects, deleting)
    CLASS_D = "CLASS_D"  # Forbidden (security, code rewrite, credential, disabling fact-check)


class CandidateStatus(str, Enum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ELIGIBLE = "ELIGIBLE"
    HYPOTHESIS_GENERATING = "HYPOTHESIS_GENERATING"
    PLANNED = "PLANNED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    EXECUTING = "EXECUTING"
    APPLIED = "APPLIED"
    MEASURING = "MEASURING"
    SUCCESSFUL = "SUCCESSFUL"
    INCONCLUSIVE = "INCONCLUSIVE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    ARCHIVED = "ARCHIVED"


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    BASELINE_COLLECTION = "BASELINE_COLLECTION"
    RUNNING = "RUNNING"
    MEASURING = "MEASURING"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"
    STOPPED = "STOPPED"
    ROLLED_BACK = "ROLLED_BACK"
    ARCHIVED = "ARCHIVED"


class MemoryStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    STRONG = "STRONG"
    WEAKENING = "WEAKENING"
    CONTRADICTED = "CONTRADICTED"
    EXPIRED = "EXPIRED"
    RETIRED = "RETIRED"


class StrategyVersionStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SHADOW = "SHADOW"
    VALIDATING = "VALIDATING"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    ROLLBACK = "ROLLBACK"
    RETIRED = "RETIRED"


# ── 1. Optimization Policies ──────────────────────────────────────────

class OptimizationPolicy(ZohraBase):
    """Per-site optimization governance policy."""

    __tablename__ = "optimization_policies"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    optimization_type: Mapped[str] = mapped_column(String(64), nullable=False, default="ALL", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    risk_class: Mapped[str] = mapped_column(String(32), nullable=False, default=RiskClass.CLASS_A.value)
    minimum_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.70)
    minimum_impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    minimum_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    minimum_article_age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    minimum_measurement_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    experiment_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_execute_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollback_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cooldown_days: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    max_changes_per_article_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    __table_args__ = (
        UniqueConstraint("site_id", "optimization_type", name="uq_opt_policy_site_type"),
    )


# ── 2. Optimization Candidates ─────────────────────────────────────────

class OptimizationCandidate(ZohraBase):
    """Candidate optimization unit ingested from Part 8 or internal signals."""

    __tablename__ = "optimization_candidates"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    candidate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_diagnostic_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    risk_class: Mapped[str] = mapped_column(String(32), nullable=False, default=RiskClass.CLASS_A.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=CandidateStatus.RECEIVED.value, index=True)
    observed_problem: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    current_metrics_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    comparison_metrics_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    affected_queries_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    possible_causes_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_opt_cand_site_art", "site_id", "article_id"),
        Index("ix_opt_cand_fingerprint", "fingerprint"),
    )


# ── 3. Optimization Plans ─────────────────────────────────────────────

class OptimizationPlan(ZohraBase):
    """Detailed bounded plan for an approved optimization hypothesis."""

    __tablename__ = "optimization_plans"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("optimization_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    optimization_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    current_state_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    proposed_state_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    hypothesis_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    expected_mechanism: Mapped[str] = mapped_column(Text, nullable=False)
    primary_metric: Mapped[str] = mapped_column(String(64), nullable=False, default="search_console_ctr")
    secondary_metrics_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    guardrail_metrics_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    baseline_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    baseline_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    measurement_period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=28)
    minimum_sample: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    success_criteria_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    failure_criteria_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    rollback_criteria_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    risk_class: Mapped[str] = mapped_column(String(32), nullable=False, default=RiskClass.CLASS_A.value)
    approval_requirement: Mapped[str] = mapped_column(String(32), nullable=False, default="NONE")
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLANNED", index=True)


# ── 4. Content Snapshots ──────────────────────────────────────────────

class ContentSnapshot(ZohraBase):
    """Immutable point-in-time snapshot of published content for change audit & rollback."""

    __tablename__ = "content_snapshots"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_type: Mapped[str] = mapped_column(String(64), nullable=False, default="BEFORE_OPTIMIZATION")
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    meta_title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slug: Mapped[str | None] = mapped_column(String(512), nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    article_body: Mapped[str] = mapped_column(Text, nullable=False)
    headings_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    internal_links_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    external_links_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    schema_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    featured_image_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    wordpress_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wordpress_revision_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_cnt_snap_art_hash", "article_id", "content_hash"),
    )


# ── 5. Optimization Changesets ────────────────────────────────────────

class OptimizationChangeset(ZohraBase):
    """Detailed diff and execution metadata for an applied optimization."""

    __tablename__ = "optimization_changesets"

    optimization_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("optimization_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    before_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    after_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    diff_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    executed_by: Mapped[str] = mapped_column(String(128), nullable=False, default="AUTONOMOUS_ENGINE")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rollback_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="APPLIED", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── 6. Optimization Approvals ─────────────────────────────────────────

class OptimizationApproval(ZohraBase):
    """Human approval record for Medium/High risk optimization plans."""

    __tablename__ = "optimization_approvals"

    optimization_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("optimization_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    required_role: Mapped[str] = mapped_column(String(64), nullable=False, default="EDITOR")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── 7. Experiments ────────────────────────────────────────────────────

class Experiment(ZohraBase):
    """Controlled SEO/content experiment tracking."""

    __tablename__ = "experiments"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    optimization_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("optimization_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    experiment_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ExperimentStatus.DRAFT.value, index=True)
    control_state_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    treatment_state_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    primary_metric: Mapped[str] = mapped_column(String(64), nullable=False, default="search_console_ctr")
    secondary_metrics_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    guardrail_metrics_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    baseline_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    baseline_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    treatment_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    treatment_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    minimum_sample: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    success_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.10)
    rollback_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=-0.15)
    result_summary_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)


# ── 8. Prediction Outcomes (Calibration) ──────────────────────────────

class PredictionOutcome(ZohraBase):
    """Records pre-publication prediction vs actual measured outcome for calibration."""

    __tablename__ = "prediction_outcomes"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    prediction_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # OPPORTUNITY_SCORE, CTR_PREDICTION, etc.
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prediction_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluation_window: Mapped[str] = mapped_column(String(32), nullable=False, default="28d")
    error_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── 9. Strategy Memories ──────────────────────────────────────────────

class StrategyMemory(ZohraBase):
    """Evidence-backed institutional knowledge learned across experiments & performance."""

    __tablename__ = "strategy_memories"

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="SITE")  # GLOBAL, SITE, NICHE, TOPIC, CONTENT_TYPE
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=MemoryStatus.CANDIDATE.value, index=True)
    contradicting_evidence_json: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ── 10. Strategy Parameters ───────────────────────────────────────────

class StrategyParameter(ZohraBase):
    """Configurable bounded parameter for strategy allocation and optimization."""

    __tablename__ = "strategy_parameters"

    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parameter_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    default_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_value: Mapped[float] = mapped_column(Float, nullable=False)
    maximum_value: Mapped[float] = mapped_column(Float, nullable=False)
    previous_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    evidence_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "parameter_name", name="uq_strat_param_site_name"),
    )


# ── 11. Strategy Versions ─────────────────────────────────────────────

class StrategyVersion(ZohraBase):
    """Versioned snapshot of site strategy parameters supporting shadow evaluation."""

    __tablename__ = "strategy_versions"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=StrategyVersionStatus.PROPOSED.value, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "version", name="uq_strat_ver_site_ver"),
    )


# ── 12. Freshness Policies ────────────────────────────────────────────

class FreshnessPolicy(ZohraBase):
    """Configurable freshness review rules by topic or content type."""

    __tablename__ = "freshness_policies"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claim_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_staleness_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    review_interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ── 13. Refresh Schedule ──────────────────────────────────────────────

class RefreshSchedule(ZohraBase):
    """Proactive review calendar for articles requiring potential refresh."""

    __tablename__ = "refresh_schedule"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    priority: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("freshness_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SCHEDULED", index=True)


# ── 14. Article Refresh History ───────────────────────────────────────

class ArticleRefreshHistory(ZohraBase):
    """Historical audit of all refreshes applied to an article."""

    __tablename__ = "article_refresh_history"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False)
    before_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    after_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_snapshots.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_result_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    performance_result_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    lifetime_optimization_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


# ── 15. Optimization Events ───────────────────────────────────────────

class OptimizationEvent(ZohraBase):
    """Full auditable lifecycle log of Part 9 optimization and learning operations."""

    __tablename__ = "optimization_events"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(128), nullable=False, default="SYSTEM")
    details_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
