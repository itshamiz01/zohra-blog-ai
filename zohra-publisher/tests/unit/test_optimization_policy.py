"""
Zohra — Part 9 Unit Tests: Optimization Policy, Risk, Hypotheses, Diffs & Content Engines.

Tests:
- Risk Classes A, B, C, and D (Forbidden)
- OptimizationPolicyEngine eligibility, volume gating, age gating, budgets, high-value pages
- Hypothesis formulation: strict fact vs hypothesis separation
- ContentDiffEngine: structural diffs, added/removed paragraphs, links, factual change flag
- TitleOptimizationEngine: multi-candidate generation, anti-clickbait safety, factual consistency
- QueryExpansionEngine: semantic relevance filter, section expansion vs standalone article
- InternalLinkOptimizationEngine: anchor text safety, relevance gating, reverse linking
- ContentConsolidationAnalyzer: cannibalization options, merge vs redirect risk gates
"""

import pytest

from app.db.models.optimization import OptimizationPolicy, RiskClass
from app.optimization.consolidation import (
    ConsolidationAction,
    ContentConsolidationAnalyzer,
    PageCannibalizationData,
)
from app.optimization.diff import ContentDiffEngine
from app.optimization.expansion import ExpansionDecisionType, QueryExpansionEngine
from app.optimization.hypothesis import OptimizationHypothesisEngine
from app.optimization.links import InternalLinkOptimizationEngine
from app.optimization.policy import OptimizationPolicyEngine
from app.optimization.titles import MetaOptimizationEngine, TitleOptimizationEngine


# ── Policy & Risk Tests ───────────────────────────────────────────────

class TestPolicyAndRiskEngine:
    def test_risk_classification(self):
        assert OptimizationPolicyEngine.classify_action("META_DESCRIPTION_REFINE") == RiskClass.CLASS_A
        assert OptimizationPolicyEngine.classify_action("SUBSTANTIAL_TITLE_CHANGE") == RiskClass.CLASS_B
        assert OptimizationPolicyEngine.classify_action("REDIRECT_URL") == RiskClass.CLASS_C
        assert OptimizationPolicyEngine.classify_action("CODE_SELF_REWRITE") == RiskClass.CLASS_D
        assert OptimizationPolicyEngine.classify_action("DISABLE_FACT_CHECKING") == RiskClass.CLASS_D

    def test_class_d_forbidden_actions_rejected(self):
        res = OptimizationPolicyEngine.evaluate_candidate(
            candidate_type="SECURITY_MODIFICATION",
            confidence=0.99,
            evidence={"impressions": 10000, "clicks": 500},
        )
        assert not res.eligible
        assert res.risk_class == RiskClass.CLASS_D
        assert res.is_forbidden
        assert any("Class D" in r for r in res.reasons)

    def test_volume_gating_rejects_insufficient_impressions(self):
        res = OptimizationPolicyEngine.evaluate_candidate(
            candidate_type="CTR_IMPROVEMENT",
            confidence=0.85,
            evidence={"impressions": 10, "clicks": 0},  # Low volume
        )
        assert not res.eligible
        assert any("Impressions" in r for r in res.reasons)

    def test_new_article_protection(self):
        # Article published 2 days ago (< 14 days threshold)
        res = OptimizationPolicyEngine.evaluate_candidate(
            candidate_type="CTR_IMPROVEMENT",
            confidence=0.85,
            evidence={"impressions": 2000, "clicks": 50},
            article_metadata={"age_days": 2},
        )
        assert not res.eligible
        assert any("New article protection" in r for r in res.reasons)

    def test_high_value_page_protection_requires_human_approval(self):
        res = OptimizationPolicyEngine.evaluate_candidate(
            candidate_type="NON_FACTUAL_TITLE_REFINE",  # Class A normally auto-executable
            confidence=0.90,
            evidence={"impressions": 50000, "clicks": 2500},
            article_metadata={"is_high_value_protected": True, "age_days": 60},
        )
        assert res.eligible
        assert res.human_approval_required
        assert not res.auto_execute_allowed
        assert res.high_value_protected

    def test_monthly_change_budget_exhaustion(self):
        res = OptimizationPolicyEngine.evaluate_candidate(
            candidate_type="CTR_IMPROVEMENT",
            confidence=0.85,
            evidence={"impressions": 2000, "clicks": 50},
            article_metadata={"age_days": 45},
            monthly_changes_count=2,  # Max is 2
        )
        assert not res.eligible
        assert not res.budget_available


# ── Hypothesis Engine Tests ───────────────────────────────────────────

