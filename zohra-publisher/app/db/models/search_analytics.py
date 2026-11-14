"""
Zohra — Search Analytics, Performance Intelligence & Indexing Models (Part 8).

Defines persistence structures for Google Search Console integration, ingestion runs,
raw & normalized search metrics, indexing status history, query intelligence & clusters,
CTR benchmarks, multi-window performance snapshots, anomaly/cannibalization detection,
and optimization candidate packages for Part 9.
"""

from __future__ import annotations

import uuid
from datetime import datetime

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


class SearchConsoleProperty(ZohraBase):
    """Google Search Console property registered to a Zohra site."""

    __tablename__ = "search_console_properties"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_uri: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    property_type: Mapped[str] = mapped_column(String(64), nullable=False, default="URL")  # URL, DOMAIN
    credential_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    inspection_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    circuit_breaker_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    circuit_open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("site_id", "property_uri", name="uq_gsc_prop_site_uri"),
        Index("ix_gsc_prop_site_enabled", "site_id", "enabled"),
    )


class AnalyticsIngestionProfile(ZohraBase):
    """Ingestion profile specifying dimension combinations and sync lag strategies."""

    __tablename__ = "analytics_ingestion_profiles"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    dimensions: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    date_lag_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    row_limit_strategy: Mapped[str] = mapped_column(String(64), nullable=False, default="PAGINATED_MAX_25000")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=10)


class AnalyticsIngestionRun(ZohraBase):
    """Tracks discrete Search Console data fetch executions."""

    __tablename__ = "analytics_ingestion_runs"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_console_properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytics_ingestion_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_dimensions: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    rows_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)
    provider_request_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ingest_run_prop_date", "property_id", "start_date", "end_date"),
    )


class SearchAnalyticsRaw(ZohraBase):
    """Audit layer for exact provider responses before downstream normalization."""

    __tablename__ = "search_analytics_raw"

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytics_ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_console_properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    page: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    query: Mapped[str | None] = mapped_column(String(1024), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    device: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    search_appearance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    position: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_dimensions_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_raw_prop_date_page", "property_id", "date", "page"),
    )


class PageDailyMetric(ZohraBase):
    """Normalized page-level search performance by day."""

    __tablename__ = "page_daily_metrics"

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
    published_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("published_articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_finality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="FINAL")

    __table_args__ = (
        UniqueConstraint("site_id", "url", "date", name="uq_page_daily_site_url_date"),
        Index("ix_pdm_site_date", "site_id", "date"),
        Index("ix_pdm_art_date", "article_id", "date"),
    )


class QueryDailyMetric(ZohraBase):
    """Normalized site-wide query search performance by day."""

    __tablename__ = "query_daily_metrics"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    query: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_query: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_finality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="FINAL")

    __table_args__ = (
        UniqueConstraint("site_id", "normalized_query", "date", name="uq_query_daily_site_query_date"),
        Index("ix_qdm_site_date", "site_id", "date"),
    )


class PageQueryDailyMetric(ZohraBase):
    """Normalized page-and-query granular search performance by day."""

    __tablename__ = "page_query_daily_metrics"

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
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    query: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_query: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_finality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="FINAL")

    __table_args__ = (
        UniqueConstraint("site_id", "url", "normalized_query", "date", name="uq_page_query_daily_site_url_q_date"),
        Index("ix_pqdm_site_art_date", "site_id", "article_id", "date"),
        Index("ix_pqdm_site_norm_q", "site_id", "normalized_query"),
    )


class PageCountryDailyMetric(ZohraBase):
    """Normalized page performance segmented by ISO country code."""

    __tablename__ = "page_country_daily_metrics"

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
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    country: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "url", "country", "date", name="uq_page_country_daily_site_url_c_date"),
    )


class PageDeviceDailyMetric(ZohraBase):
    """Normalized page performance segmented by device type."""

    __tablename__ = "page_device_daily_metrics"

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
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    device: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # DESKTOP, MOBILE, TABLET
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "url", "device", "date", name="uq_page_device_daily_site_url_d_date"),
    )


class SiteDailyMetric(ZohraBase):
    """Normalized daily rollup across the entire site."""

    __tablename__ = "site_daily_metrics"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ranking_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_finality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="FINAL")

    __table_args__ = (
        UniqueConstraint("site_id", "date", name="uq_site_daily_metrics_site_date"),
    )


class IndexingStatusHistory(ZohraBase):
    """Audit log of URL inspection and indexing evidence."""

    __tablename__ = "indexing_status_history"

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
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="GOOGLE_SEARCH_CONSOLE")
    coverage_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    robots_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_canonical: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    user_canonical: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    last_crawl_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    diagnostic_issue: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_idx_hist_site_url", "site_id", "url"),
    )


class QueryAlignmentRecord(ZohraBase):
    """Comparison between actual ranking queries and Part 3 planned target keywords."""

    __tablename__ = "query_alignment_records"

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
    query: Mapped[str] = mapped_column(String(1024), nullable=False)
    target_keyword: Mapped[str] = mapped_column(String(512), nullable=False)
    alignment_score: Mapped[float] = mapped_column(Float, nullable=False)
    intent_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unexpected_query: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="ALIGNED")
    details_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_qar_site_art", "site_id", "article_id"),
    )


class AnalyticsQueryCluster(ZohraBase):
    """Semantic cluster of search queries."""

    __tablename__ = "query_clusters"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(512), nullable=False)
    intent: Mapped[str] = mapped_column(String(64), nullable=False, default="INFORMATIONAL")
    centroid_embedding: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True)
    total_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)


