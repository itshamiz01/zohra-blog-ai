"""
Zohra — Pydantic Schemas for Part 8 Search Analytics & Performance Intelligence.

Defines schemas for:
- Search Console property management
- Analytics ingestion profiles & runs
- Raw & normalized search metrics
- Indexing status tracking & history
- Query intelligence: normalization, intent classification, alignment, clustering
- Ranking intelligence: position bands, volatility, opportunities
- CTR diagnostics with empirical site benchmarks
- Article / topic / site multi-window performance snapshots
- Anomaly & cannibalization detection
- Performance diagnostics: observed vs. hypothesized
- OptimizationCandidatePackage for Part 9 handoff
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Enums ────────────────────────────────────────────────────────────

class GSCPropertyType(str, Enum):
    URL = "URL"
    DOMAIN = "DOMAIN"


class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class IndexingStatus(str, Enum):
    INDEXED = "INDEXED"
    NOT_INDEXED = "NOT_INDEXED"
    CRAWLED_NOT_INDEXED = "CRAWLED_NOT_INDEXED"
    DISCOVERED_NOT_CRAWLED = "DISCOVERED_NOT_CRAWLED"
    BLOCKED_BY_ROBOTS = "BLOCKED_BY_ROBOTS"
    EXCLUDED_CANONICAL = "EXCLUDED_CANONICAL"
    EXCLUDED_NOINDEX = "EXCLUDED_NOINDEX"
    REDIRECT = "REDIRECT"
    UNKNOWN = "UNKNOWN"


class SearchIntent(str, Enum):
    INFORMATIONAL = "INFORMATIONAL"
    NAVIGATIONAL = "NAVIGATIONAL"
    TRANSACTIONAL = "TRANSACTIONAL"
    COMMERCIAL = "COMMERCIAL"
    LOCAL = "LOCAL"
    AMBIGUOUS = "AMBIGUOUS"


class PositionBand(str, Enum):
    TOP_1 = "TOP_1"
    TOP_3 = "TOP_3"
    TOP_5 = "TOP_5"
    TOP_10 = "TOP_10"
    PAGE_2 = "PAGE_2"
    PAGE_3_PLUS = "PAGE_3_PLUS"
    NOT_RANKING = "NOT_RANKING"


class AnomalySeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyScope(str, Enum):
    PAGE_SPECIFIC = "PAGE_SPECIFIC"
    TOPIC_SPECIFIC = "TOPIC_SPECIFIC"
    SITE_WIDE = "SITE_WIDE"
    EXTERNAL_ALGORITHMIC = "EXTERNAL_ALGORITHMIC"


class OpportunityCandidateType(str, Enum):
    LOW_CTR = "LOW_CTR"
    PAGE_2_OPPORTUNITY = "PAGE_2_OPPORTUNITY"
    NEAR_TOP_3 = "NEAR_TOP_3"
    DECLINING_TRAFFIC = "DECLINING_TRAFFIC"
    CANNIBALIZATION = "CANNIBALIZATION"
    NOT_INDEXED = "NOT_INDEXED"
    STALE_CONTENT = "STALE_CONTENT"
    QUERY_MISMATCH = "QUERY_MISMATCH"
    TOPIC_AUTHORITY_GAP = "TOPIC_AUTHORITY_GAP"


class OpportunityStatus(str, Enum):
    PENDING_PART9 = "PENDING_PART9"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    SUPERSEDED = "SUPERSEDED"


class LifecycleStage(str, Enum):
    NEW = "NEW"
    RAMPING = "RAMPING"
    ESTABLISHED = "ESTABLISHED"
    MATURE = "MATURE"
    DECLINING = "DECLINING"
    DORMANT = "DORMANT"


class VisibilityTrend(str, Enum):
    RISING = "RISING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"
    VOLATILE = "VOLATILE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DataFinalityStatus(str, Enum):
    PRELIMINARY = "PRELIMINARY"
    FINAL = "FINAL"


# ── Search Console Properties ────────────────────────────────────────

class SearchConsolePropertyCreate(BaseModel):
    site_id: uuid.UUID
    property_uri: str = Field(max_length=1024)
    property_type: GSCPropertyType = GSCPropertyType.URL
    credential_ref: str | None = None
    default_timezone: str = "UTC"

    model_config = ConfigDict(from_attributes=True)


class SearchConsolePropertyResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    property_uri: str
    property_type: str
    credential_ref: str | None = None
    enabled: bool
    analytics_enabled: bool
    inspection_enabled: bool
    default_timezone: str
    last_successful_sync_at: datetime | None = None
    last_failed_sync_at: datetime | None = None
    consecutive_failures: int
    circuit_breaker_open: bool
    circuit_open_until: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Ingestion Profiles ───────────────────────────────────────────────

class IngestionProfileCreate(BaseModel):
    name: str = Field(max_length=64)
    dimensions: list[str] = Field(default_factory=list)
    date_lag_days: int = 2
    lookback_days: int = 3
    row_limit_strategy: str = "PAGINATED_MAX_25000"
    enabled: bool = True
    priority: int = 10


class IngestionProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    dimensions: list[str]
    date_lag_days: int
    lookback_days: int
    row_limit_strategy: str
    enabled: bool
    priority: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Ingestion Runs ───────────────────────────────────────────────────

class IngestionRunResponse(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    profile_id: uuid.UUID
    start_date: datetime
    end_date: datetime
    requested_dimensions: list[str]
    rows_received: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Search Metrics ───────────────────────────────────────────────────

class SearchMetrics(BaseModel):
    """Reusable block for clicks/impressions/ctr/position."""
    clicks: int = 0
    impressions: int = 0
    ctr: float | None = None
    avg_position: float | None = None


class PageDailyMetricResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID | None = None
    published_article_id: uuid.UUID | None = None
    date: datetime
    url: str
    normalized_url: str
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None
    data_finality_status: str

    model_config = ConfigDict(from_attributes=True)


class QueryDailyMetricResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    date: datetime
    query: str
    normalized_query: str
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None
    intent: str | None = None
    data_finality_status: str

    model_config = ConfigDict(from_attributes=True)


class PageQueryDailyMetricResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID | None = None
    date: datetime
    url: str
    query: str
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None

    model_config = ConfigDict(from_attributes=True)


class SiteDailyMetricResponse(BaseModel):
    site_id: uuid.UUID
    date: datetime
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None
    ranking_pages: int
    ranking_queries: int

    model_config = ConfigDict(from_attributes=True)


# ── Indexing Status ──────────────────────────────────────────────────

class IndexingStatusResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID | None = None
    url: str
    checked_at: datetime
    status: str
    provider: str
    coverage_state: str | None = None
    robots_state: str | None = None
    canonical_state: str | None = None
    provider_canonical: str | None = None
    user_canonical: str | None = None
    last_crawl_time: datetime | None = None
    diagnostic_issue: str | None = None
    details_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class IndexingDiagnostic(BaseModel):
    """Evaluated diagnostic summary for a URL's indexing health."""
    url: str
    current_status: str
    history_count: int
    days_since_publish: int | None = None
    days_since_first_crawl: int | None = None
    canonical_mismatch: bool = False
    robots_blocked: bool = False
    diagnostic_issues: list[str] = Field(default_factory=list)
    recommendation: str | None = None


