"""
Zohra — Research Pydantic Schemas.

Type-safe request, response, and handoff contracts for Part 4 Autonomous Deep Research.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResearchDepth(str, Enum):
    LIGHT = "LIGHT"
    STANDARD = "STANDARD"
    DEEP = "DEEP"
    CRITICAL = "CRITICAL"


class QuestionPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QuestionType(str, Enum):
    DEFINITION = "definition"
    TECHNICAL = "technical"
    PRICING = "pricing"
    AVAILABILITY = "availability"
    TIMELINE = "timeline"
    COMPARISON = "comparison"
    LIMITATION = "limitation"
    STATISTICS = "statistics"
    HISTORICAL = "historical"
    LEGAL = "legal"
    PRODUCT = "product"
    PROCESS = "process"
    RISK = "risk"
    USER_EXPERIENCE = "user_experience"


class QueryType(str, Enum):
    PRIMARY_SOURCE = "primary_source"
    OFFICIAL_DOCUMENTATION = "official_documentation"
    GENERAL_WEB = "general_web"
    NEWS = "news"
    RESEARCH = "research"
    COMMUNITY = "community"
    HISTORICAL = "historical"
    VERIFICATION = "verification"
    CONTRADICTION_RESOLUTION = "contradiction_resolution"


class SourceType(str, Enum):
    OFFICIAL_DOCUMENTATION = "official_documentation"
    OFFICIAL_ANNOUNCEMENT = "official_announcement"
    ACADEMIC_PAPER = "academic_paper"
    REGULATORY_FILING = "regulatory_filing"
    NEWS_REPORT = "news_report"
    INDUSTRY_BLOG = "industry_blog"
    COMMUNITY_FORUM = "community_forum"
    REVIEW = "review"


class ClaimType(str, Enum):
    FACT = "fact"
    NUMBER = "number"
    DATE = "date"
    PRICE = "price"
    CAPABILITY = "capability"
    LIMITATION = "limitation"
    COMPARISON = "comparison"
    HISTORICAL = "historical"
    QUOTE = "quote"
    PREDICTION = "prediction"
    OPINION = "opinion"
    ATTRIBUTION = "attribution"
    AVAILABILITY = "availability"
    REQUIREMENT = "requirement"
    DEFINITION = "definition"


class ClaimImportance(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    SUPPORTING = "supporting"
    MINOR = "minor"


class ClaimStatus(str, Enum):
    UNVERIFIED = "unverified"
    WEAKLY_SUPPORTED = "weakly_supported"
    SUPPORTED = "supported"
    STRONGLY_SUPPORTED = "strongly_supported"
    DISPUTED = "disputed"
    CONTRADICTED = "contradicted"
    OUTDATED = "outdated"
    UNKNOWN = "unknown"


class WriterPolicy(str, Enum):
    SAFE_TO_STATE = "SAFE_TO_STATE"
    REQUIRE_ATTRIBUTION = "REQUIRE_ATTRIBUTION"
    DO_NOT_STATE_AS_FACT = "DO_NOT_STATE_AS_FACT"
    TIME_SENSITIVE_CONTEXT = "TIME_SENSITIVE_CONTEXT"


class SupportDirection(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    PARTIALLY_SUPPORTS = "partially_supports"
    CONTEXT_ONLY = "context_only"


class ContradictionResolutionStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED_BY_PRIMARY_SOURCE = "resolved_by_primary_source"
    RESOLVED_BY_FRESHNESS = "resolved_by_freshness"
    RESOLVED_BY_SCOPE = "resolved_by_scope"
    RESOLVED_BY_REGION = "resolved_by_region"
    RESOLVED_BY_VERSION = "resolved_by_version"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class TimelinePrecision(str, Enum):
    EXACT_TIMESTAMP = "exact_timestamp"
    DATE = "date"
    MONTH = "month"
    YEAR = "year"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"


class GapType(str, Enum):
    NO_SOURCE = "no_source"
    WEAK_SOURCE = "weak_source"
    CONTRADICTORY = "contradictory"
    OUTDATED = "outdated"
    MISSING_PRIMARY_SOURCE = "missing_primary_source"
    INSUFFICIENT_CORROBORATION = "insufficient_corroboration"
    REGIONAL_UNCERTAINTY = "regional_uncertainty"
    TEMPORAL_UNCERTAINTY = "temporal_uncertainty"


# -------------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------------

class ResearchProjectCreateRequest(BaseModel):
    opportunity_id: uuid.UUID
    research_depth: ResearchDepth = ResearchDepth.STANDARD
    custom_objective: str | None = None


class ContradictionResolveRequest(BaseModel):
    resolution_status: ContradictionResolutionStatus
    resolution_reason: str
    preferred_claim_id: uuid.UUID | None = None


# -------------------------------------------------------------------------
# Response Models
# -------------------------------------------------------------------------

class ResearchQuestionResponse(BaseModel):
    id: uuid.UUID
    question: str
    question_type: str
    priority: str
    requires_primary_source: bool
    requires_multiple_sources: bool
    status: str
    answer_summary: str | None = None
    confidence_score: float = 0.0

    class Config:
        from_attributes = True


class ResearchQueryResponse(BaseModel):
    id: uuid.UUID
    query: str
    query_type: str
    language: str
    country: str
    priority: str
    status: str
    provider: str
    result_count: int = 0
    cost: float = 0.0

    class Config:
        from_attributes = True


class ResearchSourceResponse(BaseModel):
    id: uuid.UUID
    url: str
    canonical_url: str
    title: str | None = None
    publisher: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime
    source_tier: int
    source_type: str
    is_primary_source: bool
    is_official_source: bool
    independence_group_id: str | None = None
    relevance_score: float
    authority_score: float
    reliability_score: float
    freshness_score: float
    research_value_score: float
    status: str

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    content_hash: str
    retrieved_at: datetime
    published_at: datetime | None = None
    has_changed: bool
    change_summary: str | None = None

    class Config:
        from_attributes = True


class EvidenceItemResponse(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    research_source_id: uuid.UUID
    evidence_type: str
    support_direction: str
    evidence_text_reference: str
    source_location: str | None = None
    relevance_score: float
    source_quality_score: float
    evidence_strength_score: float

    class Config:
        from_attributes = True


class ClaimResponse(BaseModel):
    id: uuid.UUID
    claim_text: str
    normalized_claim: str
    claim_type: str
    subject_entity: str | None = None
    predicate: str | None = None
    object_value: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    currency: str | None = None
    region: str | None = None
    temporal_scope: str | None = None
    importance: str
    status: str
    confidence_score: float
    verification_level: int
    time_sensitive: bool
    attribution_required: bool
    writer_policy: str
    evidence: list[EvidenceItemResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ContradictionResponse(BaseModel):
    id: uuid.UUID
    claim_a_id: uuid.UUID
    claim_b_id: uuid.UUID
    contradiction_type: str
    severity: str
    description: str
    resolution_status: str
    resolution_reason: str | None = None
    preferred_claim_id: uuid.UUID | None = None
    confidence_score: float

    class Config:
        from_attributes = True


class EntityRelationshipResponse(BaseModel):
    id: uuid.UUID
    subject_entity_id: uuid.UUID
    predicate: str
    object_entity_id: uuid.UUID | None = None
    object_value: str | None = None
    confidence_score: float
    evidence_text: str | None = None

    class Config:
        from_attributes = True


class ResearchTimelineResponse(BaseModel):
    id: uuid.UUID
    event_time: datetime | None = None
    event_time_precision: str
    time_raw_text: str | None = None
    description: str
    importance: str
    confidence_score: float

    class Config:
        from_attributes = True


class ResearchGapResponse(BaseModel):
    id: uuid.UUID
    gap_type: str
    description: str
    importance: str
    recommended_action: str
    status: str

    class Config:
        from_attributes = True


class ResearchQualityResponse(BaseModel):
    coverage_score: float
    critical_claim_coverage_score: float
    source_quality_score: float
    primary_source_coverage: float
    corroboration_score: float
    freshness_score: float
    contradiction_resolution_score: float
    evidence_specificity_score: float
    research_quality_score: float
    research_confidence_score: float
    quality_gate_status: str  # PASS, STRONG, EXCEPTIONAL, MORE_RESEARCH, INSUFFICIENT, FAIL


class ResearchProjectResponse(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    site_id: uuid.UUID
    topic: str
    research_objective: str
    research_depth: str
    language: str
    country: str
    status: str
    risk_level: str
    source_count: int
    primary_source_count: int
    claim_count: int
    verified_claim_count: int
    contradiction_count: int
    coverage_score: float
    source_quality_score: float
    research_confidence_score: float
    research_quality_score: float
    actual_cost: float
    research_version: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    stop_reason: str | None = None

    class Config:
        from_attributes = True


# -------------------------------------------------------------------------
# Part 5 Handoff Schema: FinalResearchPackage
# -------------------------------------------------------------------------

class VerifiedFactHandoff(BaseModel):
    claim_id: str
    claim: str
    claim_type: str
    subject: str | None = None
    predicate: str | None = None
    object_value: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    currency: str | None = None
    region: str | None = None
    temporal_scope: str | None = None
    status: str
    confidence: float
    time_sensitive: bool
    attribution_required: bool
    writer_policy: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class WriterInstructions(BaseModel):
    safe_claim_ids: list[str] = Field(default_factory=list)
    attribution_required_claim_ids: list[str] = Field(default_factory=list)
    do_not_state_as_fact_claim_ids: list[str] = Field(default_factory=list)
    time_sensitive_claim_ids: list[str] = Field(default_factory=list)


class ResearchQuestionsSummary(BaseModel):
    answered: list[dict[str, Any] | str] = Field(default_factory=list)
    partially_answered: list[dict[str, Any] | str] = Field(default_factory=list)
    unanswered: list[dict[str, Any] | str] = Field(default_factory=list)


class FinalResearchPackage(BaseModel):
    research_project_id: str
    opportunity_id: str
    topic: str
    research_objective: str
    executive_summary: str
    verified_facts: list[VerifiedFactHandoff] = Field(default_factory=list)
    uncertain_claims: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    primary_sources: list[dict[str, Any]] = Field(default_factory=list)
    supporting_sources: list[dict[str, Any]] = Field(default_factory=list)
    research_questions: ResearchQuestionsSummary
    content_gaps: list[dict[str, Any]] = Field(default_factory=list)
    important_numbers: list[dict[str, Any]] = Field(default_factory=list)
    important_dates: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[dict[str, Any] | str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    research_quality_score: float
    research_confidence_score: float
    source_quality_score: float
    critical_claim_coverage_score: float
    instructions_for_writer: WriterInstructions
    citation_map: dict[str, list[str]] = Field(default_factory=dict)
    version: int = 1
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
