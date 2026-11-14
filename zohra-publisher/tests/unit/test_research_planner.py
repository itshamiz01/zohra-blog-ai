"""
Unit tests for Research Planner and Question Decomposer.
"""

from __future__ import annotations

import pytest

from app.research.planner.decomposer import ResearchPlanner
from app.schemas.opportunity import ContentOpportunityPackage
from app.schemas.research import QuestionPriority, QuestionType


@pytest.fixture
def base_package() -> ContentOpportunityPackage:
    return ContentOpportunityPackage(
        opportunity_id="00000000-0000-0000-0000-000000000001",
        event_id="00000000-0000-0000-0000-000000000002",
        site_id="00000000-0000-0000-0000-000000000003",
        topic="Model X Video Generator",
        proposed_angle="Complete step-by-step tutorial for creators",
        working_title="How to Use Model X Video Generator",
        content_type="tutorial",
        target_audience=["Video editors", "Creators"],
        language="en",
        country="US",
        primary_keyword="how to use model x",
        secondary_keywords=["model x tutorial", "model x settings"],
        questions=["How much does Model X cost?", "Does Model X support 4K export?"],
        entities=["Model X", "Runway Gen-2"],
        primary_intent="tutorial",
        trend_score=85.0,
        search_demand_score=82.0,
        competition_opportunity_score=75.0,
        site_relevance_score=95.0,
        topical_authority_score=70.0,
        freshness_score=90.0,
        evergreen_score=80.0,
        original_value_score=85.0,
        serp_gap_score=80.0,
        monetization_score=70.0,
        cannibalization_risk_score=15.0,
        opportunity_score=88.0,
        confidence_score=85.0,
        recommended_action="CREATE",
    )


def test_planner_generates_goal_driven_questions(base_package):
    planner = ResearchPlanner()
    questions = planner.plan_research(base_package, research_depth="STANDARD")

    assert len(questions) >= 6
    # Must contain definition question
    assert any(q.question_type == QuestionType.DEFINITION for q in questions)
    # Tutorial must have process question as CRITICAL
    process_q = next((q for q in questions if q.question_type == QuestionType.PROCESS), None)
    assert process_q is not None
    assert process_q.priority == QuestionPriority.CRITICAL
    assert process_q.requires_primary_source is True

    # Pricing question present
    pricing_q = next((q for q in questions if q.question_type == QuestionType.PRICING), None)
    assert pricing_q is not None


def test_planner_comparison_intent_decomposes_features_and_benchmarks(base_package):
    base_package.content_type = "comparison"
    planner = ResearchPlanner()
    questions = planner.plan_research(base_package, research_depth="STANDARD")

    comp_q = next((q for q in questions if q.question_type == QuestionType.COMPARISON), None)
    assert comp_q is not None
    assert comp_q.priority == QuestionPriority.CRITICAL
    assert comp_q.requires_multiple_sources is True


def test_planner_queries_have_language_and_country(base_package):
    base_package.country = "India"
    planner = ResearchPlanner()
    questions = planner.plan_research(base_package, research_depth="STANDARD")

    for q in questions:
        for qy in q.queries:
            assert qy["country"] == "India"
            assert qy["language"] == "en"
            assert len(qy["query"]) > 5