# ── Query Intelligence ───────────────────────────────────────────────

class QueryAlignmentResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID
    query: str
    target_keyword: str
    alignment_score: float
    intent_match: bool
    unexpected_query: bool
    outcome: str

    model_config = ConfigDict(from_attributes=True)


class QueryClusterResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    label: str
    intent: str
    total_clicks: int
    total_impressions: int
    avg_position: float | None = None
    member_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class QueryClassificationResult(BaseModel):
    """Result of intent classification for a search query."""
    query: str
    normalized_query: str
    intent: SearchIntent
    confidence: float = 0.5
    is_branded: bool = False
    word_count: int = 0


# ── CTR Diagnostics ─────────────────────────────────────────────────

class CTRBenchmarkResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    segment_type: str
    segment_value: str
    position_band: str | None = None
    sample_size: int
    avg_ctr: float
    median_ctr: float
    p25_ctr: float
    p75_ctr: float
    period_start: datetime
    period_end: datetime

    model_config = ConfigDict(from_attributes=True)


class CTRDiagnosticResult(BaseModel):
    """CTR performance relative to internal site benchmark."""
    url: str
    article_id: uuid.UUID | None = None
    position_band: str
    actual_ctr: float | None
    benchmark_avg_ctr: float
    benchmark_median_ctr: float
    ctr_ratio: float | None = None  # actual / benchmark
    underperforming: bool = False
    impressions: int = 0
    sample_size_sufficient: bool = True


# ── Position & Ranking Intelligence ──────────────────────────────────

class RankingSnapshot(BaseModel):
    """Single point-in-time ranking data for a URL+query pair."""
    url: str
    query: str
    position: float | None
    position_band: PositionBand
    clicks: int = 0
    impressions: int = 0


class RankingTrend(BaseModel):
    """Trend calculation over two comparison windows."""
    url: str
    query: str | None = None
    current_position: float | None = None
    previous_position: float | None = None
    position_delta: float | None = None
    current_clicks: int = 0
    previous_clicks: int = 0
    click_change_pct: float | None = None
    trend: VisibilityTrend = VisibilityTrend.INSUFFICIENT_DATA


class Page2Opportunity(BaseModel):
    """Article ranking on page 2 that may benefit from optimization."""
    article_id: uuid.UUID
    url: str
    query: str
    avg_position: float
    impressions: int
    clicks: int
    estimated_position_to_page1: float


class NearTopOpportunity(BaseModel):
    """Article ranking in positions 4-10 with potential for top-3 advancement."""
    article_id: uuid.UUID
    url: str
    query: str
    avg_position: float
    impressions: int
    clicks: int
    distance_to_top3: float


# ── Performance Snapshots ────────────────────────────────────────────

class ArticlePerformanceSnapshotResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID
    published_article_id: uuid.UUID | None = None
    window: str
    period_start: datetime
    period_end: datetime
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None
    query_count: int
    top_query: str | None = None
    top_country: str | None = None
    top_device: str | None = None
    first_impression_at: datetime | None = None
    first_click_at: datetime | None = None
    visibility_trend: str | None = None
    click_trend: float | None = None
    impression_trend: float | None = None
    position_trend: float | None = None
    days_since_publication: int | None = None
    lifecycle_stage: str
    content_type: str | None = None
    primary_topic: str | None = None
    zohra_visibility_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class TopicPerformanceSnapshotResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    topic: str
    window: str
    period_start: datetime
    period_end: datetime
    article_count: int
    query_count: int
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None
    topical_authority_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class SitePerformanceSnapshotResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    date: datetime
    window: str
    clicks: int
    impressions: int
    ctr: float | None = None
    avg_position: float | None = None
    ranking_pages: int
    ranking_queries: int
    new_pages_with_impressions: int
    pages_with_clicks: int
    visibility_trend_7d: str | None = None
    visibility_trend_28d: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Anomaly Detection ────────────────────────────────────────────────

class AnomalyResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID | None = None
    metric: str
    baseline_value: float
    observed_value: float
    absolute_change: float
    percentage_change: float
    severity: str
    confidence: float
    possible_scope: str
    details_json: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ── Cannibalization Detection ────────────────────────────────────────

class CannibalizationEventResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    query_cluster_id: uuid.UUID | None = None
    query: str
    article_ids: list[str]
    primary_article_id: uuid.UUID | None = None
    impressions: int
    clicks: int
    ownership_switch_count: int
    confidence: float
    status: str
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Performance Diagnostics ──────────────────────────────────────────

class PerformanceDiagnostic(BaseModel):
    """Structured diagnostic: observation vs. inference, clearly separated."""
    article_id: uuid.UUID
    observed_facts: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    data_quality_caveats: list[str] = Field(default_factory=list)
    confidence_level: str = "LOW"
    summary: str = ""


# ── OptimizationCandidatePackage for Part 9 Handoff ─────────────────

class OptimizationCandidatePackage(BaseModel):
    """Immutable package describing a performance opportunity for Part 9."""
    candidate_id: str
    site_id: uuid.UUID
    article_id: uuid.UUID
    candidate_type: OpportunityCandidateType
    priority_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    observed_problem: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    current_metrics: SearchMetrics | None = None
    comparison_metrics: SearchMetrics | None = None
    affected_queries: list[str] = Field(default_factory=list)
    affected_query_clusters: list[str] = Field(default_factory=list)
    indexing_context: dict[str, Any] | None = None
    article_age: int | None = None
    content_type: str | None = None
    topic: str | None = None
    possible_causes: list[str] = Field(default_factory=list)
    recommended_investigation: list[str] = Field(default_factory=list)
    status: OpportunityStatus = OpportunityStatus.PENDING_PART9


class PerformanceOpportunityResponse(BaseModel):
    id: uuid.UUID
    candidate_id: str
    site_id: uuid.UUID
    article_id: uuid.UUID
    candidate_type: str
    priority_score: float
    confidence: float
    observed_problem: str
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    current_metrics_json: dict[str, Any] | None = None
    comparison_metrics_json: dict[str, Any] | None = None
    affected_queries_json: list[str] | None = None
    article_age: int | None = None
    content_type: str | None = None
    topic: str | None = None
    possible_causes_json: list[str] | None = None
    recommended_investigation_json: list[str] | None = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Annotations ──────────────────────────────────────────────────────

class PerformanceAnnotationCreate(BaseModel):
    site_id: uuid.UUID
    article_id: uuid.UUID | None = None
    annotation_type: str = Field(max_length=64)
    timestamp: datetime
    description: str
    related_entity_id: str | None = None


class PerformanceAnnotationResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID | None = None
    annotation_type: str
    timestamp: datetime
    description: str
    related_entity_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── API Request Schemas ──────────────────────────────────────────────

class AnalyticsSyncRequest(BaseModel):
    """Request to trigger GSC analytics ingestion."""
    property_id: uuid.UUID
    profile_names: list[str] | None = None  # None = all enabled profiles
    start_date: datetime | None = None
    end_date: datetime | None = None


class IndexingInspectionRequest(BaseModel):
    """Request to trigger URL inspection via GSC."""
    site_id: uuid.UUID
    urls: list[str] = Field(max_length=50)


class PerformanceQueryParams(BaseModel):
    """Shared query parameters for performance endpoints."""
    site_id: uuid.UUID
    window: str = "28d"
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


# ── Summary Dashboards ──────────────────────────────────────────────

class SiteAnalyticsSummary(BaseModel):
    """Quick overview of site search health."""
    site_id: uuid.UUID
    total_articles: int = 0
    indexed_articles: int = 0
    not_indexed_articles: int = 0
    total_clicks_28d: int = 0
    total_impressions_28d: int = 0
    avg_ctr_28d: float | None = None
    avg_position_28d: float | None = None
    active_anomalies: int = 0
    active_cannibalization_events: int = 0
    pending_opportunities: int = 0
    last_sync_at: datetime | None = None
