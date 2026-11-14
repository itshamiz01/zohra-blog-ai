"""Integration tests for Part 2 Discovery APIs: Sources, Events, Trends, Discovery Control."""

import pytest

from app.core.constants import EventStatus
from app.db.models.events import Event


class TestSourcesAPI:
    @pytest.mark.asyncio
    async def test_sources_crud(self, client, admin_headers):
        # 1. Create source
        payload = {
            "name": "TechCrunch RSS",
            "domain": "techcrunch.com",
            "base_url": "https://techcrunch.com/feed/",
            "source_type": "rss",
            "tier": 3,
            "category": "Technology",
            "authority_score": 85.0,
            "reliability_score": 82.0,
            "freshness_score": 90.0,
            "priority": 4,
            "polling_interval_minutes": 20,
            "is_enabled": True,
        }
        resp = await client.post("/api/v1/sources", json=payload, headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()["data"]
        source_id = data["id"]
        assert data["domain"] == "techcrunch.com"

        # 2. Get source
        resp = await client.get(f"/api/v1/sources/{source_id}", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "TechCrunch RSS"

        # 3. Disable source
        resp = await client.post(f"/api/v1/sources/{source_id}/disable", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["is_enabled"] is False

        # 4. Enable source
        resp = await client.post(f"/api/v1/sources/{source_id}/enable", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["is_enabled"] is True

        # 5. List sources
        resp = await client.get("/api/v1/sources", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1


class TestDiscoveryControlAPI:
    @pytest.mark.asyncio
    async def test_seed_and_status(self, client, admin_headers):
        # Seed default sources
        resp = await client.post("/api/v1/discovery/seed", headers=admin_headers)
        assert resp.status_code == 201
        assert "sources_added" in resp.json()["data"]

        # Check status
        resp = await client.get("/api/v1/discovery/status", headers=admin_headers)
        assert resp.status_code == 200
        status_data = resp.json()["data"]
        assert status_data["active_sources"] >= 1

        # Check stats
        resp = await client.get("/api/v1/discovery/stats", headers=admin_headers)
        assert resp.status_code == 200
        stats_data = resp.json()["data"]
        assert "sources_total" in stats_data
        assert "categories_breakdown" in stats_data


class TestEventsAndTrendsAPI:
    @pytest.mark.asyncio
    async def test_events_and_trends_listing(self, client, admin_headers, async_db):
        # Insert a sample event directly into the db
        event = Event(
            canonical_title="Anthropic Releases Claude 3.5 Sonnet",
            summary="Anthropic has released Claude 3.5 Sonnet featuring industry-leading reasoning benchmarks.",
            primary_category="Technology",
            event_type="product_launch",
            status=EventStatus.ACCELERATING,
            source_count=5,
            document_count=12,
            authority_score=90.0,
            reliability_score=92.0,
            freshness_score=95.0,
            velocity_score=88.0,
            momentum_score=85.0,
            source_diversity_score=80.0,
            confidence_score=94.0,
            trend_score=88.5,
            language="en",
            country="global",
            is_qualified_for_opportunity=True,
            trend_reasons=["+400% velocity in 2 hours", "5 independent domains"],
        )
        async_db.add(event)
        await async_db.commit()
        await async_db.refresh(event)

        # 1. Query events
        resp = await client.get("/api/v1/events", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

        # 2. Trending events
        resp = await client.get("/api/v1/events/trending", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

        # 3. Trends API
        resp = await client.get("/api/v1/trends/top", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1
        top_trend = resp.json()["data"][0]
        assert top_trend["trend_score"] >= 80.0

        # 4. Reject and restore event
        resp = await client.post(
            f"/api/v1/events/{event.id}/reject?reason=duplicate_test",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "rejected"

        resp = await client.post(f"/api/v1/events/{event.id}/restore", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"
