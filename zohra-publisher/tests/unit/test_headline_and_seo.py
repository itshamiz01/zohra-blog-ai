"""
Unit tests for HeadlineEngine, SemanticSEOOptimizer, and AISlopDetector (Part 5).
"""

from __future__ import annotations

from app.editorial.headline.engine import HeadlineEngine
from app.editorial.seo.anti_slop import AISlopDetector
from app.editorial.seo.optimizer import SemanticSEOOptimizer
from app.schemas.editorial import ContentStrategyData


def test_headline_engine_scoring_and_clickbait_penalty():
    strat = ContentStrategyData(
        reader_problem="Understand pricing",
        reader_goal="Find plans",
        search_intent="commercial_investigation",
        content_goal="Explain pricing",
        recommended_content_type="pricing",
        angle="Pricing guide",
        differentiation_strategy="Verified pricing",
        information_gain_strategy="Direct tables",
        tone="professional",
        depth="comprehensive",
        target_length_min=1000,
        target_length_max=1800,
    )
    candidates = HeadlineEngine.generate_candidates(
        topic="Model X",
        primary_keyword="model x pricing",
        strategy=strat,
    )
    assert len(candidates) >= 4
    # The selected winning headline must have selected=True and no clickbait
    selected = next((c for c in candidates if c.selected), None)
    assert selected is not None
    assert selected.overall_score >= 70.0

    # Test clickbait penalty
    clickbait_scores = HeadlineEngine.score_headline(
        headline="SHOCKING: Model X Will Destroy YouTube Creators Forever!",
        primary_keyword="model x",
        strategy=strat,
    )
    assert clickbait_scores["overall_score"] < 50.0


def test_ai_slop_detector():
    clean_text = "Model X was officially launched in October 2026. The standard plan costs $20 per month and includes 100 generations."
    clean_eval = AISlopDetector.evaluate(clean_text)
    assert clean_eval["slop_penalty"] == 0.0
    assert clean_eval["slop_count"] == 0

    slop_text = "In today's fast-paced world, whether you're a beginner or expert, let's dive into this game-changer tool."
    slop_eval = AISlopDetector.evaluate(slop_text)
    assert slop_eval["slop_penalty"] > 20.0
    assert slop_eval["slop_count"] >= 3

    cleansed = AISlopDetector.cleanse_slop(slop_text)
    assert "In today's fast-paced world" not in cleansed
    assert "let's dive in" not in cleansed


def test_semantic_seo_optimizer():
    slug = SemanticSEOOptimizer.generate_slug("Model X Video Engine: Complete Guide for Creators", "model x guide")
    assert slug == "model-x-guide"
    assert " " not in slug

    meta_title = SemanticSEOOptimizer.generate_meta_title("Model X Pricing & Plans: Full Breakdown and Hidden Limits", "model x pricing")
    assert len(meta_title) <= 65

    meta_desc = SemanticSEOOptimizer.generate_meta_description("Model X", "model x pricing", "Understand current costs and plan limits.")
    assert 120 <= len(meta_desc) <= 160

    realistic_content = (
        "# Model X: Complete Guide\n\n"
        "Model X is an advanced video generation engine designed for high-resolution content production. "
        "Creators evaluating this tool will discover a wide range of documented capabilities and structured workflows. "
        "\n\n## Core Features & Technical Capabilities\n\n"
        "The software architecture supports 4K rendering output with dedicated hardware acceleration. "
        "In addition, batch processing enables practitioners to queue multiple video clips simultaneously. "
        "\n\n## Pricing Plans & Tier Breakdown\n\n"
        "Official pricing tiers start with standard creator access. Monthly costs remain predictable without hidden limits. "
        "Users can scale their usage based on monthly project demands."
    )
    score = SemanticSEOOptimizer.calculate_seo_content_score(
        title="Model X: Complete Guide",
        content=realistic_content,
        primary_keyword="model x",
        has_faq=True,
        has_table=True,
    )
    assert score >= 75.0