class TestHypothesisEngine:
    def test_strict_fact_vs_hypothesis_separation(self):
        hyp = OptimizationHypothesisEngine.generate_hypothesis(
            candidate_type="CTR_IMPROVEMENT",
            observed_problem="Article receives 18,400 impressions with average position 5.8 but CTR is 1.1%.",
            evidence={"impressions": 18400, "avg_position": 5.8, "clicks": 202, "confidence": 0.81},
            affected_queries=["best budget microphones"],
        )
        # Verify observed fact does NOT claim causation
        assert "18,400 impressions" in hyp.observation
        assert "5.8" in hyp.observation
        assert "Google hates" not in hyp.observation
        # Hypothesis explains mechanism
        assert "search snippet" in hyp.hypothesis
        assert hyp.primary_metric == "search_console_ctr"
        assert "impressions" in hyp.guardrail_metrics
        assert "avg_position" in hyp.guardrail_metrics
        assert hyp.confidence >= 0.70


# ── Diff Engine Tests ─────────────────────────────────────────────────

class TestDiffEngine:
    def test_content_diff_computation(self):
        before = {
            "title": "Top Microphones for Podcasting",
            "meta_description": "A guide to podcast mics.",
            "article_body": "Paragraph 1 about mics.\n\nParagraph 2 about XLR interfaces.",
            "headings_json": ["Introduction", "XLR Microphones"],
            "internal_links_json": [{"url": "https://example.com/audio-gear"}],
        }
        after = {
            "title": "Best Microphones for Podcasting (2026 Guide)",
            "meta_description": "Our comprehensive guide to the best podcast microphones.",
            "article_body": "Paragraph 1 about mics.\n\nParagraph 2 about XLR interfaces.\n\nNew section about USB mics.",
            "headings_json": ["Introduction", "XLR Microphones", "USB Microphones"],
            "internal_links_json": [
                {"url": "https://example.com/audio-gear"},
                {"url": "https://example.com/usb-c-audio"},
            ],
        }

        diff = ContentDiffEngine.compute_diff(before, after)
        assert diff.title_changed
        assert diff.old_title == "Top Microphones for Podcasting"
        assert diff.new_title == "Best Microphones for Podcasting (2026 Guide)"
        assert diff.meta_description_changed
        assert "USB Microphones" in diff.headings_added
        assert len(diff.paragraphs_added) == 1
        assert "New section about USB mics." in diff.paragraphs_added[0]
        assert len(diff.internal_links_added) == 1
        assert diff.is_factual_change


# ── Title & Meta Engine Tests ─────────────────────────────────────────

class TestTitleAndMetaEngine:
    def test_anti_clickbait_filter_rejects_deceptive_phrases(self):
        safe, err = TitleOptimizationEngine.check_sensationalism_and_clickbait("Guaranteed Way to Rank #1 on Google")
        assert not safe
        assert "clickbait" in err.lower()

        safe2, err2 = TitleOptimizationEngine.check_sensationalism_and_clickbait("100% Success Secret Google Trick")
        assert not safe2

        safe3, err3 = TitleOptimizationEngine.check_sensationalism_and_clickbait("Practical Guide to Python Performance")
        assert safe3
        assert err3 is None

    def test_factual_consistency_check(self):
        body = "Here are the top tools: Tool A, Tool B, Tool C."
        # Title claims 10 tools, but body only has 3
        safe, err = TitleOptimizationEngine.check_factual_consistency("10 AI Tools We Tested", body)
        assert not safe
        assert "claims 10 items" in err

        # Hands-on claim check
        safe2, err2 = TitleOptimizationEngine.check_factual_consistency("We Tested 3 AI Tools", body)
        assert not safe2
        assert "hands-on testing" in err2

    def test_candidate_generation_and_ranking(self):
        body = "Comprehensive breakdown of wireless earbuds with battery life tests and comparison."
        candidates = TitleOptimizationEngine.generate_and_rank_candidates(
            current_title="Earbuds Guide",
            target_keyword="wireless earbuds",
            dominant_queries=["best wireless earbuds"],
            article_body=body,
        )
        assert len(candidates) >= 3
        # Best ranked candidate must be safe
        assert candidates[0].is_safe
        assert candidates[0].composite_score > 0.50

    def test_meta_description_generation(self):
        meta = MetaOptimizationEngine.generate_meta_description(
            target_keyword="remote work tools",
            dominant_queries=["best remote work tools"],
            article_summary="Essential collaboration tools for distributed teams.",
        )
        assert meta.character_count <= 160
        assert meta.includes_target_keyword
        assert meta.is_safe


# ── Query Expansion Tests ─────────────────────────────────────────────

