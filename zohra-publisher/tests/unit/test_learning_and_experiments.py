"""
Zohra — Part 9 Unit Tests: Experimentation, Learning, Strategy Memory, Portfolio & Forecasting.

Tests:
- ExperimentEngine: positive, negative, inconclusive, site trend adjustment, confounder detection
- ZohraLearningEngine: prediction calibration, memory synthesis, memory decay, contradiction handling, viral outliers
- StrategyParameterController: 25% step rate limit, boundary clamping, rollback value tracking
- StrategyVersionManager: shadow mode, promotion to active, rollback to previous version
- StrategyAllocationEngine: portfolio allocation, exploration budget bounds
- ContentInvestmentDecisionEngine: refresh vs new article decision logic
- PerformanceForecastService & SeasonalityModel: bounded forecast ranges, trend lifecycle classification
"""

import pytest

from app.db.models.optimization import (
    MemoryStatus,
    PredictionOutcome,
    StrategyMemory,
    StrategyParameter,
    StrategyVersion,
    StrategyVersionStatus,
)
from app.learning.engine import ZohraLearningEngine
from app.learning.forecasting import (
    PerformanceForecastService,
    SeasonalityModel,
    TrendLifecycleClass,
)
from app.learning.portfolio import (
    ContentBucket,
    ContentInvestmentDecisionEngine,
    InvestmentChoice,
    StrategyAllocationEngine,
)
from app.learning.strategy import (
    StrategyParameterController,
    StrategyVersionManager,
)
from app.optimization.experiments import ExperimentEngine, ExperimentResultType


# ── Experiment Engine Tests ───────────────────────────────────────────

class TestExperimentEngine:
    def test_positive_experiment_result(self):
        b_metrics = {"search_console_ctr": 0.020, "impressions": 6000, "avg_position": 5.4}
        t_metrics = {"search_console_ctr": 0.026, "impressions": 6100, "avg_position": 5.2}

        res = ExperimentEngine.evaluate_experiment(
            experiment_id="exp-1",
            primary_metric="search_console_ctr",
            baseline_metrics=b_metrics,
            treatment_metrics=t_metrics,
            minimum_sample=500,
            success_threshold=0.10,
        )
        assert res.result == ExperimentResultType.POSITIVE
        assert res.site_adjusted_relative_change >= 0.10
        assert not res.rollback_recommended

    def test_negative_experiment_triggers_rollback(self):
        b_metrics = {"search_console_ctr": 0.030, "impressions": 5000, "avg_position": 4.8}
        t_metrics = {"search_console_ctr": 0.020, "impressions": 4800, "avg_position": 5.9}  # 33% drop

        res = ExperimentEngine.evaluate_experiment(
            experiment_id="exp-2",
            primary_metric="search_console_ctr",
            baseline_metrics=b_metrics,
            treatment_metrics=t_metrics,
            rollback_threshold=-0.15,
        )
        assert res.result == ExperimentResultType.NEGATIVE
        assert res.rollback_recommended

    def test_inconclusive_due_to_insufficient_sample(self):
        b_metrics = {"search_console_ctr": 0.020, "impressions": 80}
        t_metrics = {"search_console_ctr": 0.035, "impressions": 95}  # Sample < 500

        res = ExperimentEngine.evaluate_experiment(
            experiment_id="exp-3",
            primary_metric="search_console_ctr",
            baseline_metrics=b_metrics,
            treatment_metrics=t_metrics,
            minimum_sample=500,
        )
        assert res.result == ExperimentResultType.INCONCLUSIVE
        assert not res.rollback_recommended

    def test_site_wide_trend_adjustment(self):
        # Optimized article drops 10%, but entire site dropped 35% -> net relative change is +25%!
        b_metrics = {"clicks": 100, "impressions": 5000}
        t_metrics = {"clicks": 90, "impressions": 4800}  # -10% raw change

        site_metrics = {"clicks_baseline": 10000, "clicks_treatment": 6500}  # -35% site change

        res = ExperimentEngine.evaluate_experiment(
            experiment_id="exp-4",
            primary_metric="clicks",
            baseline_metrics=b_metrics,
            treatment_metrics=t_metrics,
            site_trend_metrics=site_metrics,
            success_threshold=0.10,
        )
        # raw (-0.10) - site (-0.35) = +0.25 net relative lift
        assert res.site_adjusted_relative_change == pytest.approx(0.25, abs=0.01)
        assert res.result == ExperimentResultType.POSITIVE

    def test_confounder_detection_lowers_confidence(self):
        b_metrics = {"clicks": 100, "impressions": 5000}
        t_metrics = {"clicks": 125, "impressions": 5200}

        res = ExperimentEngine.evaluate_experiment(
            experiment_id="exp-5",
            primary_metric="clicks",
            baseline_metrics=b_metrics,
            treatment_metrics=t_metrics,
            known_confounders=["Google Core Update", "Site Outage on Day 12"],
        )
        assert res.confidence < 0.60
        assert len(res.confounders_detected) == 2


