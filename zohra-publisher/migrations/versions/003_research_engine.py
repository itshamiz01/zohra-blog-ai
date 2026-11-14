"""Autonomous Deep Research Engine: Part 4 models.

Revision ID: 003_research_engine
Revises: 002_content_opportunity_engine
Create Date: 2026-10-02 06:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "003_research_engine"
down_revision = "002_content_opportunity_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── research_projects ─────────────────────────────────────────────
    op.create_table(
        "research_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("research_depth", sa.String(length=50), nullable=False, server_default="STANDARD"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="US"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="standard"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verified_claim_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("contradiction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("critical_claim_coverage_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("research_confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("research_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("research_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("stop_reason", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_proj_site_status", "research_projects", ["site_id", "status"])
    op.create_index("ix_res_proj_opp_version", "research_projects", ["opportunity_id", "research_version"])

    # ── research_questions ───────────────────────────────────────────
    op.create_table(
        "research_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.String(length=1024), nullable=False),
        sa.Column("question_type", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("requires_primary_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_multiple_sources", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="unanswered"),
        sa.Column("answer_summary", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_q_proj_priority", "research_questions", ["research_project_id", "priority"])
    op.create_index("ix_res_q_proj_status", "research_questions", ["research_project_id", "status"])

    # ── research_queries ─────────────────────────────────────────────
    op.create_table(
        "research_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("research_question_id", sa.Uuid(), nullable=True),
        sa.Column("query", sa.String(length=512), nullable=False),
        sa.Column("query_type", sa.String(length=50), nullable=False, server_default="general_web"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="US"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="internal"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_question_id"], ["research_questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_query_proj_type", "research_queries", ["research_project_id", "query_type"])
    op.create_index("ix_res_query_proj_status", "research_queries", ["research_project_id", "status"])

    # ── research_sources ─────────────────────────────────────────────
    op.create_table(
        "research_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_tier", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="news_report"),
        sa.Column("is_primary_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_official_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("independence_group_id", sa.String(length=64), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("authority_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("research_value_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="discovered"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_src_proj_canonical", "research_sources", ["research_project_id", "canonical_url"])
    op.create_index("ix_res_src_proj_primary", "research_sources", ["research_project_id", "is_primary_source"])

    # ── document_versions ────────────────────────────────────────────
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_source_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("raw_excerpt", sa.Text(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("has_changed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doc_ver_source_hash", "document_versions", ["research_source_id", "content_hash"])

    # ── claims ───────────────────────────────────────────────────────
    op.create_table(
        "claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("normalized_claim", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=50), nullable=False, server_default="fact"),
        sa.Column("subject_entity", sa.String(length=255), nullable=True),
        sa.Column("predicate", sa.String(length=255), nullable=True),
        sa.Column("object_value", sa.Text(), nullable=True),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("region", sa.String(length=50), nullable=True),
        sa.Column("temporal_scope", sa.String(length=100), nullable=True),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("importance", sa.String(length=20), nullable=False, server_default="major"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="unverified"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("verification_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("time_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("attribution_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("writer_policy", sa.String(length=50), nullable=False, server_default="DO_NOT_STATE_AS_FACT"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_claims_proj_importance", "claims", ["research_project_id", "importance"])
    op.create_index("ix_claims_proj_status", "claims", ["research_project_id", "status"])
    op.create_index("ix_claims_proj_policy", "claims", ["research_project_id", "writer_policy"])

    # ── evidence_items ───────────────────────────────────────────────
    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("research_source_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_type", sa.String(length=50), nullable=False, server_default="secondary_reporting"),
        sa.Column("support_direction", sa.String(length=50), nullable=False, server_default="supports"),
        sa.Column("evidence_text_reference", sa.Text(), nullable=False),
        sa.Column("source_location", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("evidence_strength_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_claim_direction", "evidence_items", ["claim_id", "support_direction"])
    op.create_index("ix_evidence_source_direction", "evidence_items", ["research_source_id", "support_direction"])

    # ── contradictions ───────────────────────────────────────────────
    op.create_table(
        "contradictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("claim_a_id", sa.Uuid(), nullable=False),
        sa.Column("claim_b_id", sa.Uuid(), nullable=False),
        sa.Column("contradiction_type", sa.String(length=50), nullable=False, server_default="numeric_mismatch"),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="major"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resolution_status", sa.String(length=50), nullable=False, server_default="unresolved"),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("preferred_claim_id", sa.Uuid(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_a_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["claim_b_id"], ["claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["preferred_claim_id"], ["claims.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contra_proj_status", "contradictions", ["research_project_id", "resolution_status"])
    op.create_index("ix_contra_proj_severity", "contradictions", ["research_project_id", "severity"])

    # ── entity_relationships ─────────────────────────────────────────
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=True),
        sa.Column("subject_entity_id", sa.Uuid(), nullable=False),
        sa.Column("predicate", sa.String(length=100), nullable=False),
        sa.Column("object_entity_id", sa.Uuid(), nullable=True),
        sa.Column("object_value", sa.String(length=255), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ent_rel_subj_pred", "entity_relationships", ["subject_entity_id", "predicate"])

    # ── research_timeline_events ─────────────────────────────────────
    op.create_table(
        "research_timeline_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_time_precision", sa.String(length=50), nullable=False, server_default="date"),
        sa.Column("time_raw_text", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=20), nullable=False, server_default="major"),
        sa.Column("source_ids", sa.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_time_proj_time", "research_timeline_events", ["research_project_id", "event_time"])

    # ── research_gaps ────────────────────────────────────────────────
    op.create_table(
        "research_gaps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("research_question_id", sa.Uuid(), nullable=True),
        sa.Column("gap_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=20), nullable=False, server_default="major"),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["research_question_id"], ["research_questions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_gap_proj_status", "research_gaps", ["research_project_id", "status"])
    op.create_index("ix_res_gap_proj_type", "research_gaps", ["research_project_id", "gap_type"])

    # ── research_notes ───────────────────────────────────────────────
    op.create_table(
        "research_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("note_type", sa.String(length=50), nullable=False, server_default="observation"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_note_proj_type", "research_notes", ["research_project_id", "note_type"])

    # ── research_packages ────────────────────────────────────────────
    op.create_table(
        "research_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("research_project_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_immutable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("verified_facts_json", sa.JSON(), nullable=True),
        sa.Column("uncertain_claims_json", sa.JSON(), nullable=True),
        sa.Column("contradictions_json", sa.JSON(), nullable=True),
        sa.Column("timeline_json", sa.JSON(), nullable=True),
        sa.Column("entities_json", sa.JSON(), nullable=True),
        sa.Column("primary_sources_json", sa.JSON(), nullable=True),
        sa.Column("supporting_sources_json", sa.JSON(), nullable=True),
        sa.Column("questions_answered_json", sa.JSON(), nullable=True),
        sa.Column("questions_unanswered_json", sa.JSON(), nullable=True),
        sa.Column("content_gaps_json", sa.JSON(), nullable=True),
        sa.Column("important_numbers_json", sa.JSON(), nullable=True),
        sa.Column("important_dates_json", sa.JSON(), nullable=True),
        sa.Column("limitations_json", sa.JSON(), nullable=True),
        sa.Column("risk_flags_json", sa.JSON(), nullable=True),
        sa.Column("research_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("research_confidence_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_quality_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("critical_claim_coverage_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("instructions_for_writer_json", sa.JSON(), nullable=True),
        sa.Column("citation_map_json", sa.JSON(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["research_project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_res_pkg_opp_ver", "research_packages", ["opportunity_id", "version"], unique=True)
    op.create_index("ix_res_pkg_proj_ver", "research_packages", ["research_project_id", "version"])


def downgrade() -> None:
    op.drop_table("research_packages")
    op.drop_table("research_notes")
    op.drop_table("research_gaps")
    op.drop_table("research_timeline_events")
    op.drop_table("entity_relationships")
    op.drop_table("contradictions")
    op.drop_table("evidence_items")
    op.drop_table("claims")
    op.drop_table("document_versions")
    op.drop_table("research_sources")
    op.drop_table("research_queries")
    op.drop_table("research_questions")
    op.drop_table("research_projects")