class AnalyticsQueryClusterMember(ZohraBase):
    """Membership mapping of a specific query within an AnalyticsQueryCluster."""

    __tablename__ = "query_cluster_members"

    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class CTRBenchmark(ZohraBase):
    """Empirical internal site-specific CTR distributions."""

    __tablename__ = "ctr_benchmarks"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    segment_value: Mapped[str] = mapped_column(String(128), nullable=False)
    position_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    median_ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p25_ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    p75_ctr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("site_id", "segment_type", "segment_value", "period_start", "period_end", name="uq_ctr_benchmark_segment"),
        Index("ix_ctr_bench_site_seg", "site_id", "segment_type", "segment_value"),
    )


class ArticlePerformanceSnapshot(ZohraBase):
    """Rolling multi-window snapshot of an article's search visibility and momentum."""

    __tablename__ = "article_performance_snapshots"

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
    published_article_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("published_articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    window: Mapped[str] = mapped_column(String(32), nullable=False)  # 1d, 7d, 14d, 28d, 90d, lifetime
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_query: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    top_country: Mapped[str | None] = mapped_column(String(16), nullable=True)
    top_device: Mapped[str | None] = mapped_column(String(32), nullable=True)
    first_impression_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_click_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    visibility_trend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    click_trend: Mapped[float | None] = mapped_column(Float, nullable=True)
    impression_trend: Mapped[float | None] = mapped_column(Float, nullable=True)
    position_trend: Mapped[float | None] = mapped_column(Float, nullable=True)
    days_since_publication: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW")
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zohra_visibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "article_id", "window", "period_end", name="uq_article_perf_site_art_win_end"),
        Index("ix_art_perf_site_win_end", "site_id", "window", "period_end"),
    )


class TopicPerformanceSnapshot(ZohraBase):
    """Aggregate search visibility and empirical topical authority for topic clusters."""

    __tablename__ = "topic_performance_snapshots"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    window: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    query_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    topical_authority_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "topic", "window", "period_end", name="uq_topic_perf_site_topic_win_end"),
    )


class SitePerformanceSnapshot(ZohraBase):
    """Multi-day or multi-week site-wide performance rollup."""

    __tablename__ = "site_performance_snapshots"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    window: Mapped[str] = mapped_column(String(32), nullable=False, default="28d")
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Float, nullable=True)
    ranking_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ranking_queries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_pages_with_impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_with_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    visibility_trend_7d: Mapped[str | None] = mapped_column(String(32), nullable=True)
    visibility_trend_28d: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "date", "window", name="uq_site_perf_site_date_win"),
    )


class SearchCannibalizationEvent(ZohraBase):
    """Detection record where multiple pages compete for the same query/cluster."""

    __tablename__ = "search_cannibalization_events"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("query_clusters.id", ondelete="SET NULL"),
        nullable=True,
    )
    query: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    article_ids: Mapped[list] = mapped_column(JSON_FIELD, nullable=False, default=list)
    primary_article_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ownership_switch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DETECTED")
    details_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnalyticsAnomaly(ZohraBase):
    """Statistical anomaly detected against rolling historical baselines."""

    __tablename__ = "analytics_anomalies"

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
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_change: Mapped[float] = mapped_column(Float, nullable=False)
    percentage_change: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    possible_scope: Mapped[str] = mapped_column(String(64), nullable=False)  # PAGE_SPECIFIC, SITE_WIDE, etc.
    details_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PerformanceOpportunity(ZohraBase):
    """Part 8 prioritized diagnostic opportunity handed off to Part 9."""

    __tablename__ = "performance_opportunities"

    candidate_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
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
    priority_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    observed_problem: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON_FIELD, nullable=False, default=dict)
    current_metrics_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    comparison_metrics_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    affected_queries_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)
    affected_query_clusters_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)
    indexing_context_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)
    article_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    possible_causes_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)
    recommended_investigation_json: Mapped[list | None] = mapped_column(JSON_FIELD, nullable=True, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_PART9", index=True)


class PerformanceAnnotation(ZohraBase):
    """Chronological event marker explaining future organic performance movements."""

    __tablename__ = "performance_annotations"

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
    annotation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class AnalyticsWatermark(ZohraBase):
    """Tracks the high-watermark sync dates per property and ingestion profile."""

    __tablename__ = "analytics_watermarks"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("search_console_properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analytics_ingestion_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_successful_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempted_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("property_id", "profile_id", name="uq_watermark_prop_profile"),
    )


class PerformanceSuccessProfile(ZohraBase):
    """Site-configurable evaluation criteria defining what constitutes content success."""

    __tablename__ = "performance_success_profiles"

    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    min_impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    min_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_avg_position: Mapped[float | None] = mapped_column(Float, nullable=True, default=20.0)
    optional_business_metric: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    __table_args__ = (
        UniqueConstraint("site_id", "content_type", name="uq_success_prof_site_type"),
    )


class ArticleRevenueDaily(ZohraBase):
    """Optional revenue attribution layer."""

    __tablename__ = "article_revenue_daily"

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
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revenue_source: Mapped[str] = mapped_column(String(64), nullable=False)  # ADSENSE, AFFILIATE, ECOMMERCE, MANUAL
    revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    attribution_method: Mapped[str] = mapped_column(String(64), nullable=False, default="LAST_TOUCH")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class ArticleEconomicsSnapshot(ZohraBase):
    """Article revenue, generation cost, and AI contribution margin."""

    __tablename__ = "article_economics_snapshots"

    article_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    period: Mapped[str] = mapped_column(String(32), nullable=False)  # 28d, lifetime
    search_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attributed_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    publication_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    known_cost_total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    revenue_minus_known_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_per_search_click: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_per_1000_impressions: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("article_id", "period", name="uq_art_econ_art_period"),
    )
