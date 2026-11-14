"""
Unit tests for Coverage Analyzer, Stop Conditions, and Research Quality Scorer.
"""

from __future__ import annotations

from app.research.coverage.analyzer import CoverageAnalyzer
from app.research.quality.scorer import ResearchQualityScorer


def test_coverage_analyzer_weights_critical_questions_heavily():
    questions = [
        {"id": "q1", "question": "What is the core price?", "priority": "CRITICAL", "requires_primary_source": True},
        {"id": "q2", "question": "What year was the company founded?", "priority": "LOW"},
        {"id": "q3", "question": "Who is the designer?", "priority": "LOW"},
    ]

    # Only minor questions answered, critical pricing question unanswered
    claims = [
        {"claim_text": "The company was founded in 2020.", "predicate": "product"},
        {"claim_text": "The designer is John Doe.", "predicate": "product"},
    ]

    eval_res = CoverageAnalyzer.evaluate_coverage(questions=questions, claims=claims)
    # Critical coverage must be 0%
    assert eval_res.critical_claim_coverage_score == 0.0
    # Overall coverage heavily dragged down by missing critical question
    assert eval_res.coverage_score < 40.0
    assert len(eval_res.gaps) >= 1
    assert eval_res.gaps[0]["gap_type"] == "no_source"


def test_coverage_analyzer_stop_conditions_budget_and_expiration():
    questions = [{"id": "q1", "question": "What is X?", "priority": "MEDIUM"}]
    claims = []

    # Budget exhausted
    eval_budget = CoverageAnalyzer.evaluate_coverage(
        questions=questions, claims=claims, actual_cost=6.0, budget_limit=5.0
    )
    assert eval_budget.should_stop is True
    assert eval_budget.stop_reason == "budget_exhausted"

    # Opportunity expired
    eval_exp = CoverageAnalyzer.evaluate_coverage(
        questions=questions, claims=claims, is_expired=True
    )
    assert eval_exp.should_stop is True
    assert eval_exp.stop_reason == "opportunity_expired"


def test_research_quality_scorer_gate_pass_and_high_risk():
    standard_res = ResearchQualityScorer.evaluate_quality(
        coverage_score=85.0,
        critical_claim_coverage_score=90.0,
        source_quality_score=85.0,
        primary_source_coverage=80.0,
        corroboration_score=80.0,
        freshness_score=85.0,
        is_high_risk=False,
    )
    assert standard_res.research_quality_score >= 80.0
    assert standard_res.quality_gate_status in ("PASS", "STRONG", "EXCEPTIONAL")
    assert standard_res.needs_human_review is False

    # High-risk topic with unresolved critical contradiction gets penalized and flagged
    high_risk_res = ResearchQualityScorer.evaluate_quality(
        coverage_score=75.0,
        critical_claim_coverage_score=70.0,
        source_quality_score=75.0,
        primary_source_coverage=60.0,
        corroboration_score=60.0,
        freshness_score=70.0,
        has_unresolved_critical_contradictions=True,
        unresolved_contradictions_count=1,
        is_high_risk=True,
    )
    # Penalty deducted
    assert high_risk_res.total_penalties >= 15.0
    # High-risk threshold is 90.0 -> must require human review
    assert high_risk_res.needs_human_review is True
