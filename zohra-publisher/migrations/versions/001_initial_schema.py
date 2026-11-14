"""Initial schema: Part 1 foundation + Part 2 Discovery & Trend Engine models.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-02 01:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── PART 1: Core Foundation Tables ─────────────────────────────

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="editor"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )

    # agent_executions
    op.create_table(
        "agent_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # cost_logs
    op.create_table(
        "cost_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("agent_execution_id", sa.Uuid(), nullable=True),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_execution_id"], ["agent_executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # system_settings
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=50), nullable=False, server_default="string"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # ── PART 2: Discovery & Intelligence Engine Tables ─────────────

    # sources
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=1024), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="rss"),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=10), nullable=True, server_default="global"),
        sa.Column("language", sa.String(length=10), nullable=True, server_default="en"),
        sa.Column("authority_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("polling_interval_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_authentication", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("robots_policy_checked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("health_status", sa.String(length=50), nullable=False, server_default="healthy"),
        sa.Column("circuit_state", sa.String(length=50), nullable=False, server_default="closed"),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average_response_time_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_url"),
    )
    op.create_index("ix_sources_domain", "sources", ["domain"])
    op.create_index("ix_sources_is_enabled", "sources", ["is_enabled"])
    op.create_index("ix_sources_category", "sources", ["category"])
    op.create_index("ix_sources_tier", "sources", ["tier"])

    # source_documents
    op.create_table(
        "source_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("language_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="global"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("title_hash", sa.String(length=64), nullable=False),
        sa.Column("simhash", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="rss"),
        sa.Column("http_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("fetch_status", sa.String(length=50), nullable=False, server_default="success"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_exact_duplicate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_near_duplicate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["duplicate_of_id"], ["source_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_documents_source_id", "source_documents", ["source_id"])
    op.create_index("ix_source_documents_canonical_url", "source_documents", ["canonical_url"])
    op.create_index("ix_source_documents_content_hash", "source_documents", ["content_hash"])
    op.create_index("ix_source_documents_published_at", "source_documents", ["published_at"])
    op.create_index("ix_source_documents_discovered_at", "source_documents", ["discovered_at"])

    # entities
    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("canonical_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_index("ix_entities_normalized_name", "entities", ["normalized_name"])
    op.create_index("ix_entities_entity_type", "entities", ["entity_type"])

    # document_entities
    op.create_table(
        "document_entities",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("mentions", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "entity_id"),
    )

    # events
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_title", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("primary_category", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False, server_default="unknown"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="emerging"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("authority_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("freshness_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("velocity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("momentum_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_diversity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("trend_classification", sa.String(length=50), nullable=False, server_default="noise"),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="global"),
        sa.Column("primary_entity_id", sa.Uuid(), nullable=True),
        sa.Column("primary_source_document_id", sa.Uuid(), nullable=True),
        sa.Column("risk_flags", sa.JSON(), nullable=True),
        sa.Column("high_verification_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("contradiction_detected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("contradiction_notes", sa.JSON(), nullable=True),
        sa.Column("is_qualified_for_opportunity", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("trend_reasons", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["primary_entity_id"], ["entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["primary_source_document_id"], ["source_documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_primary_category", "events", ["primary_category"])
    op.create_index("ix_events_first_seen_at", "events", ["first_seen_at"])
    op.create_index("ix_events_last_seen_at", "events", ["last_seen_at"])
    op.create_index("ix_events_trend_score", "events", ["trend_score"])
    op.create_index("ix_events_confidence_score", "events", ["confidence_score"])
    op.create_index("ix_events_qualified", "events", ["is_qualified_for_opportunity"])

    # event_documents
    op.create_table(
        "event_documents",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_primary_source", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_original_report", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["source_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "document_id"),
    )

    # event_snapshots
    op.create_table(
        "event_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("velocity_score", sa.Float(), nullable=False),
        sa.Column("momentum_score", sa.Float(), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_snapshots_event_id", "event_snapshots", ["event_id"])
    op.create_index("ix_event_snapshots_timestamp", "event_snapshots", ["timestamp"])

    # discovery_queries
    op.create_table(
        "discovery_queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("country", sa.String(length=10), nullable=False, server_default="global"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("interval_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average_results", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("query"),
    )


def downgrade() -> None:
    # Drop Part 2
    op.drop_table("discovery_queries")
    op.drop_table("event_snapshots")
    op.drop_table("event_documents")
    op.drop_table("events")
    op.drop_table("document_entities")
    op.drop_table("entities")
    op.drop_table("source_documents")
    op.drop_table("sources")

    # Drop Part 1
    op.drop_table("system_settings")
    op.drop_table("audit_logs")
    op.drop_table("cost_logs")
    op.drop_table("agent_executions")
    op.drop_table("jobs")
    op.drop_table("users")