# ── Learning Engine Tests ─────────────────────────────────────────────

class TestLearningEngine:
    def test_prediction_calibration_detection(self):
        # 3 high-score items underperforming 3 mid-score items
        outcomes = [
            PredictionOutcome(predicted_value=90.0, actual_value=40.0),
            PredictionOutcome(predicted_value=88.0, actual_value=45.0),
            PredictionOutcome(predicted_value=85.0, actual_value=42.0),
            PredictionOutcome(predicted_value=65.0, actual_value=60.0),
            PredictionOutcome(predicted_value=62.0, actual_value=65.0),
            PredictionOutcome(predicted_value=60.0, actual_value=70.0),
        ]
        report = ZohraLearningEngine.evaluate_predictions_calibration(outcomes)
        assert not report.is_calibrated
        assert report.recalibration_needed
        assert any("inversion" in r for r in report.reasons)

    def test_strategy_memory_synthesis_scales_with_sample(self):
        res1 = ZohraLearningEngine.synthesize_strategy_memory(
            subject="How-To Title Framing",
            memory_type="TITLE_PATTERN",
            observation="Task-focused how-to titles show superior CTR.",
            consistent_experiment_count=3,
        )
        assert res1.created
        assert res1.status == MemoryStatus.SUPPORTED
        assert res1.confidence >= 0.75

        res2 = ZohraLearningEngine.synthesize_strategy_memory(
            subject="How-To Title Framing",
            memory_type="TITLE_PATTERN",
            observation="Task-focused how-to titles show superior CTR.",
            consistent_experiment_count=5,
        )
        assert res2.status == MemoryStatus.STRONG
        assert res2.confidence >= 0.85

    def test_memory_decay_over_time(self):
        mem = StrategyMemory(
            subject="Year in Title Pattern",
            memory_type="TITLE_PATTERN",
            observation="Adding year improves CTR.",
            confidence=0.80,
            status=MemoryStatus.STRONG.value,
        )
        new_conf = ZohraLearningEngine.apply_memory_decay(mem, days_without_support=120)
        assert new_conf < 0.80
        assert mem.status in (MemoryStatus.WEAKENING.value, MemoryStatus.SUPPORTED.value)

    def test_contradiction_handling(self):
        mem = StrategyMemory(
            subject="Long Form Guides",
            memory_type="ARTICLE_LENGTH_PATTERN",
            observation="4000+ words outperforms 1500 words.",
            confidence=0.80,
            status=MemoryStatus.STRONG.value,
            contradicting_evidence_json=[],
        )
        new_conf = ZohraLearningEngine.register_contradicting_evidence(
            mem,
            contradiction_evidence={"experiment_id": "exp-99", "result": "NEGATIVE", "notes": "Shorter guide had 2x dwell time"},
        )
        assert new_conf == 0.60
        assert len(mem.contradicting_evidence_json) == 1
        assert mem.status == MemoryStatus.WEAKENING.value

    def test_viral_outlier_detection(self):
        # 50,000 clicks vs 2,000 median clicks = 25x > 5x
        is_outlier = ZohraLearningEngine.is_viral_outlier(article_clicks=50000, cohort_median_clicks=2000)
        assert is_outlier

        normal = ZohraLearningEngine.is_viral_outlier(article_clicks=3000, cohort_median_clicks=2000)
        assert not normal


# ── Strategy Parameter Controller Tests ───────────────────────────────

class TestStrategyParameterController:
    def test_bounded_step_rate_limit(self):
        param = StrategyParameter(
            parameter_name="topic_relevance_weight",
            category="TOPIC_SCORING",
            default_value=0.20,
            current_value=0.20,
            minimum_value=0.05,
            maximum_value=0.80,
        )
        # Attempting jump from 0.20 to 0.90 -> should be clamped by 25% max step (max delta 0.05 -> 0.25)
        res = StrategyParameterController.apply_bounded_adjustment(
            param=param,
            proposed_value=0.90,
            evidence_ref="Test evidence",
        )
        assert res.rate_limited
        assert param.current_value == pytest.approx(0.25, abs=0.01)
        assert param.previous_value == 0.20
        assert param.rollback_value == 0.20

    def test_hard_boundary_clamping(self):
        param = StrategyParameter(
            parameter_name="min_freshness_weight",
            category="REFRESH",
            default_value=0.10,
            current_value=0.05,
            minimum_value=0.05,
            maximum_value=0.50,
        )
        # Attempting to drop below minimum_value (0.05)
        res = StrategyParameterController.apply_bounded_adjustment(
            param=param,
            proposed_value=0.01,
            evidence_ref="Test evidence",
        )
        assert res.clamped
        assert param.current_value == 0.05


