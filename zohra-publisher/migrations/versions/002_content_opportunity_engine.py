"""Content Opportunity Engine: Part 3 models.

Revision ID: 002_content_opportunity_engine
Revises: 001_initial_schema
Create Date: 2026-10-02 05:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002_content_opportunity_engine"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── sites ──────────────────────────────────────────────────────────
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("default_language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("primary_country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("niche", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_audiences", sa.JSON(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_index("ix_sites_domain_enabled", "sites", ["domain", "enabled"])

    # ── site_topics ────────────────────────────────────────────────────
    op.create_table(
        "site_topics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("topic_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_slug", sa.String(length=255), nullable=False),
        sa.Column("relevance_weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("topical_authority_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("historical_post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_topics_site_slug", "site_topics", ["site_id", "canonical_slug"], unique=True)

    # ── site_content ───────────────────────────────────────────────────
    op.create_table(
        "site_content",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("external_post_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("slug", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("primary_topic", sa.String(length=255), nullable=True),
        sa.Column("primary_keyword", sa.String(length=512), nullable=True),
        sa.Column("secondary_keywords", sa.JSON(), nullable=True),
        sa.Column("primary_intent", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="published"),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("performance_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_content_site_url", "site_content", ["site_id", "url"], unique=True)

    # ── keywords ───────────────────────────────────────────────────────
    op.create_table(
        "keywords",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("keyword", sa.String(length=512), nullable=False),
        sa.Column("normalized_keyword", sa.String(length=512), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("intent", sa.String(length=50), nullable=False),
        sa.Column("intent_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("secondary_intent", sa.String(length=50), nullable=True),
        sa.Column("search_demand_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("search_volume", sa.Integer(), nullable=True),
        sa.Column("search_volume_source", sa.String(length=100), nullable=True),
        sa.Column("search_volume_confidence", sa.Float(), nullable=True),
        sa.Column("competition_metric", sa.Float(), nullable=True),
        sa.Column("competition_source", sa.String(length=100), nullable=True),
        sa.Column("cpc", sa.Float(), nullable=True),
        sa.Column("cpc_currency", sa.String(length=10), nullable=True),
        sa.Column("cpc_source", sa.String(length=100), nullable=True),
        sa.Column("trend_direction", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("freshness_sensitivity", sa.String(length=50), nullable=False, server_default="evergreen"),
        sa.Column("commercial_value_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_keywords_norm_lang_ctry",
        "keywords",
        ["normalized_keyword", "language", "country"],
        unique=True,
    )

    # ── keyword_clusters ───────────────────────────────────────────────
    op.create_table(
        "keyword_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_topic", sa.String(length=512), nullable=False),
        sa.Column("primary_keyword", sa.String(length=512), nullable=False),
        sa.Column("primary_intent", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("keyword_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("aggregate_demand_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("commercial_value_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("cluster_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clusters_prim_lang_ctry", "keyword_clusters", ["primary_keyword", "language", "country"])

    # ── keyword_cluster_members ────────────────────────────────────────
    op.create_table(
        "keyword_cluster_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("keyword_id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["keyword_clusters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cluster_members_pair", "keyword_cluster_members", ["cluster_id", "keyword_id"], unique=True)

    # ── serp_snapshots ─────────────────────────────────────────────────
    op.create_table(
        "serp_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=512), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False, server_default="mock"),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("device", sa.String(length=20), nullable=False, server_default="desktop"),
        sa.Column("total_results_estimate", sa.Integer(), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("dominant_intent", sa.String(length=50), nullable=False, server_default="informational"),
        sa.Column("intent_alignment_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_serp_snapshots_lookup", "serp_snapshots", ["query_hash", "country", "language", "device"])

    # ── serp_results ───────────────────────────────────────────────────
    op.create_table(
        "serp_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("result_type", sa.String(length=50), nullable=False, server_default="organic"),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_official_domain", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_forum", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["serp_snapshots.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_serp_results_snapshot_pos", "serp_results", ["snapshot_id", "position"])

    # ── topic_clusters ─────────────────────────────────────────────────
    op.create_table(
        "topic_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("canonical_topic", sa.String(length=255), nullable=False),
        sa.Column("pillar_opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("aggregate_opportunity_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("topical_relevance_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topic_clusters_site_topic", "topic_clusters", ["site_id", "canonical_topic"])

    # ── content_opportunities ──────────────────────────────────────────
    op.create_table(
        "content_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("topic_cluster_id", sa.Uuid(), nullable=True),
        sa.Column("canonical_topic", sa.String(length=512), nullable=False),
        sa.Column("proposed_angle", sa.String(length=512), nullable=False),
        sa.Column("working_title", sa.String(length=1024), nullable=False),
        sa.Column("primary_keyword", sa.String(length=512), nullable=False),
        sa.Column("primary_intent", sa.String(length=50), nullable=False),
        sa.Column("secondary_intent", sa.String(length=50), nullable=True),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("target_audience", sa.JSON(), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="global"),
        sa.Column("cluster_role", sa.String(length=50), nullable=False, server_default="standalone"),
        sa.Column("recommended_action", sa.String(length=50), nullable=False, server_default="create"),
        sa.Column("target_content_id", sa.Uuid(), nullable=True),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("search_demand_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("intent_strength_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("competition_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("competition_opportunity_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("evergreen_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("site_relevance_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("topical_authority_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("original_value_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("information_gain_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("serp_gap_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("monetization_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("audience_fit_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("content_type_fit_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("cannibalization_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("opportunity_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("scoring_profile", sa.String(length=50), nullable=False, server_default="default"),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("penalties_breakdown", sa.JSON(), nullable=True),
        sa.Column("score_reasons", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="candidate"),
        sa.Column("priority", sa.String(length=50), nullable=False, server_default="qualified"),
        sa.Column("dependency_status", sa.String(length=50), nullable=False, server_default="ready"),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("freshness_decay_type", sa.String(length=50), nullable=False, server_default="evergreen"),
        sa.Column("opportunity_half_life_hours", sa.Float(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scoring_version", sa.String(length=20), nullable=False, server_default="1.0.0"),
        sa.Column("analysis_version", sa.String(length=20), nullable=False, server_default="1.0.0"),
        sa.Column("analysis_depth", sa.String(length=20), nullable=False, server_default="standard"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_content_id"], ["site_content.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["topic_cluster_id"], ["topic_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_site_status_score", "content_opportunities", ["site_id", "status", "opportunity_score"])

    # ── content_gaps ───────────────────────────────────────────────────
    op.create_table(
        "content_gaps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("keyword_cluster_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("gap_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["keyword_cluster_id"], ["keyword_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── discovered_questions ───────────────────────────────────────────
    op.create_table(
        "discovered_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("normalized_question", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(length=50), nullable=False, server_default="informational"),
        sa.Column("keyword_cluster_id", sa.Uuid(), nullable=True),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("source", sa.String(length=100), nullable=False, server_default="serp_paa"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["keyword_cluster_id"], ["keyword_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── opportunity_snapshots ──────────────────────────────────────────
    op.create_table(
        "opportunity_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("search_demand_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("competition_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("evergreen_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("monetization_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cannibalization_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── opportunity_watchlist ──────────────────────────────────────────
    op.create_table(
        "opportunity_watchlist",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("recheck_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recheck_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["content_opportunities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opp_watchlist_active_recheck", "opportunity_watchlist", ["is_active", "recheck_after"])


def downgrade() -> None:
    op.drop_table("opportunity_watchlist")
    op.drop_table("opportunity_snapshots")
    op.drop_table("discovered_questions")
    op.drop_table("content_gaps")
    op.drop_table("content_opportunities")
    op.drop_table("topic_clusters")
    op.drop_table("serp_results")
    op.drop_table("serp_snapshots")
    op.drop_table("keyword_cluster_members")
    op.drop_table("keyword_clusters")
    op.drop_table("keywords")
    op.drop_table("site_content")
    op.drop_table("site_topics")
    op.drop_table("sites")
