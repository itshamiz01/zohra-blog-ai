"""
Zohra — Opportunity Scoring Engine.

Computes multi-dimensional content opportunity scores across configurable profiles
(default, breaking_news, evergreen, commercial_comparison).
Applies explicit penalty deductions (cannibalization, risk flags, extreme competition).
Produces auditable breakdown, confidence score, priority classification, and human-readable reasons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.constants import (
    BREAKING_NEWS_OPPORTUNITY_WEIGHTS,
    COMMERCIAL_COMPARISON_OPPORTUNITY_WEIGHTS,
    DEFAULT_OPPORTUNITY_WEIGHTS,
    EVERGREEN_OPPORTUNITY_WEIGHTS,
    ContentAction,
    OpportunityClassification,
    OpportunityStatus,
)


@dataclass
class ScoringInput:
    trend_score: float = 0.0
    search_demand_score: float = 50.0
    intent_strength_score: float = 50.0
    competition_opportunity_score: float = 50.0
    site_relevance_score: float = 50.0
    topical_authority_score: float = 50.0
    freshness_score: float = 50.0
    evergreen_score: float = 50.0
    original_value_score: float = 50.0
    serp_gap_score: float = 50.0
    monetization_score: float = 0.0
    audience_fit_score: float = 50.0
    cannibalization_risk_score: float = 0.0
    risk_score: float = 0.0
    is_official_dominant: bool = False
    evidence_count: int = 3
    recommended_action: ContentAction = ContentAction.CREATE
    expires_at: datetime | None = None
    scoring_profile: str = "default"


@dataclass
class ScoringResult:
    opportunity_score: float
    confidence_score: float
    status: OpportunityStatus
    priority: OpportunityClassification
    scoring_profile: str
    score_breakdown: dict[str, float] = field(default_factory=dict)
    penalties_breakdown: dict[str, float] = field(default_factory=dict)
    positive_reasons: list[str] = field(default_factory=list)
    negative_reasons: list[str] = field(default_factory=list)
    score_explanation: list[str] = field(default_factory=list)


class OpportunityScoringEngine:
    """Calculates weighted opportunity scores, penalties, and audit explanations."""

    WEIGHT_PROFILES = {
        "default": DEFAULT_OPPORTUNITY_WEIGHTS,
        "breaking_news": BREAKING_NEWS_OPPORTUNITY_WEIGHTS,
        "evergreen": EVERGREEN_OPPORTUNITY_WEIGHTS,
        "commercial_comparison": COMMERCIAL_COMPARISON_OPPORTUNITY_WEIGHTS,
    }

    def score(self, inp: ScoringInput) -> ScoringResult:
        weights = self.WEIGHT_PROFILES.get(inp.scoring_profile, DEFAULT_OPPORTUNITY_WEIGHTS)

        # 1. Positive Component Contributions (weights sum to 1.0)
        c_demand = inp.search_demand_score * weights.get("search_demand", 0.0)
        c_intent = inp.intent_strength_score * weights.get("intent_strength", 0.0)
        c_comp = inp.competition_opportunity_score * weights.get("competition_opportunity", 0.0)
        c_site = inp.site_relevance_score * weights.get("site_relevance", 0.0)
        c_auth = inp.topical_authority_score * weights.get("topical_authority", 0.0)
        c_trend = inp.trend_score * weights.get("trend_strength", 0.0)
        c_fresh = inp.freshness_score * weights.get("freshness", 0.0)
        c_evergreen = inp.evergreen_score * weights.get("evergreen", 0.0)
        c_orig = inp.original_value_score * weights.get("original_value", 0.0)
        c_gap = inp.serp_gap_score * weights.get("serp_gap", 0.0)
        c_monetization = inp.monetization_score * weights.get("monetization", 0.0)
        c_audience = inp.audience_fit_score * weights.get("audience_fit", 0.0)

        positive_score = (
            c_demand + c_intent + c_comp + c_site + c_auth + c_trend +
            c_fresh + c_evergreen + c_orig + c_gap + c_monetization + c_audience
        )

        breakdown = {
            "search_demand": round(c_demand, 2),
            "intent_strength": round(c_intent, 2),
            "competition_opportunity": round(c_comp, 2),
            "site_relevance": round(c_site, 2),
            "topical_authority": round(c_auth, 2),
            "trend_strength": round(c_trend, 2),
            "freshness": round(c_fresh, 2),
            "evergreen": round(c_evergreen, 2),
            "original_value": round(c_orig, 2),
            "serp_gap": round(c_gap, 2),
            "monetization": round(c_monetization, 2),
            "audience_fit": round(c_audience, 2),
        }

        # 2. Penalties Calculation
        penalties: dict[str, float] = {}

        # Cannibalization penalty applies if attempting CREATE on an already covered intent
        if inp.recommended_action == ContentAction.CREATE and inp.cannibalization_risk_score > 50.0:
            cann_pen = (inp.cannibalization_risk_score / 100.0) * 25.0
            penalties["cannibalization"] = round(cann_pen, 2)
        else:
            penalties["cannibalization"] = 0.0

        # Risk penalty (YMYL, legal, unverified)
        if inp.risk_score > 0.0:
            risk_pen = min(30.0, (inp.risk_score / 100.0) * 30.0)
            penalties["risk"] = round(risk_pen, 2)
        else:
            penalties["risk"] = 0.0

        # Extreme competition penalty (official portal completely dominates query)
        if inp.is_official_dominant and inp.competition_opportunity_score < 30.0:
            penalties["extreme_competition"] = 18.0
        else:
            penalties["extreme_competition"] = 0.0

        # Expiration penalty if opportunity expires soon or is past expiration
        now = datetime.now(UTC)
        if inp.expires_at and inp.expires_at < now:
            penalties["expired"] = 40.0
        else:
            penalties["expired"] = 0.0

        total_penalties = sum(penalties.values())

        # 3. Final Opportunity Score
        final_score = round(min(100.0, max(0.0, positive_score - total_penalties)), 1)

        # 4. Confidence Score Calculation
        # Based on completeness of evidence, source counts, and alignment
        base_confidence = 60.0
        if inp.evidence_count >= 5:
            base_confidence += 20.0
        elif inp.evidence_count >= 2:
            base_confidence += 10.0

        if inp.site_relevance_score >= 80.0:
            base_confidence += 10.0
        if inp.risk_score > 70.0:
            base_confidence -= 25.0  # Severe risk significantly lowers confidence in autonomous execution
        elif inp.risk_score > 40.0:
            base_confidence -= 15.0  # Moderate risk lowers confidence

        confidence = round(min(98.0, max(25.0, base_confidence)), 1)

        # 5. Opportunity Classification
        if final_score < 40.0 or inp.site_relevance_score < 35.0:
            classification = OpportunityClassification.REJECT
            status = OpportunityStatus.REJECTED
        elif final_score < 55.0:
            classification = OpportunityClassification.LOW
            status = OpportunityStatus.CANDIDATE
        elif final_score < 65.0:
            classification = OpportunityClassification.WATCH
            status = OpportunityStatus.WATCH
        elif final_score < 75.0:
            classification = OpportunityClassification.QUALIFIED
            status = OpportunityStatus.QUALIFIED
        elif final_score < 85.0:
            classification = OpportunityClassification.HIGH_PRIORITY
            status = OpportunityStatus.HIGH_PRIORITY
        elif final_score < 95.0:
            classification = OpportunityClassification.VERY_HIGH_PRIORITY
            status = OpportunityStatus.HIGH_PRIORITY
        else:
            classification = OpportunityClassification.EXCEPTIONAL
            status = OpportunityStatus.HIGH_PRIORITY

        # 6. Audit & Diagnostic Explanation Strings
        pos_reasons: list[str] = []
        neg_reasons: list[str] = []

        if inp.search_demand_score >= 70.0:
            pos_reasons.append("High search demand with emerging user curiosity")
        if inp.intent_strength_score >= 75.0:
            pos_reasons.append("Strong and specific search intent targeting actionable questions")
        if inp.competition_opportunity_score >= 65.0:
            pos_reasons.append("Favorable competitive landscape with weak exact-intent coverage")
        if inp.site_relevance_score >= 80.0:
            pos_reasons.append("Strong topical relevance directly aligned with site niche")
        if inp.original_value_score >= 75.0:
            pos_reasons.append("Substantial opportunity for information gain beyond existing pages")
        if inp.serp_gap_score >= 70.0:
            pos_reasons.append("Multiple structural gaps identified in top SERP results")

        if inp.competition_opportunity_score < 40.0:
            neg_reasons.append("Fierce competition dominated by high-authority or official sites")
        if inp.cannibalization_risk_score > 50.0:
            neg_reasons.append(f"Significant cannibalization risk ({inp.cannibalization_risk_score}/100) on existing site content")
        if inp.risk_score > 40.0:
            neg_reasons.append("Elevated risk policy flags require editorial verification")
        if inp.site_relevance_score < 50.0:
            neg_reasons.append("Weak alignment with primary site audience and categories")

        explanation: list[str] = []
        explanation.append(f"Opportunity Score: {final_score}/100 ({classification.value.upper()}) | Confidence: {confidence}%")
        for r in pos_reasons:
            explanation.append(f"+ {r}")
        for r in neg_reasons:
            explanation.append(f"- {r}")
        for k, v in penalties.items():
            if v > 0:
                explanation.append(f"- Penalty [{k}]: -{v} points")

        return ScoringResult(
            opportunity_score=final_score,
            confidence_score=confidence,
            status=status,
            priority=classification,
            scoring_profile=inp.scoring_profile,
            score_breakdown=breakdown,
            penalties_breakdown=penalties,
            positive_reasons=pos_reasons,
            negative_reasons=neg_reasons,
            score_explanation=explanation,
        )
