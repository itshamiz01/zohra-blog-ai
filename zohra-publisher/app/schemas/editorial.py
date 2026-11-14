"""
Zohra — Editorial Generation & Drafting Schemas (Part 5).

Pydantic schemas for content strategy, article blueprints, section writing,
claim grounding, quality scoring, brand voice, and the Part 6 handoff package.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    BREAKING_NEWS = "breaking_news"
    NEWS_ANALYSIS = "news_analysis"
    EXPLAINER = "explainer"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    REVIEW = "review"
    ALTERNATIVES = "alternatives"
    PRICING = "pricing"
    TROUBLESHOOTING = "troubleshooting"
    REFERENCE = "reference"
    GUIDE = "guide"
    CASE_STUDY = "case_study"
    TIMELINE = "timeline"
    FAQ = "faq"


class PrimaryIntent(str, Enum):
    INFORMATIONAL = "informational"
    NEWS = "news"
    TUTORIAL = "tutorial"
    COMPARISON = "comparison"
    COMMERCIAL_INVESTIGATION = "commercial_investigation"
    TRANSACTIONAL = "transactional"
    TROUBLESHOOTING = "troubleshooting"
    REFERENCE = "reference"


class GroundingStatus(str, Enum):
    GROUNDED = "grounded"
    PARTIALLY_GROUNDED = "partially_grounded"
    UNGROUNDED = "ungrounded"
    NON_FACTUAL = "non_factual"
    ATTRIBUTION_REQUIRED = "attribution_required"


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class DraftCreateRequest(BaseModel):
    research_package_id: uuid.UUID
    content_type_override: str | None = None
    target_audience: list[str] | None = None
    tone_override: str | None = None
    brand_voice_id: uuid.UUID | None = None
    language_override: str | None = None
    country_override: str | None = None


class DraftReviseRequest(BaseModel):
    section_id: str | None = None
    instruction: str
    issue_type: str = "editorial_fix"


class EditorialOverrideRequest(BaseModel):
    headline: str | None = None
    angle: str | None = None
    content_type: str | None = None
    section_order: list[str] | None = None
    tone: str | None = None
    target_audience: list[str] | None = None
    call_to_action: str | None = None


class BrandVoiceProfileCreate(BaseModel):
    site_id: uuid.UUID
    name: str
    tone: str = "professional_approachable"
    formality: str = "neutral"
    sentence_style: str = "clear_concise"
    vocabulary_level: str = "intermediate"
    preferred_patterns: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)
    humor_level: str = "none"
    technical_depth: str = "moderate"
    directness: str = "high"
    examples: list[dict[str, Any]] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Component Data Schemas
# -----------------------------------------------------------------------------

class ContentStrategyData(BaseModel):
    reader_problem: str
    reader_goal: str
    search_intent: str
    content_goal: str
    recommended_content_type: str
    angle: str
    differentiation_strategy: str
    information_gain_strategy: str
    tone: str
    depth: str
    target_length_min: int
    target_length_max: int
    conversion_goal: str | None = None
    risk_notes: str | None = None


class SectionBlueprint(BaseModel):
    section_id: str
    heading: str
    purpose: str
    reader_question: str
    target_claim_ids: list[str] = Field(default_factory=list)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    required_sources: list[str] = Field(default_factory=list)
    target_keywords: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    recommended_format: str = "prose"  # prose, list, steps, table, comparison
    estimated_length: int = 300
    citation_requirement: bool = True
    risk_notes: str | None = None


class ArticleBlueprintData(BaseModel):
    working_title: str
    article_promise: str
    primary_intent: str
    content_type: str
    target_audience: str | None = None
    introduction_goal: str
    sections: list[SectionBlueprint] = Field(default_factory=list)
    conclusion_goal: str
    faq_plan: list[dict[str, Any]] = Field(default_factory=list)
    table_plan: list[dict[str, Any]] = Field(default_factory=list)
    citation_plan: list[dict[str, Any]] = Field(default_factory=list)
    internal_link_plan: list[dict[str, Any]] = Field(default_factory=list)
    claim_allocation: dict[str, list[str]] = Field(default_factory=dict)


class HeadlineCandidateResponse(BaseModel):
    id: uuid.UUID
    headline: str
    style: str
    intent_score: float
    clarity_score: float
    accuracy_score: float
    seo_score: float
    brand_score: float
    overall_score: float
    selected: bool
    selection_reason: str | None = None

    class Config:
        from_attributes = True


class DraftSection(BaseModel):
    section_id: str
    heading: str
    content: str
    used_claim_ids: list[str] = Field(default_factory=list)
    citation_placements: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)


class DraftFAQItem(BaseModel):
    question: str
    answer: str
    grounded_claim_ids: list[str] = Field(default_factory=list)


class DraftTableItem(BaseModel):
    table_id: str
    title: str
    headers: list[str]
    rows: list[list[str]]
    grounded_claim_ids: list[str] = Field(default_factory=list)


class SentenceGroundingDetail(BaseModel):
    sentence_index: int
    section_id: str
    sentence_text: str
    claim_ids: list[str]
    grounding_status: str
    confidence: float


class DraftQualityScores(BaseModel):
    intent_satisfaction: float
    grounding: float
    information_gain: float
    clarity: float
    structure: float
    seo_content: float
    citation_quality: float
    readability: float
    brand_voice: float
    draft_quality: float
    quality_gate_passed: bool
    classification: str  # REJECT, MAJOR_REVISION, REVISION_REQUIRED, PART_6_ELIGIBLE, STRONG_DRAFT, EXCEPTIONAL_DRAFT


class InternalLinkCandidateResponse(BaseModel):
    source_section_id: str
    target_content_id: str | None = None
    target_url: str
    recommended_anchor_context: str
    relevance_score: float
    reason: str


class BrandVoiceProfileResponse(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    name: str
    tone: str
    formality: str
    sentence_style: str
    vocabulary_level: str
    preferred_patterns: list[str] = Field(default_factory=list)
    avoid_patterns: list[str] = Field(default_factory=list)
    humor_level: str
    technical_depth: str
    directness: str

    class Config:
        from_attributes = True


# -----------------------------------------------------------------------------
# Part 6 Handoff Package: EditorialDraftPackage
# -----------------------------------------------------------------------------

class EditorialArticleContent(BaseModel):
    introduction: str
    sections: list[DraftSection] = Field(default_factory=list)
    faq: list[DraftFAQItem] = Field(default_factory=list)
    tables: list[DraftTableItem] = Field(default_factory=list)
    conclusion: str


class EditorialDraftPackageData(BaseModel):
    draft_project_id: str
    research_package_id: str
    opportunity_id: str
    content_type: str
    primary_keyword: str
    primary_intent: str
    target_audience: list[str] = Field(default_factory=list)
    strategy: dict[str, Any]
    headline: str
    slug_candidate: str
    meta_title: str
    meta_description: str
    article: EditorialArticleContent
    claim_usage: list[dict[str, Any]] = Field(default_factory=list)
    citation_map: list[dict[str, Any]] = Field(default_factory=list)
    internal_link_candidates: list[dict[str, Any]] = Field(default_factory=list)
    schema_candidates: list[str] = Field(default_factory=list)
    social_metadata: dict[str, str] = Field(default_factory=dict)
    quality: DraftQualityScores
    risk_flags: list[str] = Field(default_factory=list)
    research_followups: list[dict[str, Any]] = Field(default_factory=list)
    revalidate_after: str | None = None
    draft_version: int = 1
    generation_metadata: dict[str, str] = Field(default_factory=dict)


# -----------------------------------------------------------------------------
# Project & Version Response Models
# -----------------------------------------------------------------------------

class DraftVersionResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    title: str
    slug_candidate: str
    meta_title: str | None = None
    meta_description: str | None = None
    content: str
    grounding_score: float
    quality_score: float
    generation_reason: str
    created_at: datetime

    class Config:
        from_attributes = True


class DraftProjectResponse(BaseModel):
    id: uuid.UUID
    research_package_id: uuid.UUID
    opportunity_id: uuid.UUID
    site_id: uuid.UUID
    content_type: str
    target_audience: list[str] | None = None
    primary_keyword: str
    primary_intent: str
    language: str
    country: str
    status: str
    strategy_version: int
    blueprint_version: int
    writer_version: int
    prompt_version: str
    research_quality_score: float
    draft_quality_score: float
    grounding_score: float
    readability_score: float
    intent_alignment_score: float
    information_gain_score: float
    seo_content_score: float
    brand_voice_score: float
    actual_cost: float
    revalidate_after: datetime | None = None
    stop_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class DraftExplanationResponse(BaseModel):
    draft_project_id: uuid.UUID
    status: str
    angle: str
    why_this_angle: str
    why_this_structure: str
    why_this_headline: str
    claims_used_count: int
    claims_excluded_count: int
    unsupported_claims_prevented: int
    citations_count: int
    remaining_information_gaps: list[str]
    quality_breakdown: DraftQualityScores
    revisions_performed: int
    cost_summary: dict[str, float]