# ── Strategy Version Manager Tests ────────────────────────────────────

class TestStrategyVersionManager:
    def test_shadow_mode_and_promotion(self):
        shadow_ver = StrategyVersionManager.create_shadow_version(
            site_id="site-1",
            version_label="v2.0-shadow",
            parameters={"topic_weight": 0.45},
            reason="Testing increased topical authority weight",
        )
        assert shadow_ver.status == StrategyVersionStatus.SHADOW.value

        active_ver = StrategyVersion(
            site_id="site-1",
            version="v1.0",
            parameters_json={"topic_weight": 0.30},
            status=StrategyVersionStatus.ACTIVE.value,
        )

        promoted, retired = StrategyVersionManager.promote_to_active(shadow_ver, active_ver)
        assert promoted.status == StrategyVersionStatus.ACTIVE.value
        assert retired.status == StrategyVersionStatus.RETIRED.value

    def test_strategy_rollback(self):
        v2 = StrategyVersion(
            site_id="site-1",
            version="v2.0",
            status=StrategyVersionStatus.ACTIVE.value,
        )
        v1 = StrategyVersion(
            site_id="site-1",
            version="v1.0",
            status=StrategyVersionStatus.RETIRED.value,
        )
        restored, failed = StrategyVersionManager.rollback_version(v2, v1)
        assert restored.status == StrategyVersionStatus.ACTIVE.value
        assert failed.status == StrategyVersionStatus.ROLLBACK.value


# ── Portfolio & Content Investment Tests ──────────────────────────────

class TestPortfolioAndInvestmentEngine:
    def test_exploration_budget_throttling(self):
        # 100 total articles: 18 experimental (18% > 15% limit)
        counts = {
            ContentBucket.CORE_EVERGREEN.value: 40,
            ContentBucket.TRENDING.value: 20,
            ContentBucket.NEWS.value: 12,
            ContentBucket.REFRESH.value: 10,
            ContentBucket.EXPERIMENTAL.value: 18,
        }
        res = StrategyAllocationEngine.evaluate_portfolio_budget(counts, max_exploration_ratio=0.15)
        assert res.exploration_budget_exceeded
        assert not res.can_publish_experimental

    def test_refresh_wins_for_existing_authoritative_match(self):
        existing = {
            "id": "art-101",
            "title": "Complete Python Asyncio Tutorial",
            "intent": "INFORMATIONAL",
            "impressions": 15000,
            "age_days": 180,
        }
        dec = ContentInvestmentDecisionEngine.evaluate_opportunity_investment(
            opportunity_query="python asyncio tutorial",
            opportunity_intent="INFORMATIONAL",
            opportunity_potential_clicks=800,
            matched_existing_article=existing,
        )
        assert dec.choice == InvestmentChoice.REFRESH_EXISTING
        assert dec.refresh_score > dec.new_article_score

    def test_new_article_wins_for_distinct_intent(self):
        existing = {
            "id": "art-101",
            "title": "Complete Python Asyncio Tutorial",
            "intent": "INFORMATIONAL",
            "impressions": 15000,
        }
        # Intent is COMMERCIAL comparison, not informational tutorial
        dec = ContentInvestmentDecisionEngine.evaluate_opportunity_investment(
            opportunity_query="best async python web frameworks 2026",
            opportunity_intent="COMMERCIAL",
            opportunity_potential_clicks=1200,
            matched_existing_article=existing,
        )
        assert dec.choice == InvestmentChoice.CREATE_NEW_ARTICLE
        assert dec.new_article_score > dec.refresh_score


# ── Forecasting & Seasonality Tests ───────────────────────────────────

class TestForecastingAndSeasonality:
    def test_conservative_metric_forecast_range(self):
        recent_clicks = [45, 52, 48, 55, 60, 49, 53, 58, 62, 50, 47, 54, 56, 52]
        fc = PerformanceForecastService.forecast_metric_range(
            article_id="art-1",
            metric="clicks",
            recent_daily_values=recent_clicks,
            forecast_days=28,
        )
        assert fc.expected_range.low < fc.expected_range.mid < fc.expected_range.high
        assert fc.confidence > 0.50

    def test_seasonality_and_trend_lifecycle_classification(self):
        pattern = SeasonalityModel.get_seasonal_pattern("tax preparation guide")
        assert pattern is not None
        assert pattern.peak_month == 4  # April

        # Trend active for 45 days with steady impressions -> EVERGREEN_TRANSITION
        daily = [200] * 45
        t_class = SeasonalityModel.classify_trend_lifecycle(days_active=45, daily_impressions=daily)
        assert t_class == TrendLifecycleClass.EVERGREEN_TRANSITION
