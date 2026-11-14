"""
Zohra — Content Opportunity Handoff Contract for Part 4.

Builds clean, structured ContentOpportunityPackage objects ready for Part 4
(Deep Research & Fact Brief Engine) without passing raw internet noise.
"""

from __future__ import annotations

from typing import Any

from app.db.models.content_opportunities import ContentOpportunity
from app.schemas.opportunity import ContentOpportunityPackage


def build_opportunity_package(
    opportunity: ContentOpportunity,
    secondary_keywords: list[str] | None = None,
    questions: list[str] | None = None,
    entities: list[str] | None = None,
    content_gaps: list[str] | None = None,
    competitor_urls: list[str] | None = None,
    existing_related_content: list[dict[str, Any]] | None = None,
) -> ContentOpportunityPackage:
    """Constructs a clean ContentOpportunityPackage for Part 4."""
    # Extract gap descriptions if relationship is loaded or passed
    gaps_list = content_gaps or []
    if not gaps_list and hasattr(opportunity, "gaps") and opportunity.gaps:
        gaps_list = [g.description for g in opportunity.gaps]

    # Extract questions if relationship is loaded or passed
    q_list = questions or []
    if not q_list and hasattr(opportunity, "questions") and opportunity.questions:
        q_list = [q.question for q in opportunity.questions]

    return ContentOpportunityPackage(
        opportunity_id=str(opportunity.id),
        event_id=str(opportunity.event_id) if opportunity.event_id else None,
        site_id=str(opportunity.site_id),
        topic=opportunity.canonical_topic,
        proposed_angle=opportunity.proposed_angle,
        working_title=opportunity.working_title,
        content_type=opportunity.content_type,
        target_audience=opportunity.target_audience or [],
        language=opportunity.language,
        country=opportunity.country,
        primary_keyword=opportunity.primary_keyword,
        secondary_keywords=secondary_keywords or [],
        questions=q_list,
        entities=entities or [],
        primary_intent=opportunity.primary_intent,
        secondary_intent=opportunity.secondary_intent,
        trend_score=opportunity.trend_score,
        search_demand_score=opportunity.search_demand_score,
        competition_opportunity_score=opportunity.competition_opportunity_score,
        site_relevance_score=opportunity.site_relevance_score,
        topical_authority_score=opportunity.topical_authority_score,
        freshness_score=opportunity.freshness_score,
        evergreen_score=opportunity.evergreen_score,
        original_value_score=opportunity.original_value_score,
        serp_gap_score=opportunity.serp_gap_score,
        monetization_score=opportunity.monetization_score,
        cannibalization_risk_score=opportunity.cannibalization_risk_score,
        opportunity_score=opportunity.opportunity_score,
        confidence_score=opportunity.confidence_score,
        recommended_action=opportunity.recommended_action.upper(),
        content_gaps=gaps_list,
        competitor_urls=competitor_urls or [],
        existing_related_content=existing_related_content or [],
        risk_flags=opportunity.risk_flags or [],
        expires_at=opportunity.expires_at.isoformat() if opportunity.expires_at else None,
        score_explanation=opportunity.score_reasons or [],
    )
