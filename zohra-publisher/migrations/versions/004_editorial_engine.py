"""Editorial Generation & Drafting Engine: Part 5 models.

Revision ID: 004_editorial_engine
Revises: 003_research_engine
Create Date: 2026-10-02 07:45:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_editorial_engine"
down_revision = "003_research_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── draft_projects ────────────────────────────────────────────────
    op.create_table(
        "draft_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_package_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False, server_default="explainer"),
        sa.Column("target_audience", sa.JSON(), nullable=True),
        sa.Column("primary_keyword", sa.String(length=256), nullable=False),
        sa.Column("primary_intent", sa.String(length=64), nullable=False, server_default="informational"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="US"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("strategy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("blueprint_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("writer_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("prompt_version", sa.String(length=32), nullable=False, server_default="v1.0"),
        sa.Column("research_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("draft_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grounding_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("readability_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("intent_alignment_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("information_gain_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("seo_content_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("brand_voice_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("revalidate_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stop_reason", sa.String(length=256), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_package_id"], ["research_packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dp_status", "draft_projects", ["status"])
    op.create_index("ix_dp_opp_id", "draft_projects", ["opportunity_id"])
    op.create_index("ix_dp_research_pkg_id", "draft_projects", ["research_package_id"])
    op.create_index("ix_dp_site_id", "draft_projects", ["site_id"])

    # ── content_strategies ───────────────────────────────────────────
    op.create_table(
        "content_strategies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("reader_problem", sa.Text(), nullable=False),
        sa.Column("reader_goal", sa.Text(), nullable=False),
        sa.Column("search_intent", sa.String(length=64), nullable=False),
        sa.Column("content_goal", sa.Text(), nullable=False),
        sa.Column("recommended_content_type", sa.String(length=64), nullable=False),
        sa.Column("angle", sa.Text(), nullable=False),
        sa.Column("differentiation_strategy", sa.Text(), nullable=False),
        sa.Column("information_gain_strategy", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=64), nullable=False, server_default="authoritative_approachable"),
        sa.Column("depth", sa.String(length=32), nullable=False, server_default="comprehensive"),
        sa.Column("target_length_min", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("target_length_max", sa.Integer(), nullable=False, server_default="2400"),
        sa.Column("conversion_goal", sa.Text(), nullable=True),
        sa.Column("risk_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cs_draft_project_id", "content_strategies", ["draft_project_id"])

    # ── article_blueprints ───────────────────────────────────────────
    op.create_table(
        "article_blueprints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("working_title", sa.String(length=512), nullable=False),
        sa.Column("article_promise", sa.Text(), nullable=False),
        sa.Column("primary_intent", sa.String(length=64), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("target_audience", sa.String(length=256), nullable=True),
        sa.Column("introduction_goal", sa.Text(), nullable=False),
        sa.Column("sections_json", sa.JSON(), nullable=False),
        sa.Column("conclusion_goal", sa.Text(), nullable=False),
        sa.Column("faq_plan_json", sa.JSON(), nullable=True),
        sa.Column("table_plan_json", sa.JSON(), nullable=True),
        sa.Column("citation_plan_json", sa.JSON(), nullable=True),
        sa.Column("internal_link_plan_json", sa.JSON(), nullable=True),
        sa.Column("claim_allocation_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ab_draft_project_id", "article_blueprints", ["draft_project_id"])

    # ── draft_claim_usage ────────────────────────────────────────────
    op.create_table(
        "draft_claim_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("usage_type", sa.String(length=32), nullable=False, server_default="primary"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("citation_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dcu_project_claim", "draft_claim_usage", ["draft_project_id", "claim_id"])
    op.create_index("ix_dcu_project_section", "draft_claim_usage", ["draft_project_id", "section_id"])

    # ── draft_versions ───────────────────────────────────────────────
    op.create_table(
        "draft_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("slug_candidate", sa.String(length=256), nullable=False),
        sa.Column("meta_title", sa.String(length=256), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sections_json", sa.JSON(), nullable=True),
        sa.Column("faq_json", sa.JSON(), nullable=True),
        sa.Column("tables_json", sa.JSON(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("generation_reason", sa.String(length=64), nullable=False, server_default="initial_generation"),
        sa.Column("parent_version_id", sa.Uuid(), nullable=True),
        sa.Column("grounding_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_version_id"], ["draft_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dv_project_version", "draft_versions", ["draft_project_id", "version_number"])
    op.create_index("ix_dv_content_hash", "draft_versions", ["content_hash"])

    # ── sentence_grounding ───────────────────────────────────────────
    op.create_table(
        "sentence_grounding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.String(length=64), nullable=False),
        sa.Column("sentence_index", sa.Integer(), nullable=False),
        sa.Column("sentence_text", sa.Text(), nullable=False),
        sa.Column("sentence_text_hash", sa.String(length=64), nullable=False),
        sa.Column("claim_ids_json", sa.JSON(), nullable=False),
        sa.Column("grounding_status", sa.String(length=32), nullable=False, server_default="grounded"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_version_id"], ["draft_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sg_version_section", "sentence_grounding", ["draft_version_id", "section_id"])
    op.create_index("ix_sg_status", "sentence_grounding", ["grounding_status"])

    # ── headline_candidates ──────────────────────────────────────────
    op.create_table(
        "headline_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("headline", sa.String(length=512), nullable=False),
        sa.Column("style", sa.String(length=64), nullable=False, server_default="direct"),
        sa.Column("intent_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("clarity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("accuracy_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("seo_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("brand_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("selection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hc_draft_project_id", "headline_candidates", ["draft_project_id"])
    op.create_index("ix_hc_selected", "headline_candidates", ["selected"])

    # ── brand_voice_profiles ─────────────────────────────────────────
    op.create_table(
        "brand_voice_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("tone", sa.String(length=64), nullable=False, server_default="professional_approachable"),
        sa.Column("formality", sa.String(length=32), nullable=False, server_default="neutral"),
        sa.Column("sentence_style", sa.String(length=64), nullable=False, server_default="clear_concise"),
        sa.Column("vocabulary_level", sa.String(length=32), nullable=False, server_default="intermediate"),
        sa.Column("preferred_patterns_json", sa.JSON(), nullable=True),
        sa.Column("avoid_patterns_json", sa.JSON(), nullable=True),
        sa.Column("humor_level", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("technical_depth", sa.String(length=32), nullable=False, server_default="moderate"),
        sa.Column("directness", sa.String(length=32), nullable=False, server_default="high"),
        sa.Column("examples_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bvp_site_id", "brand_voice_profiles", ["site_id"])

    # ── revision_tasks ───────────────────────────────────────────────
    op.create_table(
        "revision_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_id", sa.Uuid(), nullable=False),
        sa.Column("issue_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("section_id", sa.String(length=64), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("before_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("after_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_version_id"], ["draft_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rt_project_status", "revision_tasks", ["draft_project_id", "status"])

    # ── research_followup_requests ───────────────────────────────────
    op.create_table(
        "research_followup_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="high"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rfr_draft_project", "research_followup_requests", ["draft_project_id"])
    op.create_index("ix_rfr_status", "research_followup_requests", ["status"])

    # ── editorial_draft_packages ─────────────────────────────────────
    op.create_table(
        "editorial_draft_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("research_package_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready_for_part6"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("grounding_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("intent_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("package_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["content_opportunities.id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_package_id"], ["research_packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_edp_draft_project_id", "editorial_draft_packages", ["draft_project_id"])
    op.create_index("ix_edp_opp_id", "editorial_draft_packages", ["opportunity_id"])

    # ── internal_link_candidates ─────────────────────────────────────
    op.create_table(
        "internal_link_candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("draft_project_id", sa.Uuid(), nullable=False),
        sa.Column("source_section_id", sa.String(length=64), nullable=False),
        sa.Column("target_content_id", sa.Uuid(), nullable=True),
        sa.Column("target_url", sa.String(length=512), nullable=False),
        sa.Column("recommended_anchor_context", sa.Text(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_project_id"], ["draft_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ilc_project_section", "internal_link_candidates", ["draft_project_id", "source_section_id"])


def downgrade() -> None:
    op.drop_table("internal_link_candidates")
    op.drop_table("editorial_draft_packages")
    op.drop_table("research_followup_requests")
    op.drop_table("revision_tasks")
    op.drop_table("brand_voice_profiles")
    op.drop_table("headline_candidates")
    op.drop_table("sentence_grounding")
    op.drop_table("draft_versions")
    op.drop_table("draft_claim_usage")
    op.drop_table("article_blueprints")
    op.drop_table("content_strategies")
    op.drop_table("draft_projects")
