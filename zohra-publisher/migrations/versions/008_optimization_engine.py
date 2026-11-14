"""Learning Engine, Strategy Memory & Controlled Self-Optimization: Part 9 models.

Revision ID: 008_optimization_engine
Revises: 007_search_analytics
Create Date: 2026-10-02 12:15:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "008_optimization_engine"
down_revision = "007_search_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. optimization_policies ──────────────────────────────────────
    op.create_table(
        "optimization_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("optimization_type", sa.String(length=64), nullable=False, server_default="ALL"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("risk_class", sa.String(length=32), nullable=False, server_default="CLASS_A"),
        sa.Column("minimum_confidence", sa.Float(), nullable=False, server_default="0.70"),
        sa.Column("minimum_impressions", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("minimum_clicks", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("minimum_article_age_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("minimum_measurement_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("human_approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("experiment_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_execute_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rollback_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("cooldown_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("max_changes_per_article_per_month", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "optimization_type", name="uq_opt_policy_site_type"),
    )

    # ── 2. optimization_candidates ────────────────────────────────────
    op.create_table(
        "optimization_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_type", sa.String(length=64), nullable=False),
        sa.Column("source_diagnostic_id", sa.String(length=128), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.70"),
        sa.Column("risk_class", sa.String(length=32), nullable=False, server_default="CLASS_A"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RECEIVED"),
        sa.Column("observed_problem", sa.Text(), nullable=False),
        sa.Column("deduplication_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("current_metrics_json", sa.JSON(), nullable=False),
        sa.Column("comparison_metrics_json", sa.JSON(), nullable=False),
        sa.Column("affected_queries_json", sa.JSON(), nullable=False),
        sa.Column("possible_causes_json", sa.JSON(), nullable=False),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deduplication_fingerprint", name="uq_opt_candidate_fingerprint"),
    )

    # ── 3. optimization_plans ─────────────────────────────────────────
    op.create_table(
        "optimization_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("optimization_type", sa.String(length=64), nullable=False),
        sa.Column("current_state_json", sa.JSON(), nullable=False),
        sa.Column("proposed_state_json", sa.JSON(), nullable=False),
        sa.Column("hypothesis_json", sa.JSON(), nullable=False),
        sa.Column("expected_mechanism", sa.Text(), nullable=False),
        sa.Column("primary_metric", sa.String(length=64), nullable=False, server_default="search_console_ctr"),
        sa.Column("secondary_metrics_json", sa.JSON(), nullable=False),
        sa.Column("guardrail_metrics_json", sa.JSON(), nullable=False),
        sa.Column("baseline_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("baseline_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("measurement_period_days", sa.Integer(), nullable=False, server_default="28"),
        sa.Column("minimum_sample", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("success_criteria_json", sa.JSON(), nullable=False),
        sa.Column("failure_criteria_json", sa.JSON(), nullable=False),
        sa.Column("rollback_criteria_json", sa.JSON(), nullable=False),
        sa.Column("risk_class", sa.String(length=32), nullable=False, server_default="CLASS_A"),
        sa.Column("approval_requirement", sa.String(length=32), nullable=False, server_default="NONE"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["optimization_candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 4. content_snapshots ──────────────────────────────────────────
    op.create_table(
        "content_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_type", sa.String(length=32), nullable=False, server_default="BEFORE_OPTIMIZATION"),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("meta_title", sa.String(length=512), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=512), nullable=True),
        sa.Column("canonical_url", sa.String(length=1024), nullable=True),
        sa.Column("article_body", sa.Text(), nullable=False),
        sa.Column("headings_json", sa.JSON(), nullable=False),
        sa.Column("internal_links_json", sa.JSON(), nullable=False),
        sa.Column("external_links_json", sa.JSON(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("featured_image_json", sa.JSON(), nullable=False),
        sa.Column("wordpress_post_id", sa.Integer(), nullable=True),
        sa.Column("wordpress_revision_id", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 5. optimization_changesets ────────────────────────────────────
    op.create_table(
        "optimization_changesets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("optimization_plan_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("before_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("after_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("change_type", sa.String(length=64), nullable=False),
        sa.Column("diff_json", sa.JSON(), nullable=False),
        sa.Column("executed_by", sa.String(length=64), nullable=False, server_default="OPTIMIZATION_ENGINE"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rollback_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rollback_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="APPLIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["optimization_plan_id"], ["optimization_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 6. optimization_approvals ─────────────────────────────────────
    op.create_table(
        "optimization_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("optimization_plan_id", sa.Uuid(), nullable=False),
        sa.Column("required_role", sa.String(length=32), nullable=False, server_default="ADMIN"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(length=128), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["optimization_plan_id"], ["optimization_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 7. experiments ────────────────────────────────────────────────
    op.create_table(
        "experiments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("optimization_plan_id", sa.Uuid(), nullable=True),
        sa.Column("experiment_type", sa.String(length=64), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("control_state_json", sa.JSON(), nullable=False),
        sa.Column("treatment_state_json", sa.JSON(), nullable=False),
        sa.Column("primary_metric", sa.String(length=64), nullable=False, server_default="search_console_ctr"),
        sa.Column("secondary_metrics_json", sa.JSON(), nullable=False),
        sa.Column("guardrail_metrics_json", sa.JSON(), nullable=False),
        sa.Column("baseline_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("baseline_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("treatment_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("treatment_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minimum_sample", sa.Integer(), nullable=False, server_default="500"),
        sa.Column("success_threshold", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("rollback_threshold", sa.Float(), nullable=False, server_default="-0.15"),
        sa.Column("result_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 8. prediction_outcomes ────────────────────────────────────────
    op.create_table(
        "prediction_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("prediction_type", sa.String(length=64), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("predicted_class", sa.String(length=64), nullable=True),
        sa.Column("prediction_confidence", sa.Float(), nullable=False, server_default="0.50"),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("actual_class", sa.String(length=64), nullable=True),
        sa.Column("evaluation_window", sa.String(length=32), nullable=False, server_default="28_DAYS"),
        sa.Column("error_delta", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 9. strategy_memories ──────────────────────────────────────────
    op.create_table(
        "strategy_memories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="SITE"),
        sa.Column("memory_type", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("observation", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.50"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CANDIDATE"),
        sa.Column("contradicting_evidence_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 10. strategy_parameters ───────────────────────────────────────
    op.create_table(
        "strategy_parameters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("parameter_name", sa.String(128), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("default_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("minimum_value", sa.Float(), nullable=False),
        sa.Column("maximum_value", sa.Float(), nullable=False),
        sa.Column("previous_value", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("evidence_reference", sa.String(255), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rollback_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "parameter_name", name="uq_strategy_param_site"),
    )

    # ── 11. strategy_versions ─────────────────────────────────────────
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="PROPOSED"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "version", name="uq_strategy_version_site"),
    )

    # ── 12. freshness_policies ────────────────────────────────────────
    op.create_table(
        "freshness_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(128), nullable=False, server_default="ALL"),
        sa.Column("content_type", sa.String(64), nullable=False, server_default="ALL"),
        sa.Column("max_staleness_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("proactive_review_days_before_expiry", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "topic", "content_type", name="uq_freshness_policy_site"),
    )

    # ── 13. refresh_schedules ─────────────────────────────────────────
    op.create_table(
        "refresh_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False, server_default="REFRESH_CANDIDATE"),
        sa.Column("status", sa.String(32), nullable=False, server_default="SCHEDULED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 14. article_refresh_histories ─────────────────────────────────
    op.create_table(
        "article_refresh_histories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("change_type", sa.String(64), nullable=False),
        sa.Column("before_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("after_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("verification_passed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("performance_delta_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 15. optimization_events ───────────────────────────────────────
    op.create_table(
        "optimization_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_data_json", sa.JSON(), nullable=False),
        sa.Column("actor", sa.String(64), nullable=False, server_default="SYSTEM"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("optimization_events")
    op.drop_table("article_refresh_histories")
    op.drop_table("refresh_schedules")
    op.drop_table("freshness_policies")
    op.drop_table("strategy_versions")
    op.drop_table("strategy_parameters")
    op.drop_table("strategy_memories")
    op.drop_table("prediction_outcomes")
    op.drop_table("experiments")
    op.drop_table("optimization_approvals")
    op.drop_table("optimization_changesets")
    op.drop_table("content_snapshots")
    op.drop_table("optimization_plans")
    op.drop_table("optimization_candidates")
    op.drop_table("optimization_policies")