class TestQueryExpansionEngine:
    def test_irrelevant_query_rejected_as_keyword_stuffing(self):
        eval_res = QueryExpansionEngine.evaluate_query_for_expansion(
            rising_query="cheap refrigerator repair in dallas",
            impressions=5000,
            article_title="Python Asyncio Best Practices",
            article_topic="Python Programming",
            article_body="Asyncio event loops and tasks in Python 3.12...",
        )
        assert eval_res.decision == ExpansionDecisionType.NO_ACTION_RELEVANCE_TOO_LOW
        assert "Rejecting to prevent keyword stuffing" in eval_res.reason

    def test_high_volume_distinct_intent_spawns_new_article(self):
        eval_res = QueryExpansionEngine.evaluate_query_for_expansion(
            rising_query="fastapi vs django pricing and performance",
            impressions=2500,
            article_title="Complete Guide to FastAPI",
            article_topic="FastAPI Web Framework",
            article_body="Building high performance REST APIs with FastAPI...",
        )
        assert eval_res.decision == ExpansionDecisionType.CREATE_NEW_ARTICLE
        assert "Standalone new article" in eval_res.reason

    def test_relevant_query_generates_section_expansion_plan(self):
        eval_res = QueryExpansionEngine.evaluate_query_for_expansion(
            rising_query="fastapi background tasks error handling",
            impressions=800,
            article_title="Complete Guide to FastAPI",
            article_topic="FastAPI Web Framework",
            article_body="Building high performance REST APIs with FastAPI...",
        )
        assert eval_res.decision == ExpansionDecisionType.EXPAND_SECTION
        assert eval_res.section_plan is not None
        assert "Background Tasks" in eval_res.section_plan.heading
        assert len(eval_res.section_plan.questions_answered) > 0


# ── Internal Link Engine Tests ────────────────────────────────────────

class TestInternalLinkEngine:
    def test_anchor_text_safety(self):
        # 1-word anchor rejected
        safe1, err1 = InternalLinkOptimizationEngine.validate_anchor_text_safety("microphones", "microphones")
        assert not safe1

        # Generic anchor rejected
        safe2, err2 = InternalLinkOptimizationEngine.validate_anchor_text_safety("click here", "audio tools")
        assert not safe2
        assert "overly generic" in err2.lower()

        # Natural descriptive anchor accepted
        safe3, err3 = InternalLinkOptimizationEngine.validate_anchor_text_safety("best podcast microphones guide", "podcast microphones")
        assert safe3
        assert err3 is None

    def test_irrelevant_link_rejection(self):
        sources = [
            {"id": "src-1", "title": "Vegan Baking Recipes", "topic": "Food & Cooking"},
            {"id": "src-2", "title": "Home Recording Studio Setup", "topic": "Audio Production"},
        ]
        recs = InternalLinkOptimizationEngine.find_reverse_link_opportunities(
            new_article_id="target-1",
            new_article_title="Best Podcast Microphones",
            new_article_topic="Audio Production",
            new_article_url="https://example.com/podcast-mics",
            candidate_source_articles=sources,
            min_relevance=0.50,
        )
        # Vegan Baking should be filtered out
        assert len(recs) == 1
        assert recs[0].source_article_id == "src-2"
        assert recs[0].relevance_score >= 0.50


# ── Content Consolidation Tests ───────────────────────────────────────

class TestContentConsolidationAnalyzer:
    def test_cannibalization_with_dominant_page_differentiates(self):
        pages = [
            PageCannibalizationData(article_id="p1", url="/best-laptops", title="Best Laptops", clicks=95, impressions=4000, avg_position=4.2),
            PageCannibalizationData(article_id="p2", url="/cheap-laptops", title="Budget Laptops", clicks=2, impressions=450, avg_position=16.8),
        ]
        plan = ContentConsolidationAnalyzer.analyze_cannibalization("best laptops", pages)
        assert plan.recommended_action == ConsolidationAction.DIFFERENTIATE
        assert not plan.human_approval_required
        assert plan.primary_article_id == "p1"

    def test_severe_cannibalization_requires_merge_and_approval(self):
        pages = [
            PageCannibalizationData(article_id="p1", url="/seo-guide", title="SEO Guide", clicks=120, impressions=5000, avg_position=6.1),
            PageCannibalizationData(article_id="p2", url="/search-engine-optimization", title="Search Optimization", clicks=95, impressions=4200, avg_position=7.4),
        ]
        plan = ContentConsolidationAnalyzer.analyze_cannibalization("seo guide", pages)
        assert plan.recommended_action == ConsolidationAction.MERGE
        assert plan.risk_class == RiskClass.CLASS_C
        assert plan.human_approval_required
