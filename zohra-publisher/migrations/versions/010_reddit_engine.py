"""Reddit Opportunity & Referral Engine: Part 11 models.

Revision ID: 010_reddit_engine
Revises: 009_production_operations
Create Date: 2026-10-03 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "010_reddit_engine"
down_revision = "009_production_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. reddit_sources ─────────────────────────────────────────────
    op.create_table(
        "reddit_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("subscriber_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevance_keywords", sa.JSON(), nullable=False),
        sa.Column("scan_frequency_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("post_count_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_sources_site_id", "reddit_sources", ["site_id"])
    op.create_index("ix_reddit_sources_subreddit", "reddit_sources", ["subreddit"])
    op.create_index("ix_reddit_sources_site_sub", "reddit_sources", ["site_id", "subreddit"], unique=True)

    # ── 2. reddit_question_clusters ───────────────────────────────────
    op.create_table(
        "reddit_question_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("cluster_name", sa.String(length=256), nullable=False),
        sa.Column("canonical_problem", sa.Text(), nullable=False),
        sa.Column("parent_topic", sa.String(length=256), nullable=False),
        sa.Column("subtopics", sa.JSON(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("primary_intent", sa.String(length=50), nullable=False, server_default="informational"),
        sa.Column("aggregate_momentum_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_question_clusters_site_id", "reddit_question_clusters", ["site_id"])

    # ── 3. reddit_questions ───────────────────────────────────────────
    op.create_table(
        "reddit_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("reddit_post_id", sa.String(length=50), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("author_id", sa.String(length=100), nullable=True),
        sa.Column("permalink", sa.String(length=512), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("raw_title", sa.Text(), nullable=False),
        sa.Column("raw_body", sa.Text(), nullable=True),
        sa.Column("flair", sa.String(length=100), nullable=True),
        sa.Column("reddit_score", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reddit_comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_question", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("question_type", sa.String(length=50), nullable=False, server_default="other"),
        sa.Column("primary_question", sa.Text(), nullable=False),
        sa.Column("underlying_problem", sa.Text(), nullable=True),
        sa.Column("search_intent", sa.String(length=50), nullable=False, server_default="informational"),
        sa.Column("target_audience", sa.String(length=200), nullable=True),
        sa.Column("extracted_entities", sa.JSON(), nullable=False),
        sa.Column("urgency_level", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("relevance_reasons", sa.JSON(), nullable=False),
        sa.Column("clarity_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("answerability_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="discovered"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["reddit_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["cluster_id"], ["reddit_question_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_questions_site_id", "reddit_questions", ["site_id"])
    op.create_index("ix_reddit_questions_source_id", "reddit_questions", ["source_id"])
    op.create_index("ix_reddit_questions_cluster_id", "reddit_questions", ["cluster_id"])
    op.create_index("ix_reddit_questions_reddit_post_id", "reddit_questions", ["reddit_post_id"])
    op.create_index("ix_reddit_questions_subreddit", "reddit_questions", ["subreddit"])
    op.create_index("ix_reddit_questions_question_type", "reddit_questions", ["question_type"])
    op.create_index("ix_reddit_questions_status", "reddit_questions", ["status"])
    op.create_index("ix_reddit_questions_site_post", "reddit_questions", ["site_id", "reddit_post_id"], unique=True)
    op.create_index("ix_reddit_questions_sub_date", "reddit_questions", ["subreddit", "posted_at"])

    # ── 4. reddit_community_policies ──────────────────────────────────
    op.create_table(
        "reddit_community_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("posting_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("commenting_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("external_links_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("self_promotion_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("disclosure_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("promotion_restrictions", sa.Text(), nullable=True),
        sa.Column("required_karma", sa.Integer(), nullable=True),
        sa.Column("required_account_age_days", sa.Integer(), nullable=True),
        sa.Column("rules_text", sa.Text(), nullable=True),
        sa.Column("raw_rules_json", sa.JSON(), nullable=False),
        sa.Column("rule_status", sa.String(length=50), nullable=False, server_default="verified"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["reddit_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_community_policies_site_id", "reddit_community_policies", ["site_id"])
    op.create_index("ix_reddit_community_policies_source_id", "reddit_community_policies", ["source_id"])
    op.create_index("ix_reddit_community_policies_subreddit", "reddit_community_policies", ["subreddit"])
    op.create_index("ix_reddit_community_policy_site_sub", "reddit_community_policies", ["site_id", "subreddit"], unique=True)

    # ── 5. reddit_opportunities ───────────────────────────────────────
    op.create_table(
        "reddit_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("working_title", sa.String(length=512), nullable=False),
        sa.Column("proposed_angle", sa.Text(), nullable=False),
        sa.Column("target_keyword", sa.String(length=256), nullable=False),
        sa.Column("secondary_keywords", sa.JSON(), nullable=False),
        sa.Column("recommended_action", sa.String(length=50), nullable=False, server_default="create_new_article"),
        sa.Column("existing_article_match_id", sa.Uuid(), nullable=True),
        sa.Column("existing_article_title", sa.String(length=512), nullable=True),
        sa.Column("content_gap_summary", sa.Text(), nullable=True),
        sa.Column("website_relevance_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("recurrence_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("engagement_momentum_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("content_gap_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("search_intent_fit_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("evergreen_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("answerability_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("overall_opportunity_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("score_reasons", sa.JSON(), nullable=False),
        sa.Column("handoff_status", sa.String(length=50), nullable=False, server_default="ready_for_research"),
        sa.Column("generated_article_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="scored"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["reddit_questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cluster_id"], ["reddit_question_clusters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["existing_article_match_id"], ["published_articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_article_id"], ["published_articles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_opportunities_site_id", "reddit_opportunities", ["site_id"])
    op.create_index("ix_reddit_opportunities_question_id", "reddit_opportunities", ["question_id"])
    op.create_index("ix_reddit_opportunities_cluster_id", "reddit_opportunities", ["cluster_id"])
    op.create_index("ix_reddit_opportunities_recommended_action", "reddit_opportunities", ["recommended_action"])
    op.create_index("ix_reddit_opportunities_overall_opportunity_score", "reddit_opportunities", ["overall_opportunity_score"])
    op.create_index("ix_reddit_opportunities_handoff_status", "reddit_opportunities", ["handoff_status"])
    op.create_index("ix_reddit_opportunities_status", "reddit_opportunities", ["status"])

    # ── 6. reddit_response_drafts ─────────────────────────────────────
    op.create_table(
        "reddit_response_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=True),
        sa.Column("reddit_post_id", sa.String(length=50), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("response_type", sa.String(length=50), nullable=False, server_default="answer_only"),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("has_external_link", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("proposed_link", sa.String(length=1024), nullable=True),
        sa.Column("link_rationale", sa.Text(), nullable=True),
        sa.Column("rule_check_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rule_check_details", sa.JSON(), nullable=False),
        sa.Column("anti_spam_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("anti_spam_details", sa.JSON(), nullable=False),
        sa.Column("destination_article_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="response_drafted"),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["reddit_opportunities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_response_drafts_site_id", "reddit_response_drafts", ["site_id"])
    op.create_index("ix_reddit_response_drafts_opportunity_id", "reddit_response_drafts", ["opportunity_id"])
    op.create_index("ix_reddit_response_drafts_reddit_post_id", "reddit_response_drafts", ["reddit_post_id"])
    op.create_index("ix_reddit_response_drafts_subreddit", "reddit_response_drafts", ["subreddit"])
    op.create_index("ix_reddit_response_drafts_status", "reddit_response_drafts", ["status"])

    # ── 7. reddit_publications ────────────────────────────────────────
    op.create_table(
        "reddit_publications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("draft_id", sa.Uuid(), nullable=False),
        sa.Column("reddit_post_id", sa.String(length=50), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("workflow_id", sa.String(length=100), nullable=False),
        sa.Column("response_hash", sa.String(length=64), nullable=False),
        sa.Column("remote_comment_id", sa.String(length=50), nullable=True),
        sa.Column("remote_comment_url", sa.String(length=1024), nullable=True),
        sa.Column("final_body", sa.Text(), nullable=False),
        sa.Column("included_link", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="submitted"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_removed_by_mod", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("comment_upvotes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("child_replies_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_id"], ["reddit_response_drafts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_publications_site_id", "reddit_publications", ["site_id"])
    op.create_index("ix_reddit_publications_draft_id", "reddit_publications", ["draft_id"])
    op.create_index("ix_reddit_publications_reddit_post_id", "reddit_publications", ["reddit_post_id"])
    op.create_index("ix_reddit_publications_subreddit", "reddit_publications", ["subreddit"])
    op.create_index("ix_reddit_publications_workflow_id", "reddit_publications", ["workflow_id"], unique=True)
    op.create_index("ix_reddit_publications_response_hash", "reddit_publications", ["response_hash"])
    op.create_index("ix_reddit_publications_remote_comment_id", "reddit_publications", ["remote_comment_id"])
    op.create_index("ix_reddit_publications_status", "reddit_publications", ["status"])

    # ── 8. reddit_referral_events ─────────────────────────────────────
    op.create_table(
        "reddit_referral_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("publication_id", sa.Uuid(), nullable=True),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("destination_url", sa.String(length=1024), nullable=False),
        sa.Column("article_slug", sa.String(length=256), nullable=False),
        sa.Column("utm_source", sa.String(length=50), nullable=False, server_default="reddit"),
        sa.Column("utm_medium", sa.String(length=50), nullable=False, server_default="community"),
        sa.Column("utm_campaign", sa.String(length=100), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=True),
        sa.Column("pageviews", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("engaged_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("converted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_id"], ["reddit_publications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reddit_referral_events_site_id", "reddit_referral_events", ["site_id"])
    op.create_index("ix_reddit_referral_events_publication_id", "reddit_referral_events", ["publication_id"])
    op.create_index("ix_reddit_referral_events_subreddit", "reddit_referral_events", ["subreddit"])
    op.create_index("ix_reddit_referral_events_article_slug", "reddit_referral_events", ["article_slug"])
    op.create_index("ix_reddit_referral_events_utm_campaign", "reddit_referral_events", ["utm_campaign"])
    op.create_index("ix_reddit_referral_events_session_id", "reddit_referral_events", ["session_id"])
    op.create_index("ix_reddit_referrals_article_time", "reddit_referral_events", ["article_slug", "occurred_at"])


def downgrade() -> None:
    op.drop_table("reddit_referral_events")
    op.drop_table("reddit_publications")
    op.drop_table("reddit_response_drafts")
    op.drop_table("reddit_opportunities")
    op.drop_table("reddit_community_policies")
    op.drop_table("reddit_questions")
    op.drop_table("reddit_question_clusters")
    op.drop_table("reddit_sources")
