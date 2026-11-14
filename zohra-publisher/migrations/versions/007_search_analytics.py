"""Search Analytics, Indexing Intelligence & Performance Diagnostics: Part 8 models.

Revision ID: 007_search_analytics
Revises: 006_publishing_engine
Create Date: 2026-10-02 12:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "007_search_analytics"
down_revision = "006_publishing_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. search_console_properties ──────────────────────────────────
    op.create_table(
        "search_console_properties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("property_uri", sa.String(length=1024), nullable=False),
        sa.Column("property_type", sa.String(length=64), nullable=False, server_default="URL"),
        sa.Column("credential_ref", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("analytics_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("inspection_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("circuit_breaker_open", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("circuit_open_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "property_uri", name="uq_gsc_prop_site_uri"),
    )
    op.create_index("ix_gsc_prop_site", "search_console_properties", ["site_id"])
    op.create_index("ix_gsc_prop_uri", "search_console_properties", ["property_uri"])
    op.create_index("ix_gsc_prop_site_enabled", "search_console_properties", ["site_id", "enabled"])

    # ── 2. analytics_ingestion_profiles ───────────────────────────────
    op.create_table(
        "analytics_ingestion_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("date_lag_days", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("row_limit_strategy", sa.String(length=64), nullable=False, server_default="PAGINATED_MAX_25000"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_analytics_profile_name"),
    )

    # ── 3. analytics_ingestion_runs ───────────────────────────────────
    op.create_table(
        "analytics_ingestion_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_dimensions", sa.JSON(), nullable=False),
        sa.Column("rows_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("provider_request_reference", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["search_console_properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["analytics_ingestion_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_run_prop", "analytics_ingestion_runs", ["property_id"])
    op.create_index("ix_ingest_run_prop_date", "analytics_ingestion_runs", ["property_id", "start_date", "end_date"])

    # ── 4. search_analytics_raw ───────────────────────────────────────
    op.create_table(
        "search_analytics_raw",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("page", sa.String(length=2048), nullable=True),
        sa.Column("query", sa.String(length=1024), nullable=True),
        sa.Column("country", sa.String(length=16), nullable=True),
        sa.Column("device", sa.String(length=32), nullable=True),
        sa.Column("search_appearance", sa.String(length=64), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("position", sa.Float(), nullable=True),
        sa.Column("raw_dimensions_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["analytics_ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["search_console_properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_raw_prop_date_page", "search_analytics_raw", ["property_id", "date", "page"])
    op.create_index("ix_raw_query", "search_analytics_raw", ["query"])

    # ── 5. page_daily_metrics ─────────────────────────────────────────
    op.create_table(
        "page_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("published_article_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("data_finality_status", sa.String(length=32), nullable=False, server_default="FINAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_article_id"], ["published_articles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "url", "date", name="uq_page_daily_site_url_date"),
    )
    op.create_index("ix_pdm_site_date", "page_daily_metrics", ["site_id", "date"])
    op.create_index("ix_pdm_art_date", "page_daily_metrics", ["article_id", "date"])

    # ── 6. query_daily_metrics ────────────────────────────────────────
    op.create_table(
        "query_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("query", sa.String(length=1024), nullable=False),
        sa.Column("normalized_query", sa.String(length=1024), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("data_finality_status", sa.String(length=32), nullable=False, server_default="FINAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "normalized_query", "date", name="uq_query_daily_site_query_date"),
    )
    op.create_index("ix_qdm_site_date", "query_daily_metrics", ["site_id", "date"])

    # ── 7. page_query_daily_metrics ───────────────────────────────────
    op.create_table(
        "page_query_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("normalized_url", sa.String(length=2048), nullable=False),
        sa.Column("query", sa.String(length=1024), nullable=False),
        sa.Column("normalized_query", sa.String(length=1024), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("data_finality_status", sa.String(length=32), nullable=False, server_default="FINAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "url", "normalized_query", "date", name="uq_page_query_daily_site_url_q_date"),
    )
    op.create_index("ix_pqdm_site_art_date", "page_query_daily_metrics", ["site_id", "article_id", "date"])
    op.create_index("ix_pqdm_site_norm_q", "page_query_daily_metrics", ["site_id", "normalized_query"])

    # ── 8. page_country_daily_metrics ─────────────────────────────────
    op.create_table(
        "page_country_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("country", sa.String(length=16), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "url", "country", "date", name="uq_page_country_daily_site_url_c_date"),
    )

    # ── 9. page_device_daily_metrics ──────────────────────────────────
    op.create_table(
        "page_device_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("device", sa.String(length=32), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "url", "device", "date", name="uq_page_device_daily_site_url_d_date"),
    )

    # ── 10. site_daily_metrics ────────────────────────────────────────
    op.create_table(
        "site_daily_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("ranking_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranking_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("data_finality_status", sa.String(length=32), nullable=False, server_default="FINAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "date", name="uq_site_daily_metrics_site_date"),
    )

    # ── 11. indexing_status_history ───────────────────────────────────
    op.create_table(
        "indexing_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="GOOGLE_SEARCH_CONSOLE"),
        sa.Column("coverage_state", sa.String(length=128), nullable=True),
        sa.Column("robots_state", sa.String(length=64), nullable=True),
        sa.Column("canonical_state", sa.String(length=64), nullable=True),
        sa.Column("provider_canonical", sa.String(length=2048), nullable=True),
        sa.Column("user_canonical", sa.String(length=2048), nullable=True),
        sa.Column("last_crawl_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diagnostic_issue", sa.String(length=64), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_idx_hist_site_url", "indexing_status_history", ["site_id", "url"])

    # ── 12. query_alignment_records ───────────────────────────────────
    op.create_table(
        "query_alignment_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=1024), nullable=False),
        sa.Column("target_keyword", sa.String(length=512), nullable=False),
        sa.Column("alignment_score", sa.Float(), nullable=False),
        sa.Column("intent_match", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unexpected_query", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("outcome", sa.String(length=32), nullable=False, server_default="ALIGNED"),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qar_site_art", "query_alignment_records", ["site_id", "article_id"])

    # ── 13. query_clusters & query_cluster_members ────────────────────
    op.create_table(
        "query_clusters",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=512), nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=False, server_default="INFORMATIONAL"),
        sa.Column("centroid_embedding", sa.JSON(), nullable=True),
        sa.Column("total_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "query_cluster_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("query", sa.String(length=1024), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["query_clusters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_qcm_cluster_query", "query_cluster_members", ["cluster_id", "query"])

    # ── 14. ctr_benchmarks ────────────────────────────────────────────
    op.create_table(
        "ctr_benchmarks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("segment_type", sa.String(length=64), nullable=False),
        sa.Column("segment_value", sa.String(length=128), nullable=False),
        sa.Column("position_band", sa.String(length=32), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_ctr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("median_ctr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p25_ctr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("p75_ctr", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "segment_type", "segment_value", "period_start", "period_end", name="uq_ctr_benchmark_segment"),
    )
    op.create_index("ix_ctr_bench_site_seg", "ctr_benchmarks", ["site_id", "segment_type", "segment_value"])

    # ── 15. article_performance_snapshots ─────────────────────────────
    op.create_table(
        "article_performance_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("published_article_id", sa.Uuid(), nullable=True),
        sa.Column("window", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("query_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_query", sa.String(length=1024), nullable=True),
        sa.Column("top_country", sa.String(length=16), nullable=True),
        sa.Column("top_device", sa.String(length=32), nullable=True),
        sa.Column("first_impression_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_click_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visibility_trend", sa.String(length=32), nullable=True),
        sa.Column("click_trend", sa.Float(), nullable=True),
        sa.Column("impression_trend", sa.Float(), nullable=True),
        sa.Column("position_trend", sa.Float(), nullable=True),
        sa.Column("days_since_publication", sa.Integer(), nullable=True),
        sa.Column("lifecycle_stage", sa.String(length=32), nullable=False, server_default="NEW"),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("primary_topic", sa.String(length=255), nullable=True),
        sa.Column("zohra_visibility_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_article_id"], ["published_articles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "article_id", "window", "period_end", name="uq_article_perf_site_art_win_end"),
    )
    op.create_index("ix_art_perf_site_win_end", "article_performance_snapshots", ["site_id", "window", "period_end"])

    # ── 16. topic_performance_snapshots ───────────────────────────────
    op.create_table(
        "topic_performance_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("window", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("article_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("query_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("topical_authority_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "topic", "window", "period_end", name="uq_topic_perf_site_topic_win_end"),
    )

    # ── 17. site_performance_snapshots ────────────────────────────────
    op.create_table(
        "site_performance_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window", sa.String(length=32), nullable=False, server_default="28d"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=True),
        sa.Column("avg_position", sa.Float(), nullable=True),
        sa.Column("ranking_pages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ranking_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_pages_with_impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_with_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visibility_trend_7d", sa.String(length=32), nullable=True),
        sa.Column("visibility_trend_28d", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "date", "window", name="uq_site_perf_site_date_win"),
    )

    # ── 18. search_cannibalization_events ─────────────────────────────
    op.create_table(
        "search_cannibalization_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("query_cluster_id", sa.Uuid(), nullable=True),
        sa.Column("query", sa.String(length=1024), nullable=False),
        sa.Column("article_ids", sa.JSON(), nullable=False),
        sa.Column("primary_article_id", sa.Uuid(), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ownership_switch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DETECTED"),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_cluster_id"], ["query_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 19. analytics_anomalies ───────────────────────────────────────
    op.create_table(
        "analytics_anomalies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("observed_value", sa.Float(), nullable=False),
        sa.Column("absolute_change", sa.Float(), nullable=False),
        sa.Column("percentage_change", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("possible_scope", sa.String(length=64), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 20. performance_opportunities ─────────────────────────────────
    op.create_table(
        "performance_opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_type", sa.String(length=64), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("observed_problem", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("current_metrics_json", sa.JSON(), nullable=True),
        sa.Column("comparison_metrics_json", sa.JSON(), nullable=True),
        sa.Column("affected_queries_json", sa.JSON(), nullable=True),
        sa.Column("affected_query_clusters_json", sa.JSON(), nullable=True),
        sa.Column("indexing_context_json", sa.JSON(), nullable=True),
        sa.Column("article_age", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=64), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("possible_causes_json", sa.JSON(), nullable=True),
        sa.Column("recommended_investigation_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING_PART9"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", name="uq_perf_opp_candidate_id"),
    )
    op.create_index("ix_perf_opp_priority", "performance_opportunities", ["priority_score"])

    # ── 21. performance_annotations ───────────────────────────────────
    op.create_table(
        "performance_annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("annotation_type", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("related_entity_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 22. analytics_watermarks ──────────────────────────────────────
    op.create_table(
        "analytics_watermarks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("last_successful_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["property_id"], ["search_console_properties.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["analytics_ingestion_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("property_id", "profile_id", name="uq_watermark_prop_profile"),
    )

    # ── 23. performance_success_profiles ──────────────────────────────
    op.create_table(
        "performance_success_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("evaluation_age_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("min_impressions", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("min_clicks", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_avg_position", sa.Float(), nullable=True, server_default="20.0"),
        sa.Column("optional_business_metric", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "content_type", name="uq_success_prof_site_type"),
    )

    # ── 24. article_revenue_daily ─────────────────────────────────────
    op.create_table(
        "article_revenue_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revenue_source", sa.String(length=64), nullable=False),
        sa.Column("revenue", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("attribution_method", sa.String(length=64), nullable=False, server_default="LAST_TOUCH"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rev_art_date", "article_revenue_daily", ["article_id", "date"])

    # ── 25. article_economics_snapshots ───────────────────────────────
    op.create_table(
        "article_economics_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("period", sa.String(length=32), nullable=False),
        sa.Column("search_clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attributed_revenue", sa.Float(), nullable=True),
        sa.Column("ai_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("publication_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("known_cost_total", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("revenue_minus_known_cost", sa.Float(), nullable=True),
        sa.Column("cost_per_search_click", sa.Float(), nullable=True),
        sa.Column("cost_per_1000_impressions", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("article_id", "period", name="uq_art_econ_art_period"),
    )


def downgrade() -> None:
    op.drop_table("article_economics_snapshots")
    op.drop_table("article_revenue_daily")
    op.drop_table("performance_success_profiles")
    op.drop_table("analytics_watermarks")
    op.drop_table("performance_annotations")
    op.drop_table("performance_opportunities")
    op.drop_table("analytics_anomalies")
    op.drop_table("search_cannibalization_events")
    op.drop_table("site_performance_snapshots")
    op.drop_table("topic_performance_snapshots")
    op.drop_table("article_performance_snapshots")
    op.drop_table("ctr_benchmarks")
    op.drop_table("query_cluster_members")
    op.drop_table("query_clusters")
    op.drop_table("query_alignment_records")
    op.drop_table("indexing_status_history")
    op.drop_table("site_daily_metrics")
    op.drop_table("page_device_daily_metrics")
    op.drop_table("page_country_daily_metrics")
    op.drop_table("page_query_daily_metrics")
    op.drop_table("query_daily_metrics")
    op.drop_table("page_daily_metrics")
    op.drop_table("search_analytics_raw")
    op.drop_table("analytics_ingestion_runs")
    op.drop_table("analytics_ingestion_profiles")
    op.drop_table("search_console_properties")
