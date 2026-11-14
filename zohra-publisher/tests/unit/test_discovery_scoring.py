"""Unit tests for velocity, momentum, freshness, diversity, confidence, spam, trend, and lifecycle scoring."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.constants import EventStatus, SourceTier, TrendClassification
from app.discovery.scoring.confidence import calculate_event_confidence
from app.discovery.scoring.diversity import calculate_source_diversity
from app.discovery.scoring.freshness import calculate_freshness
from app.discovery.scoring.lifecycle import evaluate_event_lifecycle
from app.discovery.scoring.spam import detect_event_spam
from app.discovery.scoring.trend import classify_trend_score
from app.discovery.scoring.velocity import calculate_velocity


class TestVelocity:
    def test_windowed_velocity_acceleration(self):
        now = datetime.now(UTC)
        # 10 recent documents in the last 15 minutes
        timestamps = [now - timedelta(minutes=i) for i in range(10)]
        v_score, accel = calculate_velocity(timestamps)
        assert v_score >= 50.0
        assert accel >= 1.0

    def test_zero_documents_velocity(self):
        v_score, accel = calculate_velocity([])
        assert v_score == 0.0
        assert accel in (0.0, 1.0)


class TestFreshness:
    def test_exponential_decay(self):
        now = datetime.now(UTC)
        recent_time = now - timedelta(hours=1)
        old_time = now - timedelta(hours=48)

        f_recent = calculate_freshness(first_seen=recent_time, category="Technology")
        f_old = calculate_freshness(first_seen=old_time, category="Technology")
        assert f_recent > f_old
        assert f_recent > 80.0
        assert f_old < 30.0


class TestDiversity:
    def test_multi_domain_and_tier_diversity(self):
        sources = [
            MagicMock(domain="reuters.com", tier=SourceTier.TIER_2, country="US"),
            MagicMock(domain="bbc.com", tier=SourceTier.TIER_2, country="GB"),
            MagicMock(domain="nasa.gov", tier=SourceTier.TIER_1, country="US"),
            MagicMock(domain="theverge.com", tier=SourceTier.TIER_3, country="US"),
        ]
        score = calculate_source_diversity(sources)
        assert score >= 70.0

    def test_single_domain_diversity(self):
        sources = [
            MagicMock(domain="same-farm.com", tier=SourceTier.TIER_5, country="US"),
            MagicMock(domain="same-farm.com", tier=SourceTier.TIER_5, country="US"),
        ]
        score = calculate_source_diversity(sources)
        assert score <= 30.0


class TestConfidence:
    def test_tier_1_confirmation_boosts_confidence(self):
        docs = [
            MagicMock(id=uuid4(), title="Tech Launch", content_text="Release announced on Oct 5"),
            MagicMock(
                id=uuid4(), title="Tech Launch Official", content_text="Release announced on Oct 5"
            ),
        ]
        sources = [
            MagicMock(tier=SourceTier.TIER_3, reliability_score=70.0, domain="theverge.com"),
            MagicMock(tier=SourceTier.TIER_1, reliability_score=98.0, domain="openai.com"),
        ]
        res = calculate_event_confidence(documents=docs, sources=sources)
        assert res["confidence_score"] >= 75.0
        assert not res["contradiction_detected"]

    def test_contradiction_detection(self):
        docs = [
            MagicMock(id=uuid4(), title="Release in 2025", content_text="Release date is 2025"),
            MagicMock(id=uuid4(), title="Release in 2027", content_text="Release date is 2027"),
        ]
        sources = [
            MagicMock(tier=SourceTier.TIER_2, reliability_score=80.0, domain="reuters.com"),
            MagicMock(tier=SourceTier.TIER_2, reliability_score=80.0, domain="bbc.com"),
        ]
        res = calculate_event_confidence(documents=docs, sources=sources)
        assert res["confidence_score"] <= 85.0


class TestSpamDetection:
    def test_detects_content_farm_repetition(self):
        docs = [
            MagicMock(
                title="Cheap Crypto Airdrop 100x Guaranteed",
                summary="Free money giveaway",
                content_text="Claim guaranteed crypto token airdrop free now click here",
                canonical_url=f"http://farm{i}.xyz/airdrop",
                word_count=50,
            )
            for i in range(8)
        ]
        sources = [
            MagicMock(domain=f"farm{i}.xyz", tier=SourceTier.TIER_5, reliability_score=10.0)
            for i in range(8)
        ]
        res = detect_event_spam(documents=docs, sources=sources, velocity_acceleration=1.0)
        assert res["spam_probability"] >= 0.50
        assert res["is_spam"] is True


class TestTrendScoring:
    def test_classification_buckets(self):
        assert classify_trend_score(15.0) == TrendClassification.NOISE
        assert classify_trend_score(35.0) == TrendClassification.WEAK_SIGNAL
        assert classify_trend_score(55.0) == TrendClassification.MONITOR
        assert classify_trend_score(68.0) == TrendClassification.EMERGING
        assert classify_trend_score(78.0) == TrendClassification.TRENDING
        assert classify_trend_score(88.0) == TrendClassification.HIGH_VELOCITY
        assert classify_trend_score(98.0) == TrendClassification.EXCEPTIONAL_SIGNAL

    def test_lifecycle_evaluation(self):
        event = MagicMock(
            status=EventStatus.EMERGING,
            document_count=15,
            source_count=5,
            velocity_score=85.0,
            acceleration_ratio=2.5,
            momentum_score=80.0,
            freshness_score=80.0,
            trend_score=82.0,
            spam_probability=0.0,
            last_seen_at=datetime.now(UTC),
            is_qualified_for_opportunity=True,
        )
        new_status = evaluate_event_lifecycle(event)
        assert new_status in [EventStatus.ACCELERATING, EventStatus.ACTIVE]
