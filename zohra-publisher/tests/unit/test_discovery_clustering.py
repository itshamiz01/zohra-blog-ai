"""Unit tests for event clustering, candidate narrowing, and merge/split operations."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.constants import EventStatus
from app.discovery.clustering.embeddings import DeterministicEmbeddingProvider
from app.discovery.clustering.engine import EventClusteringEngine


class TestEventClusteringEngine:
    @pytest.mark.asyncio
    async def test_embedding_cosine_similarity(self):
        emb_provider = DeterministicEmbeddingProvider()
        e1 = await emb_provider.embed_text("Apple announces M4 chip in new MacBook Pro models")
        e2 = await emb_provider.embed_text(
            "Apple unveils M4 processor powering latest MacBook laptops"
        )
        e3 = await emb_provider.embed_text("Federal Reserve holds benchmark interest rate steady")

        sim_related = EventClusteringEngine._cosine_similarity(e1, e2)
        sim_unrelated = EventClusteringEngine._cosine_similarity(e1, e3)

        assert sim_related > sim_unrelated
        assert sim_related > 0.40

    def test_candidate_narrowing_time_window(self):
        engine = EventClusteringEngine(db=MagicMock())
        now = datetime.now(UTC)
        old_time = now - timedelta(hours=72)  # beyond default 48h window

        recent_event = MagicMock(
            primary_category="Technology",
            last_seen_at=now - timedelta(hours=2),
            status=EventStatus.ACTIVE,
        )
        old_event = MagicMock(
            primary_category="Technology",
            last_seen_at=old_time,
            status=EventStatus.ACTIVE,
        )

        candidates = engine._filter_candidates(
            all_events=[recent_event, old_event],
            category="Technology",
            now=now,
            window_hours=48,
        )
        assert recent_event in candidates
        assert old_event not in candidates

    def test_candidate_narrowing_category(self):
        engine = EventClusteringEngine(db=MagicMock())
        now = datetime.now(UTC)

        tech_event = MagicMock(
            primary_category="Technology",
            last_seen_at=now,
            status=EventStatus.ACTIVE,
        )
        entertainment_event = MagicMock(
            primary_category="Entertainment",
            last_seen_at=now,
            status=EventStatus.ACTIVE,
        )

        candidates = engine._filter_candidates(
            all_events=[tech_event, entertainment_event],
            category="Technology",
            now=now,
            window_hours=48,
        )
        assert tech_event in candidates
        assert entertainment_event not in candidates
