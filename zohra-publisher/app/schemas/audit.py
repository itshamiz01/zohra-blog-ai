"""
Zohra — Audit Engine Schemas (Part 6).

Pydantic schemas for independent editorial and factual audit, claim verification,
citation validation, hallucination detection, SEO audit, originality analysis,
risk review, quality scores, decisions, and the Part 7 final audit package.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuditDecision(str, Enum):
    PASS = "PASS"
    REVISE = "REVISE"
    MORE_RESEARCH = "MORE_RESEARCH"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REJECT = "REJECT"


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"
    INFO = "INFO"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClaimVerificationStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    OUTDATED = "OUTDATED"
    MISLEADING = "MISLEADING"
    ATTRIBUTION_MISSING = "ATTRIBUTION_MISSING"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"


class CheckStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class AuditStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    FACT_CHECKING = "fact_checking"
    CITATION_CHECKING = "citation_checking"
    CONTENT_CHECKING = "content_checking"
    SEO_CHECKING = "seo_checking"
    RISK_CHECKING = "risk_checking"
    ADVERSARIAL_REVIEW = "adversarial_review"
    SCORING = "scoring"
    DECISION_PENDING = "decision_pending"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class AuditCreateRequest(BaseModel):
    draft_project_id: uuid.UUID
    draft_version_id: uuid.UUID | None = None
    force_recheck: bool = False
    audit_type: str = "full_publication_audit"
    policy_version: str = "policy-v1.0"


class HumanOverrideRequest(BaseModel):
    issue_id: uuid.UUID | None = None
    override_decision: AuditDecision | None = None
    reason: str
    actor: str


# -----------------------------------------------------------------------------
# Component Data Schemas
# -----------------------------------------------------------------------------

class ParsedSentence(BaseModel):
    sentence_index: int
    text: str
    is_heading: bool = False
    is_quote: bool = False
    is_table_cell: bool = False
    is_faq: bool = False
    citations: list[str] = Field(default_factory=list)


class ParsedParagraph(BaseModel):
    paragraph_index: int
    text: str
    sentences: list[ParsedSentence] = Field(default_factory=list)


class ParsedSection(BaseModel):
    section_id: str
    heading: str
    level: int = 2
    paragraphs: list[ParsedParagraph] = Field(default_factory=list)
    raw_content: str = ""


class ParsedDraftContent(BaseModel):
    title: str
    meta_title: str
    meta_description: str
    slug: str
    sections: list[ParsedSection] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    faqs: list[dict[str, Any]] = Field(default_factory=list)
    quotes: list[dict[str, Any]] = Field(default_factory=list)
    citations_found: list[str] = Field(default_factory=list)
    links_found: list[str] = Field(default_factory=list)
    content_hash: str


class ExtractedClaim(BaseModel):
    section_id: str
    sentence_index: int
    claim_text: str
    normalized_claim: str
    claim_type: str = "factual"
    importance: str = "supporting"  # critical, major, supporting
    numbers_found: list[str] = Field(default_factory=list)
    dates_found: list[str] = Field(default_factory=list)
    requires_attribution: bool = False


class ClaimMatchResult(BaseModel):
    claim_text: str
    normalized_claim: str
    section_id: str
    sentence_index: int
    importance: str
    matched_research_claim_id: uuid.UUID | None = None
    match_confidence: float = 0.0
    verification_status: ClaimVerificationStatus = ClaimVerificationStatus.UNSUPPORTED
    entailment_score: float = 0.0
    audit_notes: str | None = None
    inflation_detected: bool = False
    scope_expanded: bool = False
    stale_evidence: bool = False


class CitationValidationResult(BaseModel):
    citation_id: str
    exists_in_research: bool
    source_url: str | None = None
    source_authority: float = 0.0
    entailment_valid: bool = False
    is_fabricated: bool = False
    is_mismatched: bool = False
    location: str
    associated_claim: str | None = None


class AuditQualityScores(BaseModel):
    factual_integrity: float = 0.0
    grounding: float = 0.0
    citation_quality: float = 0.0
    temporal_integrity: float = 0.0
    originality: float = 0.0
    intent_satisfaction: float = 0.0
    information_gain: float = 0.0
    seo_quality: float = 0.0
    content_quality: float = 0.0
    structure: float = 0.0
    brand_voice: float = 0.0
    risk_compliance: float = 0.0
    overall_score: float = 0.0


class AuditIssueItem(BaseModel):
    issue_code: str
    issue_category: str
    severity: IssueSeverity
    section_id: str | None = None
    paragraph_index: int | None = None
    sentence_index: int | None = None
    claim_id: str | None = None
    source_id: str | None = None
    description: str
    evidence: str | None = None
    recommended_action: str
    routing_target: str = "part5_writer"


class RevisionPackage(BaseModel):
    draft_project_id: str
    draft_version_number: int
    target: str = "part5_writer"
    must_preserve_elements: list[str] = Field(default_factory=list)
    issues_to_fix: list[AuditIssueItem] = Field(default_factory=list)
    prohibited_changes: list[str] = Field(default_factory=list)
    revision_guidance: str


class ResearchReturnPackage(BaseModel):
    draft_project_id: str
    research_package_id: str
    target: str = "part4_research"
    missing_questions: list[str] = Field(default_factory=list)
    affected_claims: list[str] = Field(default_factory=list)
    priority: str = "HIGH"
    freshness_required: bool = False
    blocked_sections: list[str] = Field(default_factory=list)


class HumanReviewPackage(BaseModel):
    audit_id: str
    risk_category: str
    risk_level: RiskLevel
    critical_issues: list[AuditIssueItem] = Field(default_factory=list)
    reasons_for_human_review: list[str] = Field(default_factory=list)
    specific_decisions_required: list[str] = Field(default_factory=list)


class FinalAuditPackageData(BaseModel):
    audit_id: str
    draft_project_id: str
    draft_version_number: int
    research_package_id: str
    research_package_version: int
    scores: AuditQualityScores
    claim_summary: dict[str, int]
    citation_summary: dict[str, int]
    issues: list[AuditIssueItem]
    risk: dict[str, Any]
    required_checks: dict[str, str]
    critical_failures: list[str]
    decision: AuditDecision
    eligible_for_part7: bool
    audit_fingerprint: str
    content_hash: str
    audit_token: str
    policy_version: str
    completed_at: str


# -----------------------------------------------------------------------------
# Response Schemas
# -----------------------------------------------------------------------------

class AuditProjectResponse(BaseModel):
    id: uuid.UUID
    draft_project_id: uuid.UUID
    draft_version_id: uuid.UUID | None = None
    research_package_id: uuid.UUID
    research_package_version: int
    opportunity_id: uuid.UUID
    site_id: uuid.UUID
    audit_type: str
    risk_level: str
    status: str
    factual_score: float
    citation_score: float
    grounding_score: float
    temporal_score: float
    originality_score: float
    intent_score: float
    information_gain_score: float
    seo_score: float
    content_quality_score: float
    structure_score: float
    brand_score: float
    risk_score: float
    overall_quality_score: float
    critical_issue_count: int
    major_issue_count: int
    minor_issue_count: int
    decision: str | None = None
    estimated_cost: float
    actual_cost: float
    auditor_version: str
    policy_version: str
    audit_fingerprint: str | None = None
    content_hash: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    decision: str | None = None
    overall_quality_score: float
    critical_issue_count: int
    major_issue_count: int
    minor_issue_count: int
    completed_at: datetime | None = None


class AuditExplanationResponse(BaseModel):
    audit_id: uuid.UUID
    decision: AuditDecision
    eligible_for_part7: bool
    why_decision_reached: str
    critical_failures: list[str]
    score_breakdown: AuditQualityScores
    failed_claims: list[dict[str, Any]]
    failed_citations: list[dict[str, Any]]
    numeric_date_discrepancies: list[str]
    originality_findings: list[str]
    seo_findings: list[str]
    risk_findings: list[str]
    next_step: str
    routing_package: dict[str, Any] | None = None
