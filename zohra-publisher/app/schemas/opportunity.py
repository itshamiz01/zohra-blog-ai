"""
Zohra — Pydantic schemas for Part 3:
Content Opportunity Intelligence Engine, Search Intent, Keywords, SERPs,
Competition, Content Gaps, Cannibalization & Part 4 Handoff.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    AnalysisDepth,
    ClusterRole,
    ContentAction,
    ContentType,
    FreshnessDecayType,
    OpportunityClassification,
    OpportunityDependencyStatus,
    OpportunityStatus,
    SearchIntent,
    SERPResultType,
)

# ============================================================================
# SITE SCHEMAS
# ============================================================================


class SiteBase(BaseModel):
    name: str = Field(..., max_length=255)
    domain: str = Field(..., max_length=255)
    default_language: str = Field(default="en", max_length=10)
    primary_country: str = Field(default="global", max_length=50)
    niche: str = Field(..., max_length=255)
    description: str | None = None
    target_audiences: list[str] = Field(default_factory=list)
    enabled: bool = True
    config_json: dict[str, Any] = Field(default_factory=dict)


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: str | None = None
    niche: str | None = None
    description: str | None = None
    target_audiences: list[str] | None = None
    enabled: bool | None = None
    config_json: dict[str, Any] | None = None


class SiteResponse(SiteBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SiteTopicBase(BaseModel):
    topic_name: str = Field(..., max_length=255)
    canonical_slug: str = Field(..., max_length=255)
    relevance_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    topical_authority_score: float = Field(default=50.0, ge=0.0, le=100.0)
    historical_post_count: int = Field(default=0, ge=0)


class SiteTopicCreate(SiteTopicBase):
    site_id: UUID


class SiteTopicResponse(SiteTopicBase):
    id: UUID
    site_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SiteContentBase(BaseModel):
    url: str = Field(..., max_length=2048)
    slug: str = Field(..., max_length=512)
    title: str = Field(..., max_length=1024)
    summary: str | None = None
    external_post_id: str | None = None
    primary_topic: str | None = None
    primary_keyword: str | None = None
    secondary_keywords: list[str] = Field(default_factory=list)
    primary_intent: SearchIntent | str | None = None
    language: str = "en"
    country: str = "global"
    status: str = "published"
    performance_json: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SiteContentCreate(SiteContentBase):
    site_id: UUID


class SiteContentResponse(SiteContentBase):
    id: UUID
    site_id: UUID
    published_at: datetime | None = None
    last_modified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# KEYWORD & CLUSTER SCHEMAS
# ============================================================================


class KeywordBase(BaseModel):
    keyword: str = Field(..., max_length=512)
    normalized_keyword: str = Field(..., max_length=512)
    language: str = Field(default="en", max_length=10)
    country: str = Field(default="global", max_length=50)
    intent: SearchIntent = SearchIntent.INFORMATIONAL
    intent_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    secondary_intent: SearchIntent | None = None
    search_demand_score: float = Field(default=50.0, ge=0.0, le=100.0)

    # EXTERNAL METRICS - NULL if unavailable. Never fabricate 0.
    search_volume: int | None = None
    search_volume_source: str | None = None
    search_volume_confidence: float | None = None

    competition_metric: float | None = None
    competition_source: str | None = None

    cpc: float | None = None
    cpc_currency: str | None = None
    cpc_source: str | None = None

    trend_direction: str = "unknown"
    freshness_sensitivity: FreshnessDecayType = FreshnessDecayType.EVERGREEN
    commercial_value_score: float = Field(default=0.0, ge=0.0, le=100.0)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class KeywordCreate(KeywordBase):
    pass


class KeywordResponse(KeywordBase):
    id: UUID
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KeywordClusterMemberResponse(BaseModel):
    id: UUID
    cluster_id: UUID
    keyword_id: UUID
    is_primary: bool
    similarity_score: float
    keyword: KeywordResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class KeywordClusterBase(BaseModel):
    canonical_topic: str = Field(..., max_length=512)
    primary_keyword: str = Field(..., max_length=512)
    primary_intent: SearchIntent = SearchIntent.INFORMATIONAL
    language: str = "en"
    country: str = "global"
    keyword_count: int = 1
    aggregate_demand_score: float = 50.0
    commercial_value_score: float = 0.0
    freshness_score: float = 50.0
    cluster_confidence: float = 1.0


class KeywordClusterResponse(KeywordClusterBase):
    id: UUID
    members: list[KeywordClusterMemberResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SERP SCHEMAS
# ============================================================================


class SERPResultItem(BaseModel):
    position: int
    url: str
    domain: str
    title: str
    snippet: str | None = None
    result_type: SERPResultType = SERPResultType.ORGANIC
    published_date: datetime | None = None
    is_official_domain: bool = False
    is_forum: bool = False
    features: dict[str, Any] = Field(default_factory=dict)


class SERPResultResponse(SERPResultItem):
    id: UUID
    snapshot_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SERPSnapshotResponse(BaseModel):
    id: UUID
    query: str
    query_hash: str
    provider: str
    country: str
    language: str
    device: str
    total_results_estimate: int | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    dominant_intent: SearchIntent
    intent_alignment_score: float
    retrieved_at: datetime
    expires_at: datetime | None = None
    cost_usd: float = 0.0
    results: list[SERPResultResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CONTENT GAP & QUESTION SCHEMAS
# ============================================================================


class ContentGapResponse(BaseModel):
    id: UUID
    keyword_cluster_id: UUID | None = None
    opportunity_id: UUID | None = None
    gap_type: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    importance_score: float
    confidence_score: float
    source_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoveredQuestionResponse(BaseModel):
    id: UUID
    question: str
    normalized_question: str
    intent: SearchIntent
    importance_score: float
    source: str
    confidence: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TOPIC CLUSTER SCHEMAS
# ============================================================================


class TopicClusterBase(BaseModel):
    site_id: UUID
    name: str = Field(..., max_length=255)
    canonical_topic: str = Field(..., max_length=255)
    pillar_opportunity_id: UUID | None = None
    language: str = "en"
    country: str = "global"
    status: str = "active"
    aggregate_opportunity_score: float = 50.0
    topical_relevance_score: float = 50.0


class TopicClusterCreate(TopicClusterBase):
    pass


class TopicClusterResponse(TopicClusterBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CONTENT OPPORTUNITY SCHEMAS
# ============================================================================


class ScoreBreakdown(BaseModel):
    search_demand: float = 0.0
    intent_strength: float = 0.0
    competition_opportunity: float = 0.0
    site_relevance: float = 0.0
    topical_authority: float = 0.0
    trend_strength: float = 0.0
    freshness: float = 0.0
    evergreen: float = 0.0
    original_value: float = 0.0
    information_gain: float = 0.0
    serp_gap: float = 0.0
    monetization: float = 0.0
    audience_fit: float = 0.0
    content_type_fit: float = 0.0


class PenaltiesBreakdown(BaseModel):
    cannibalization_penalty: float = 0.0
    risk_penalty: float = 0.0
    low_confidence_penalty: float = 0.0
    extreme_competition_penalty: float = 0.0
    expiration_penalty: float = 0.0


class ContentOpportunityBase(BaseModel):
    canonical_topic: str
    proposed_angle: str
    working_title: str
    primary_keyword: str
    primary_intent: SearchIntent
    secondary_intent: SearchIntent | None = None
    content_type: ContentType = ContentType.EXPLAINER
    target_audience: list[str] = Field(default_factory=list)
    language: str = "en"
    country: str = "global"
    cluster_role: ClusterRole = ClusterRole.STANDALONE
    recommended_action: ContentAction = ContentAction.CREATE

    # Component Scores
    trend_score: float = 0.0
    search_demand_score: float = 50.0
    intent_strength_score: float = 50.0
    competition_score: float = 50.0
    competition_opportunity_score: float = 50.0
    freshness_score: float = 50.0
    evergreen_score: float = 50.0
    site_relevance_score: float = 50.0
    topical_authority_score: float = 50.0
    original_value_score: float = 50.0
    information_gain_score: float = 50.0
    serp_gap_score: float = 50.0
    monetization_score: float = 0.0
    audience_fit_score: float = 50.0
    content_type_fit_score: float = 50.0
    cannibalization_risk_score: float = 0.0
    risk_score: float = 0.0

    opportunity_score: float = 50.0
    confidence_score: float = 50.0

    scoring_profile: str = "default"
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    penalties_breakdown: dict[str, Any] = Field(default_factory=dict)
    score_reasons: list[str] = Field(default_factory=list)

    status: OpportunityStatus = OpportunityStatus.CANDIDATE
    priority: OpportunityClassification = OpportunityClassification.QUALIFIED
    dependency_status: OpportunityDependencyStatus = OpportunityDependencyStatus.READY

    reasoning_summary: str | None = None
    risk_flags: list[str] = Field(default_factory=list)
    freshness_decay_type: FreshnessDecayType = FreshnessDecayType.EVERGREEN
    opportunity_half_life_hours: float | None = None
    expires_at: datetime | None = None

    scoring_version: str = "1.0.0"
    analysis_version: str = "1.0.0"
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD


class ContentOpportunityResponse(ContentOpportunityBase):
    id: UUID
    site_id: UUID
    event_id: UUID | None = None
    topic_cluster_id: UUID | None = None
    target_content_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityExplanationResponse(BaseModel):
    opportunity_id: UUID
    canonical_topic: str
    working_title: str
    recommended_action: ContentAction
    opportunity_score: float
    confidence_score: float
    priority: OpportunityClassification
    positive_factors: list[str]
    negative_factors: list[str]
    penalties_applied: list[str]
    score_breakdown: dict[str, Any]
    missing_data_notes: list[str]
    risk_notes: list[str]
    data_sources: list[str]


class OpportunitySnapshotResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    opportunity_score: float
    confidence_score: float
    status: str
    search_demand_score: float
    competition_score: float
    trend_score: float
    freshness_score: float
    evergreen_score: float
    monetization_score: float
    cannibalization_risk_score: float
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityWatchlistResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    reason: str
    recheck_after: datetime
    recheck_count: int
    last_checked_at: datetime | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ContentActionOverrideRequest(BaseModel):
    recommended_action: ContentAction
    reason: str
    target_content_id: UUID | None = None


# ============================================================================
# PART 4 HANDOFF PACKAGE SCHEMA
# ============================================================================


class ContentOpportunityPackage(BaseModel):
    """
    Standardized payload handed off from Part 3 to Part 4 (Deep Research & Fact Briefs).
    Contains clean, structured opportunity data, keywords, SERP evidence,
    content gaps, competitor URLs, and risk flags — no raw internet chaos.
    """

    opportunity_id: str
    event_id: str | None = None
    site_id: str

    topic: str
    proposed_angle: str
    working_title: str
    content_type: str
    target_audience: list[str] = Field(default_factory=list)

    language: str = "en"
    country: str = "global"

    primary_keyword: str
    secondary_keywords: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)

    primary_intent: str
    secondary_intent: str | None = None

    trend_score: float
    search_demand_score: float
    competition_opportunity_score: float
    site_relevance_score: float
    topical_authority_score: float
    freshness_score: float
    evergreen_score: float
    original_value_score: float
    serp_gap_score: float
    monetization_score: float
    cannibalization_risk_score: float

    opportunity_score: float
    confidence_score: float
    recommended_action: str

    content_gaps: list[str] = Field(default_factory=list)
    competitor_urls: list[str] = Field(default_factory=list)
    existing_related_content: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)

    expires_at: str | None = None
    score_explanation: list[str] = Field(default_factory=list)
