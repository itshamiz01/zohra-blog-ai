"""Unit tests for SearchIntentClassifier & Intent Specificity Strength."""

import pytest

from app.core.constants import SearchIntent
from app.opportunity.intent.classifier import SearchIntentClassifier


@pytest.fixture
def classifier():
    return SearchIntentClassifier()


def test_classify_tutorial_intent(classifier):
    res = classifier.classify("how to use model x for beginners")
    assert res.primary_intent == SearchIntent.TUTORIAL
    assert res.confidence >= 0.75
    assert res.intent_strength_score >= 80.0


def test_classify_comparison_intent(classifier):
    res = classifier.classify("ChatGPT vs Gemini for coding")
    assert res.primary_intent == SearchIntent.COMPARISON
    assert res.secondary_intent == SearchIntent.COMMERCIAL_INVESTIGATION
    assert res.confidence >= 0.80


def test_classify_commercial_pricing_intent(classifier):
    res = classifier.classify("Claude Pro pricing tiers and monthly cost")
    assert res.primary_intent == SearchIntent.COMMERCIAL_INVESTIGATION
    assert res.intent_strength_score >= 85.0


def test_classify_troubleshooting_intent(classifier):
    res = classifier.classify("OpenAI API rate limit error fix not working")
    assert res.primary_intent == SearchIntent.TROUBLESHOOTING
    assert res.intent_strength_score >= 85.0


def test_classify_navigational_intent(classifier):
    res = classifier.classify("ChatGPT official login portal")
    assert res.primary_intent == SearchIntent.NAVIGATIONAL


def test_intent_strength_specificity_progression(classifier):
    vague = classifier.calculate_intent_strength("AI", SearchIntent.INFORMATIONAL)
    broad = classifier.calculate_intent_strength("AI video tools", SearchIntent.COMMERCIAL_INVESTIGATION)
    specific = classifier.calculate_intent_strength(
        "best AI tools for YouTube automation beginners", SearchIntent.COMMERCIAL_INVESTIGATION
    )

    assert vague < broad < specific
    assert vague <= 35.0
    assert specific >= 85.0


def test_serp_intent_validation_override(classifier):
    # When SERP is dominated by official login portal, overrides predicted informational intent
    corrected_intent, conf, reason = classifier.validate_with_serp(
        initial_intent=SearchIntent.INFORMATIONAL,
        top_domains=["openai.com", "openai.com", "auth.openai.com"],
        result_types=["organic", "organic", "organic"],
        is_official_dominant=True,
    )
    assert corrected_intent == SearchIntent.NAVIGATIONAL
    assert conf >= 0.90
    assert "official_portal" in reason
