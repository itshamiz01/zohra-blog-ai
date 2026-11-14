"""
Zohra — Part 8 Unit Tests: Search Analytics & Performance Intelligence.

Tests:
- URL normalization and slug extraction
- Query normalization and intent classification
- CTR benchmark calculation and diagnostics
- Ranking intelligence: trends, page-2 detection, near-top detection
- Anomaly detection with significance gates
- Cannibalization detection
- Performance diagnostics engine (observation vs. hypothesis)
- Optimization candidate generation
- Position band assignment
- Lifecycle stage classification
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.analytics.anomaly_detector import (
    detect_metric_anomaly,
    detect_site_vs_page_anomaly,
)
from app.analytics.cannibalization import detect_cannibalization
from app.analytics.ctr_benchmark import (
    calculate_ctr_benchmark,
    diagnose_ctr,
    position_to_band,
)
from app.analytics.diagnostic import build_diagnostic
from app.analytics.opportunity_generator import (
    generate_candidate_id,
    generate_cannibalization_opportunity,
    generate_low_ctr_opportunity,
    generate_page2_opportunity,
    prioritize_candidates,
)
from app.analytics.query_classifier import (
    classify_intent,
    classify_query,
    normalize_query,
)
from app.analytics.ranking import (
    calculate_position_volatility,
    classify_lifecycle_stage,
    compute_ranking_trend,
    detect_near_top_opportunities,
    detect_page2_opportunities,
)
from app.analytics.url_normalizer import extract_slug_from_url, normalize_url
from app.schemas.analytics import (
    OpportunityCandidateType,
    PositionBand,
    SearchIntent,
    VisibilityTrend,
)


# ── URL Normalization Tests ──────────────────────────────────────────

class TestURLNormalization:
    def test_strips_trailing_slash(self):
        assert normalize_url("https://example.com/blog/post/") == "https://example.com/blog/post"

    def test_preserves_root_path(self):
        assert normalize_url("https://example.com/") == "https://example.com/"

    def test_lowercases_scheme_and_host(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Blog") == "https://example.com/Blog"

    def test_removes_query_string(self):
        assert normalize_url("https://example.com/post?utm_source=twitter") == "https://example.com/post"

    def test_removes_fragment(self):
        assert normalize_url("https://example.com/post#section-1") == "https://example.com/post"

    def test_removes_both_query_and_fragment(self):
        result = normalize_url("https://example.com/post?a=1#top")
        assert result == "https://example.com/post"

    def test_empty_path_normalizes_to_root(self):
        assert normalize_url("https://example.com") == "https://example.com/"

    def test_extract_slug_from_typical_url(self):
        assert extract_slug_from_url("https://example.com/blog/ai-content-strategy") == "ai-content-strategy"

    def test_extract_slug_from_root_returns_none(self):
        assert extract_slug_from_url("https://example.com/") is None

    def test_extract_slug_strips_trailing_slash(self):
        assert extract_slug_from_url("https://example.com/blog/my-post/") == "my-post"


# ── Query Classification Tests ───────────────────────────────────────

class TestQueryClassification:
    def test_normalizes_whitespace(self):
        assert normalize_query("  how  to  build   a   blog  ") == "how to build a blog"

    def test_lowercases(self):
        assert normalize_query("SEO Best Practices") == "seo best practices"

    def test_removes_special_chars(self):
        assert normalize_query("what's the best SEO tool?") == "whats the best seo tool"

    def test_preserves_hyphens(self):
        assert normalize_query("long-tail keywords") == "long-tail keywords"

    def test_classify_informational(self):
        assert classify_intent("how to optimize content for SEO") == SearchIntent.INFORMATIONAL

    def test_classify_transactional(self):
        assert classify_intent("buy seo tools subscription") == SearchIntent.TRANSACTIONAL

    def test_classify_commercial(self):
        assert classify_intent("best seo tools 2026 review") == SearchIntent.COMMERCIAL

    def test_classify_navigational_short_query(self):
        assert classify_intent("google analytics") == SearchIntent.NAVIGATIONAL

    def test_classify_local(self):
        assert classify_intent("seo agency near me") == SearchIntent.LOCAL

    def test_full_classification_pipeline(self):
        result = classify_query("how to improve blog SEO", brand_terms=["zohra"])
        assert result.normalized_query == "how to improve blog seo"
        assert result.intent == SearchIntent.INFORMATIONAL
        assert result.is_branded is False
        assert result.word_count == 5

    def test_branded_query_detection(self):
        result = classify_query("zohra ai content platform", brand_terms=["zohra"])
        assert result.is_branded is True


# ── Position Band Tests ──────────────────────────────────────────────

class TestPositionBands:
    def test_top_1(self):
        assert position_to_band(1.0) == PositionBand.TOP_1

    def test_top_3(self):
        assert position_to_band(2.5) == PositionBand.TOP_3

    def test_top_5(self):
        assert position_to_band(4.0) == PositionBand.TOP_5

    def test_top_10(self):
        assert position_to_band(8.0) == PositionBand.TOP_10

    def test_page_2(self):
        assert position_to_band(15.0) == PositionBand.PAGE_2

    def test_page_3_plus(self):
        assert position_to_band(25.0) == PositionBand.PAGE_3_PLUS

    def test_none_position(self):
        assert position_to_band(None) == PositionBand.NOT_RANKING


# ── CTR Benchmark Tests ─────────────────────────────────────────────

class TestCTRBenchmark:
    def test_empty_values(self):
        result = calculate_ctr_benchmark([])
        assert result["sample_size"] == 0
        assert result["avg_ctr"] == 0.0

    def test_single_value(self):
        result = calculate_ctr_benchmark([0.05])
        assert result["sample_size"] == 1
        assert result["avg_ctr"] == 0.05

    def test_multiple_values(self):
        result = calculate_ctr_benchmark([0.02, 0.04, 0.06, 0.08, 0.10])
        assert result["sample_size"] == 5
        assert result["avg_ctr"] == 0.06
        assert result["median_ctr"] == 0.06

    def test_ctr_diagnosis_underperforming(self):
        result = diagnose_ctr(
            url="https://example.com/test",
            actual_ctr=0.01,
            avg_position=3.0,
            impressions=200,
            benchmark_avg_ctr=0.05,
            benchmark_median_ctr=0.04,
        )
        assert result.underperforming is True
        assert result.ctr_ratio is not None
        assert result.ctr_ratio < 1.0

    def test_ctr_diagnosis_acceptable(self):
        result = diagnose_ctr(
            url="https://example.com/good",
            actual_ctr=0.04,
            avg_position=3.0,
            impressions=200,
            benchmark_avg_ctr=0.05,
            benchmark_median_ctr=0.04,
        )
        assert result.underperforming is False

    def test_insufficient_impressions(self):
        result = diagnose_ctr(
            url="https://example.com/new",
            actual_ctr=0.01,
            avg_position=3.0,
            impressions=10,
            benchmark_avg_ctr=0.05,
            benchmark_median_ctr=0.04,
            min_impressions=50,
        )
        assert result.sample_size_sufficient is False
        # Don't flag as underperforming with insufficient data
        assert result.underperforming is False


# ── Ranking Intelligence Tests ───────────────────────────────────────

class TestRankingIntelligence:
    def test_ranking_trend_rising(self):
        trend = compute_ranking_trend(
            url="https://example.com/post",
            query="test query",
            current_position=5.0,
            previous_position=12.0,
            current_clicks=50,
            previous_clicks=20,
        )
        assert trend.trend == VisibilityTrend.RISING
        assert trend.position_delta < 0  # Position decreased = ranking improved

    def test_ranking_trend_declining(self):
        trend = compute_ranking_trend(
            url="https://example.com/post",
            query="test",
            current_position=15.0,
            previous_position=5.0,
            current_clicks=5,
            previous_clicks=50,
        )
        assert trend.trend == VisibilityTrend.DECLINING

    def test_ranking_trend_stable(self):
        trend = compute_ranking_trend(
            url="https://example.com/post",
            query="test",
            current_position=5.0,
            previous_position=5.5,
            current_clicks=50,
            previous_clicks=48,
        )
        assert trend.trend == VisibilityTrend.STABLE

    def test_page2_opportunity_detection(self):
        metrics = [
            {
                "article_id": uuid.uuid4(),
                "url": "https://example.com/post",
                "query": "seo tips",
                "avg_position": 12.0,
                "impressions": 100,
                "clicks": 3,
            },
            {
                "article_id": uuid.uuid4(),
                "url": "https://example.com/already-page1",
                "query": "good query",
                "avg_position": 5.0,
                "impressions": 200,
                "clicks": 40,
            },
        ]
        opps = detect_page2_opportunities(metrics)
        assert len(opps) == 1
        assert opps[0].avg_position == 12.0

    def test_near_top_opportunity_detection(self):
        metrics = [
            {
                "article_id": uuid.uuid4(),
                "url": "https://example.com/close",
                "query": "almost there",
                "avg_position": 5.5,
                "impressions": 500,
                "clicks": 30,
            },
        ]
        opps = detect_near_top_opportunities(metrics)
        assert len(opps) == 1
        assert opps[0].distance_to_top3 == 2.5

    def test_position_volatility_stable(self):
        # Very stable positions
        positions = [5.0, 5.1, 4.9, 5.0, 5.2, 4.8, 5.0]
        vol = calculate_position_volatility(positions)
        assert vol < 0.5

    def test_position_volatility_high(self):
        positions = [3.0, 15.0, 5.0, 20.0, 2.0, 18.0, 4.0]
        vol = calculate_position_volatility(positions)
        assert vol > 5.0

    def test_position_volatility_insufficient_data(self):
        assert calculate_position_volatility([5.0, 5.0]) == 0.0


# ── Lifecycle Stage Tests ────────────────────────────────────────────

class TestLifecycleStage:
    def test_new_article(self):
        assert classify_lifecycle_stage(3, 0, None) == "NEW"

    def test_ramping_article(self):
        assert classify_lifecycle_stage(15, 50, None) == "RAMPING"

    def test_established_article(self):
        assert classify_lifecycle_stage(60, 500, 0.1) == "ESTABLISHED"

    def test_declining_article(self):
        assert classify_lifecycle_stage(100, 200, -0.5) == "DECLINING"

    def test_dormant_article(self):
        assert classify_lifecycle_stage(200, 0, None) == "DORMANT"


# ── Anomaly Detection Tests ──────────────────────────────────────────

class TestAnomalyDetection:
    def test_detects_significant_drop(self):
        site_id = uuid.uuid4()
        baseline = [100.0] * 28  # Stable baseline of 100 clicks/day
        result = detect_metric_anomaly(
            metric_name="clicks",
            observed_value=30.0,
            baseline_values=baseline,
            site_id=site_id,
            min_baseline_points=7,
            min_volume=10,
            current_volume=30,
        )
        assert result is not None
        assert result["percentage_change"] < 0
        assert result["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_no_anomaly_for_normal_variation(self):
        site_id = uuid.uuid4()
        baseline = [100.0 + i * 2 for i in range(28)]  # Gradual growth
        result = detect_metric_anomaly(
            metric_name="clicks",
            observed_value=130.0,
            baseline_values=baseline,
            site_id=site_id,
            min_volume=10,
            current_volume=130,
        )
        # Within 2 std devs should not trigger
        assert result is None

    def test_insufficient_baseline_returns_none(self):
        site_id = uuid.uuid4()
        result = detect_metric_anomaly(
            metric_name="clicks",
            observed_value=10.0,
            baseline_values=[100.0, 100.0],
            site_id=site_id,
            min_baseline_points=7,
            min_volume=10,
            current_volume=10,
        )
        assert result is None

    def test_volume_gate_filters_low_volume(self):
        site_id = uuid.uuid4()
        baseline = [100.0] * 28
        result = detect_metric_anomaly(
            metric_name="clicks",
            observed_value=5.0,
            baseline_values=baseline,
            site_id=site_id,
            min_volume=50,
            current_volume=5,
        )
        assert result is None

    def test_site_wide_scope_adjustment(self):
        site_anomaly = {
            "percentage_change": -50.0,
            "possible_scope": "SITE_WIDE",
        }
        page_anomalies = [
            {
                "percentage_change": -40.0,
                "possible_scope": "PAGE_SPECIFIC",
            },
        ]
        adjusted = detect_site_vs_page_anomaly(page_anomalies, site_anomaly)
        assert adjusted[0]["possible_scope"] == "SITE_WIDE"


# ── Cannibalization Detection Tests ──────────────────────────────────

class TestCannibalizationDetection:
    def test_detects_basic_cannibalization(self):
        art1 = uuid.uuid4()
        art2 = uuid.uuid4()
        metrics = [
            {
                "query": "seo tips",
                "normalized_query": "seo tips",
                "url": "https://example.com/seo-guide",
                "article_id": art1,
                "clicks": 10,
                "impressions": 100,
                "avg_position": 5.0,
                "date": "2026-09-01",
            },
            {
                "query": "seo tips",
                "normalized_query": "seo tips",
                "url": "https://example.com/seo-advanced",
                "article_id": art2,
                "clicks": 5,
                "impressions": 80,
                "avg_position": 8.0,
                "date": "2026-09-01",
            },
        ]
        events = detect_cannibalization(metrics)
        assert len(events) == 1
        assert len(events[0]["article_ids"]) == 2

    def test_no_cannibalization_single_page(self):
        art1 = uuid.uuid4()
        metrics = [
            {
                "query": "unique query",
                "normalized_query": "unique query",
                "url": "https://example.com/unique",
                "article_id": art1,
                "clicks": 50,
                "impressions": 200,
                "avg_position": 3.0,
                "date": "2026-09-01",
            },
        ]
        events = detect_cannibalization(metrics)
        assert len(events) == 0

    def test_insufficient_impressions_filtered(self):
        art1 = uuid.uuid4()
        art2 = uuid.uuid4()
        metrics = [
            {
                "query": "rare query",
                "normalized_query": "rare query",
                "url": "https://example.com/a",
                "article_id": art1,
                "clicks": 0,
                "impressions": 5,
                "avg_position": 15.0,
                "date": "2026-09-01",
            },
            {
                "query": "rare query",
                "normalized_query": "rare query",
                "url": "https://example.com/b",
                "article_id": art2,
                "clicks": 0,
                "impressions": 3,
                "avg_position": 20.0,
                "date": "2026-09-01",
            },
        ]
        events = detect_cannibalization(metrics, min_impressions=20)
        assert len(events) == 0


# ── Performance Diagnostics Tests ────────────────────────────────────

class TestDiagnosticEngine:
    def test_produces_observed_facts(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 100, "impressions": 5000, "ctr": 0.02, "avg_position": 8.5},
        )
        assert len(diag.observed_facts) > 0
        assert any("impressions" in f.lower() for f in diag.observed_facts)

    def test_clearly_labels_hypotheses(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 5, "impressions": 200, "ctr": 0.025, "avg_position": 15.0},
        )
        # Hypotheses should be explicitly labeled
        for h in diag.hypotheses:
            assert "HYPOTHESIS" in h

    def test_includes_data_quality_caveats(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 2, "impressions": 30, "ctr": 0.067, "avg_position": 12.0},
        )
        assert len(diag.data_quality_caveats) > 0
        assert any("sample size" in c.lower() or "lag" in c.lower() for c in diag.data_quality_caveats)

    def test_zero_impressions_diagnosis(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 0, "impressions": 0, "ctr": None, "avg_position": None},
        )
        assert any("zero" in f.lower() for f in diag.observed_facts)

    def test_indexing_issue_generates_hypothesis(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 0, "impressions": 0, "ctr": None, "avg_position": None},
            indexing_status="NOT_INDEXED",
        )
        assert any("NOT_INDEXED" in h for h in diag.hypotheses)

    def test_anomaly_data_included_in_observations(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 10, "impressions": 500, "ctr": 0.02, "avg_position": 8.0},
            anomalies=[
                {
                    "metric": "clicks",
                    "percentage_change": -45.0,
                    "severity": "HIGH",
                }
            ],
        )
        assert any("anomaly" in f.lower() for f in diag.observed_facts)

    def test_cannibalization_data_included(self):
        diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 20, "impressions": 500, "ctr": 0.04, "avg_position": 7.0},
            cannibalization=[
                {
                    "query": "seo tips",
                    "article_ids": ["a", "b"],
                    "ownership_switch_count": 3,
                }
            ],
        )
        assert any("cannibalization" in f.lower() for f in diag.observed_facts)

    def test_confidence_level_scales_with_data(self):
        # Low data = LOW confidence
        low_diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 1, "impressions": 10, "ctr": 0.1, "avg_position": 5.0},
        )
        assert low_diag.confidence_level == "LOW"

        # High data = HIGH confidence
        high_diag = build_diagnostic(
            article_id=uuid.uuid4(),
            metrics={"clicks": 200, "impressions": 5000, "ctr": 0.04, "avg_position": 5.0},
            anomalies=[{"metric": "clicks", "percentage_change": -20.0, "severity": "MEDIUM"}],
        )
        assert high_diag.confidence_level == "HIGH"


# ── Optimization Candidate Generation Tests ──────────────────────────

class TestOpportunityGeneration:
    def test_candidate_id_deterministic(self):
        sid = uuid.uuid4()
        aid = uuid.uuid4()
        id1 = generate_candidate_id(sid, aid, "LOW_CTR", "seo tips")
        id2 = generate_candidate_id(sid, aid, "LOW_CTR", "seo tips")
        assert id1 == id2

    def test_candidate_id_varies_by_type(self):
        sid = uuid.uuid4()
        aid = uuid.uuid4()
        id1 = generate_candidate_id(sid, aid, "LOW_CTR", "seo tips")
        id2 = generate_candidate_id(sid, aid, "PAGE_2_OPPORTUNITY", "seo tips")
        assert id1 != id2

    def test_generate_low_ctr_opportunity(self):
        opp = generate_low_ctr_opportunity(
            site_id=uuid.uuid4(),
            article_id=uuid.uuid4(),
            url="https://example.com/test",
            actual_ctr=0.01,
            benchmark_avg_ctr=0.05,
            avg_position=5.0,
            impressions=500,
            clicks=5,
            query="test query",
        )
        assert opp.candidate_type == OpportunityCandidateType.LOW_CTR
        assert opp.priority_score > 0
        assert opp.observed_problem
        assert len(opp.possible_causes) > 0
        assert len(opp.recommended_investigation) > 0

    def test_generate_page2_opportunity(self):
        opp = generate_page2_opportunity(
            site_id=uuid.uuid4(),
            article_id=uuid.uuid4(),
            url="https://example.com/post",
            query="seo tips",
            avg_position=13.5,
            impressions=200,
            clicks=5,
        )
        assert opp.candidate_type == OpportunityCandidateType.PAGE_2_OPPORTUNITY
        assert "page 2" in opp.observed_problem.lower() or "position" in opp.observed_problem.lower()

    def test_generate_cannibalization_opportunity(self):
        opp = generate_cannibalization_opportunity(
            site_id=uuid.uuid4(),
            primary_article_id=uuid.uuid4(),
            query="seo best practices",
            competing_article_ids=["a", "b", "c"],
            impressions=1000,
            clicks=50,
            ownership_switch_count=5,
        )
        assert opp.candidate_type == OpportunityCandidateType.CANNIBALIZATION
        assert opp.confidence > 0.4

    def test_prioritize_candidates(self):
        candidates = [
            generate_low_ctr_opportunity(
                site_id=uuid.uuid4(),
                article_id=uuid.uuid4(),
                url=f"https://example.com/post-{i}",
                actual_ctr=0.01,
                benchmark_avg_ctr=0.05,
                avg_position=5.0,
                impressions=100 * (i + 1),
                clicks=i,
                query=f"query {i}",
            )
            for i in range(10)
        ]
        prioritized = prioritize_candidates(candidates, max_candidates=3)
        assert len(prioritized) == 3
        # Should be sorted by priority (highest first)
        assert prioritized[0].priority_score >= prioritized[1].priority_score
