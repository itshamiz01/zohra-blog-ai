"""Pydantic schemas for Part 2 Discovery & Trend Intelligence Engine."""

import contextlib
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    CircuitBreakerState,
    EventStatus,
    EventType,
    RiskFlag,
    SourceHealth,
    SourceTier,
    SourceType,
    TrendClassification,
)

# ============================================================================
# SOURCE SCHEMAS
# ============================================================================


class SourceBase(BaseModel):
    name: str = Field(..., max_length=255)
    domain: str = Field(..., max_length=255)
    base_url: str = Field(..., max_length=1024)
    source_type: SourceType = SourceType.RSS
    tier: SourceTier = SourceTier.TIER_3
    category: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default="global", max_length=10)
    language: str | None = Field(default="en", max_length=10)
    authority_score: float = Field(default=50.0, ge=0.0, le=100.0)
    reliability_score: float = Field(default=50.0, ge=0.0, le=100.0)
    freshness_score: float = Field(default=50.0, ge=0.0, le=100.0)
    priority: int = Field(default=3, ge=1, le=5)
    polling_interval_minutes: int = Field(default=30, ge=1, le=1440)
    is_enabled: bool = True
    is_trusted: bool = False
    requires_authentication: bool = False
    robots_policy_checked: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    base_url: str | None = None
    source_type: SourceType | None = None
    tier: SourceTier | None = None
    category: str | None = None
    country: str | None = None
    language: str | None = None
    authority_score: float | None = Field(default=None, ge=0.0, le=100.0)
    reliability_score: float | None = Field(default=None, ge=0.0, le=100.0)
    freshness_score: float | None = Field(default=None, ge=0.0, le=100.0)
    priority: int | None = Field(default=None, ge=1, le=5)
    polling_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    is_enabled: bool | None = None
    is_trusted: bool | None = None
    requires_authentication: bool | None = None
    robots_policy_checked: bool | None = None
    metadata_json: dict[str, Any] | None = None


class SourceResponse(SourceBase):
    id: UUID
    health_status: SourceHealth = SourceHealth.HEALTHY
    circuit_breaker_state: CircuitBreakerState = Field(
        default=CircuitBreakerState.CLOSED, alias="circuit_breaker_state"
    )
    circuit_state: CircuitBreakerState = Field(default=CircuitBreakerState.CLOSED)
    consecutive_failures: int = 0
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    average_response_time_ms: float = 0.0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SourceTestResult(BaseModel):
    source_id: UUID
    success: bool
    status_code: int | None = None
    items_found: int = 0
    response_time_ms: float = 0.0
    error: str | None = None


# ============================================================================
# DOCUMENT SCHEMAS
# ============================================================================


class SourceDocumentResponse(BaseModel):
    id: UUID
    source_id: UUID
    external_id: str | None = None
    url: str
    canonical_url: str
    title: str
    summary: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    language: str
    country: str
    source_type: SourceType
    word_count: int
    is_exact_duplicate: bool
    is_near_duplicate: bool
    duplicate_of_id: UUID | None = None
    categories: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    created_at: datetime

    @field_validator("categories", "risk_flags", mode="before")
    @classmethod
    def _coerce_doc_lists(cls, v: Any) -> list[str]:
        return v or []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ENTITY SCHEMAS
# ============================================================================


class EntityResponse(BaseModel):
    id: UUID
    entity_type: str
    canonical_name: str
    normalized_name: str
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime

    @field_validator("aliases", mode="before")
    @classmethod
    def _coerce_aliases(cls, v: Any) -> list[str]:
        return v or []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EVENT SCHEMAS
# ============================================================================


class EventDocumentResponse(BaseModel):
    document_id: UUID
    title: str
    url: str
    similarity_score: float
    relevance_score: float
    is_primary_source: bool
    is_original_report: bool
    created_at: datetime


class EventResponse(BaseModel):
    id: UUID
    canonical_title: str
    summary: str
    primary_category: str
    event_type: EventType
    first_seen_at: datetime
    last_seen_at: datetime
    event_time: datetime | None = None
    status: EventStatus
    source_count: int
    document_count: int
    authority_score: float
    reliability_score: float
    freshness_score: float
    velocity_score: float
    momentum_score: float
    source_diversity_score: float
    confidence_score: float
    trend_score: float
    trend_classification: TrendClassification
    language: str
    country: str
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    high_verification_required: bool
    contradiction_detected: bool
    is_qualified_for_opportunity: bool
    trend_reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("risk_flags", mode="before")
    @classmethod
    def _coerce_risk_flags(cls, v: Any) -> list[RiskFlag]:
        if not v:
            return []
        res = []
        for x in v:
            if isinstance(x, RiskFlag):
                res.append(x)
            elif isinstance(x, str):
                with contextlib.suppress(ValueError):
                    res.append(RiskFlag(x))
        return res

    @field_validator("trend_reasons", mode="before")
    @classmethod
    def _coerce_trend_reasons(cls, v: Any) -> list[str]:
        return v or []

    model_config = ConfigDict(from_attributes=True)


class EventDetailResponse(EventResponse):
    primary_source_document_id: UUID | None = None
    contradiction_notes: list[str] = Field(default_factory=list)
    documents: list[EventDocumentResponse] = Field(default_factory=list)
    entities: list[EntityResponse] = Field(default_factory=list)

    @field_validator("contradiction_notes", "documents", "entities", mode="before")
    @classmethod
    def _coerce_detail_lists(cls, v: Any) -> list:
        return v or []


class EventMergeRequest(BaseModel):
    source_event_id: UUID
    target_event_id: UUID
    reason: str = Field(..., min_length=3, max_length=500)


class EventSplitRequest(BaseModel):
    document_ids: list[UUID] = Field(..., min_length=1)
    new_event_title: str = Field(..., min_length=5, max_length=500)
    reason: str = Field(..., min_length=3, max_length=500)


# ============================================================================
# TREND & TIMELINE SCHEMAS
# ============================================================================


class TrendItemResponse(BaseModel):
    event_id: UUID
    title: str
    category: str
    event_type: str
    trend_score: float
    velocity_score: float
    momentum_score: float
    confidence_score: float
    source_diversity_score: float
    source_count: int
    document_count: int
    status: str
    classification: str
    first_seen_at: datetime
    last_seen_at: datetime
    trend_reasons: list[str] = Field(default_factory=list)
    is_qualified: bool


class EventSnapshotResponse(BaseModel):
    id: UUID
    event_id: UUID
    timestamp: datetime
    document_count: int
    source_count: int
    velocity_score: float
    momentum_score: float
    trend_score: float
    confidence_score: float
    status: EventStatus

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DISCOVERY CONTROL & STATS SCHEMAS
# ============================================================================


class DiscoveryRunRequest(BaseModel):
    source_ids: list[UUID] | None = None
    force: bool = False


class DiscoveryStatusResponse(BaseModel):
    autonomy_enabled: bool
    discovery_enabled: bool
    maintenance_mode: bool
    active_sources: int
    paused_sources: int
    circuit_open_sources: int
    pending_tasks: int = 0


class DiscoveryStatsResponse(BaseModel):
    sources_total: int
    sources_healthy: int
    sources_failing: int
    documents_discovered_today: int
    exact_duplicates_blocked_today: int
    near_duplicates_flagged_today: int
    active_events_count: int
    trending_events_count: int
    emerging_events_count: int
    qualified_opportunities_count: int
    categories_breakdown: dict[str, int]
    languages_breakdown: dict[str, int]
    discovery_spend_usd_today: float
