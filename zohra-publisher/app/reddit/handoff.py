"""
Zohra — Reddit Opportunity to Research & Article Handoff.

Translates RedditOpportunity entities into standardized ContentOpportunityPackage
contracts for Zohra's core Research, Fact-Verification, and Editorial Publishing engines.

Strict Evidence Policy:
Reddit content represents DISCOVERY SIGNALS and USER PAIN POINTS.
Reddit comments are never treated as verified factual evidence.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.reddit import RedditOpportunity, RedditQuestion
from app.schemas.opportunity import ContentOpportunityPackage

logger = get_logger("reddit.handoff")


def build_reddit_opportunity_package(
    opportunity: RedditOpportunity,
    question: RedditQuestion | None = None,
) -> ContentOpportunityPackage:
    """
    Constructs a standard ContentOpportunityPackage ready for Zohra's
    Part 4 (Research) and Part 5/6 (Writing & Publishing) pipelines.
    """
    subquestions = []
    if question:
        subquestions.append(question.primary_question)
        if question.underlying_problem:
            subquestions.append(f"Core Challenge: {question.underlying_problem}")

    if opportunity.cluster and opportunity.cluster.subtopics:
        subquestions.extend(opportunity.cluster.subtopics)

    gaps = []
    if opportunity.content_gap_summary:
        gaps.append(opportunity.content_gap_summary)
    else:
        gaps.append("Address real-world user dilemma with concrete frameworks and clear evidence.")

    return ContentOpportunityPackage(
        opportunity_id=str(opportunity.id),
        event_id=None,
        site_id=str(opportunity.site_id),
        topic=opportunity.working_title,
        proposed_angle=opportunity.proposed_angle,
        working_title=opportunity.working_title,
        content_type="guide",
        target_audience=[question.target_audience] if question and question.target_audience else ["general readers"],
        language="en",
        country="global",
        primary_keyword=opportunity.target_keyword,
        secondary_keywords=opportunity.secondary_keywords or [],
        questions=subquestions,
        entities=(question.extracted_entities if question and question.extracted_entities else []),
        primary_intent=question.search_intent if question else "informational",
        secondary_intent=None,
        trend_score=float(opportunity.engagement_momentum_score or 50.0),
        search_demand_score=float(opportunity.search_intent_fit_score or 50.0),
        competition_opportunity_score=float(opportunity.content_gap_score or 50.0),
        site_relevance_score=float(opportunity.website_relevance_score or 50.0),
        topical_authority_score=float(opportunity.website_relevance_score or 50.0),
        freshness_score=85.0,
        evergreen_score=float(opportunity.evergreen_score or 50.0),
        original_value_score=85.0,
        serp_gap_score=float(opportunity.content_gap_score or 50.0),
        monetization_score=20.0,
        cannibalization_risk_score=10.0,
        opportunity_score=float(opportunity.overall_opportunity_score or 50.0),
        confidence_score=float(opportunity.confidence_score or 50.0),
        recommended_action=str(opportunity.recommended_action or "create_new_article").upper(),
        content_gaps=gaps,
        competitor_urls=[],
        existing_related_content=[{"id": str(opportunity.existing_article_match_id), "title": opportunity.existing_article_title}] if opportunity.existing_article_match_id else [],
        risk_flags=[],
        expires_at=None,
        score_explanation=opportunity.score_reasons or [],
    )
