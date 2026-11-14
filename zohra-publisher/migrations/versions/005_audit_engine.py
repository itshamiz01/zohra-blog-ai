"""Editorial Audit & Quality Firewall: Part 6 models.

Revision ID: 005_audit_engine
Revises: 004_editorial_engine
Create Date: 2026-10-02 09:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "005_audit_engine"
down_revision = "004_editorial_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── audit_projects ────────────────────────────────────────────────
    op.create_table(
        "audit_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_id", sa.Uuid(), nullable=True),
        sa.Column("research_project_id", sa.Uuid(), nullable=True),
        sa.Column("research_package_id", sa.Uuid(), nullable=False),
        sa.Column("research_package_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("audit_type", sa.String(length=32), nullable=False, server_default="full_publication_audit"),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("factual_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("citation_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grounding_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("temporal_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("originality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("intent_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("information_gain_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("seo_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("content_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("structure_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("brand_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("overall_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("critical_issue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("major_issue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minor_issue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("decision_reason_json", sa.JSON(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("auditor_version", sa.String(length=32), nullable=False, server_default="part6-v1.0"),
        sa.Column("policy_version", sa.String(length=32), nullable=False, server_default="policy-v1.0"),
        sa.Column("audit_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_version_id"], ["draft_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_package_id"], ["research_packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_draft_proj", "audit_projects", ["draft_project_id"])
    op.create_index("ix_ap_res_pkg", "audit_projects", ["research_package_id"])
    op.create_index("ix_ap_decision", "audit_projects", ["decision"])
    op.create_index("ix_ap_status", "audit_projects", ["status"])
    op.create_index("ix_ap_risk_level", "audit_projects", ["risk_level"])
    op.create_index("ix_ap_audit_fingerprint", "audit_projects", ["audit_fingerprint"])

    # ── audit_issues ──────────────────────────────────────────────────
    op.create_table(
        "audit_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_project_id", sa.Uuid(), nullable=False),
        sa.Column("issue_code", sa.String(length=64), nullable=False),
        sa.Column("issue_category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MAJOR"),
        sa.Column("section_id", sa.String(length=128), nullable=True),
        sa.Column("paragraph_index", sa.Integer(), nullable=True),
        sa.Column("sentence_index", sa.Integer(), nullable=True),
        sa.Column("claim_id", sa.Uuid(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("routing_target", sa.String(length=32), nullable=False, server_default="part5_writer"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("overridden_by", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_project_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_proj_sev", "audit_issues", ["audit_project_id", "severity"])
    op.create_index("ix_ai_code", "audit_issues", ["issue_code"])
    op.create_index("ix_ai_cat", "audit_issues", ["issue_category"])
    op.create_index("ix_ai_status", "audit_issues", ["status"])

    # ── audited_claims ────────────────────────────────────────────────
    op.create_table(
        "audited_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_project_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.String(length=128), nullable=True),
        sa.Column("sentence_index", sa.Integer(), nullable=True),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("normalized_claim", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=False, server_default="factual"),
        sa.Column("importance", sa.String(length=32), nullable=False, server_default="supporting"),
        sa.Column("matched_research_claim_id", sa.Uuid(), nullable=True),
        sa.Column("match_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("verification_status", sa.String(length=64), nullable=False, server_default="UNSUPPORTED"),
        sa.Column("entailment_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("audit_notes", sa.Text(), nullable=True),
        sa.Column("extracted_numbers", sa.JSON(), nullable=True),
        sa.Column("extracted_dates", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_project_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_research_claim_id"], ["claims.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ac_proj_status", "audited_claims", ["audit_project_id", "verification_status"])

    # ── content_overlap_findings ──────────────────────────────────────
    op.create_table(
        "content_overlap_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_project_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("draft_location", sa.String(length=128), nullable=False),
        sa.Column("source_location", sa.String(length=256), nullable=True),
        sa.Column("overlap_type", sa.String(length=64), nullable=False, server_default="exact_ngram"),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("matched_text_hash", sa.String(length=128), nullable=True),
        sa.Column("matched_text_sample", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MAJOR"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_project_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cof_proj_type", "content_overlap_findings", ["audit_project_id", "overlap_type"])

    # ── content_risk_policies ─────────────────────────────────────────
    op.create_table(
        "content_risk_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("minimum_research_quality", sa.Float(), nullable=False, server_default="80.0"),
        sa.Column("minimum_grounding", sa.Float(), nullable=False, server_default="95.0"),
        sa.Column("minimum_factual_score", sa.Float(), nullable=False, server_default="95.0"),
        sa.Column("minimum_citation_score", sa.Float(), nullable=False, server_default="90.0"),
        sa.Column("minimum_overall_quality", sa.Float(), nullable=False, server_default="85.0"),
        sa.Column("human_review_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("auto_publish_allowed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("freshness_requirement_hours", sa.Integer(), nullable=True),
        sa.Column("strict_quote_enforcement", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("political_neutrality_enforced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("policy_version", sa.String(length=32), nullable=False, server_default="v1.0"),
        sa.Column("rules_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_crp_cat_risk", "content_risk_policies", ["category", "risk_level"], unique=True)

    # ── audit_checks ──────────────────────────────────────────────────
    op.create_table(
        "audit_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_project_id", sa.Uuid(), nullable=False),
        sa.Column("check_type", sa.String(length=64), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_project_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ac_proj_type", "audit_checks", ["audit_project_id", "check_type"], unique=True)

    # ── final_audit_packages ──────────────────────────────────────────
    op.create_table(
        "final_audit_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_project_id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("research_package_id", sa.Uuid(), nullable=False),
        sa.Column("research_package_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("eligible_for_part7", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("overall_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("factual_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grounding_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("audit_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("audit_token", sa.String(length=256), nullable=False),
        sa.Column("package_json", sa.JSON(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["audit_project_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_package_id"], ["research_packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fap_audit_project_id", "final_audit_packages", ["audit_project_id"], unique=True)
    op.create_index("ix_fap_token", "final_audit_packages", ["audit_token"], unique=True)
    op.create_index("ix_fap_hash", "final_audit_packages", ["content_hash"])
    op.create_index("ix_fap_decision", "final_audit_packages", ["decision"])
    op.create_index("ix_fap_eligible", "final_audit_packages", ["eligible_for_part7"])


def downgrade() -> None:
    op.drop_table("final_audit_packages")
    op.drop_table("audit_checks")
    op.drop_table("content_risk_policies")
    op.drop_table("content_overlap_findings")
    op.drop_table("audited_claims")
    op.drop_table("audit_issues")
    op.drop_table("audit_projects")
