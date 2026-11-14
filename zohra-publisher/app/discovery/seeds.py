"""Seed sources for Zohra Discovery Engine.

Provides reputable, safe baseline sources across Technology, AI, Science, and Business.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import SourceHealth, SourceTier, SourceType
from app.db.models.sources import Source

DEFAULT_SEEDS = [
    {
        "name": "MIT Technology Review",
        "domain": "technologyreview.com",
        "base_url": "https://www.technologyreview.com/feed/",
        "source_type": SourceType.RSS,
        "tier": SourceTier.TIER_2,
        "category": "Technology",
        "country": "US",
        "language": "en",
        "authority_score": 92.0,
        "reliability_score": 90.0,
        "freshness_score": 80.0,
        "priority": 4,
        "polling_interval_minutes": 30,
        "is_enabled": True,
        "is_trusted": True,
    },
    {
        "name": "Ars Technica",
        "domain": "arstechnica.com",
        "base_url": "https://feeds.arstechnica.com/arstechnica/index",
        "source_type": SourceType.RSS,
        "tier": SourceTier.TIER_2,
        "category": "Technology",
        "country": "US",
        "language": "en",
        "authority_score": 88.0,
        "reliability_score": 87.0,
        "freshness_score": 85.0,
        "priority": 4,
        "polling_interval_minutes": 20,
        "is_enabled": True,
        "is_trusted": True,
    },
    {
        "name": "BBC News Technology",
        "domain": "bbc.com",
        "base_url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "source_type": SourceType.RSS,
        "tier": SourceTier.TIER_2,
        "category": "Technology",
        "country": "GB",
        "language": "en",
        "authority_score": 95.0,
        "reliability_score": 93.0,
        "freshness_score": 88.0,
        "priority": 5,
        "polling_interval_minutes": 15,
        "is_enabled": True,
        "is_trusted": True,
    },
    {
        "name": "NASA Breaking News",
        "domain": "nasa.gov",
        "base_url": "https://www.nasa.gov/feed/",
        "source_type": SourceType.RSS,
        "tier": SourceTier.TIER_1,
        "category": "Science",
        "country": "US",
        "language": "en",
        "authority_score": 99.0,
        "reliability_score": 99.0,
        "freshness_score": 70.0,
        "priority": 4,
        "polling_interval_minutes": 60,
        "is_enabled": True,
        "is_trusted": True,
    },
    {
        "name": "Hacker News Frontpage",
        "domain": "news.ycombinator.com",
        "base_url": "https://news.ycombinator.com/rss",
        "source_type": SourceType.COMMUNITY,
        "tier": SourceTier.TIER_4,
        "category": "Technology",
        "country": "global",
        "language": "en",
        "authority_score": 50.0,
        "reliability_score": 45.0,
        "freshness_score": 98.0,
        "priority": 3,
        "polling_interval_minutes": 10,
        "is_enabled": True,
        "is_trusted": False,
    },
]


async def load_seed_sources(db: AsyncSession) -> int:
    """Load default seed sources if not already present. Returns count of added sources."""
    added = 0
    for seed in DEFAULT_SEEDS:
        existing = await db.execute(
            select(Source).where(
                (Source.base_url == seed["base_url"]) | (Source.name == seed["name"])
            )
        )
        if not existing.scalar_one_or_none():
            source = Source(
                **seed,
                health_status=SourceHealth.HEALTHY,
                consecutive_failures=0,
                average_response_time_ms=0.0,
            )
            db.add(source)
            added += 1

    if added > 0:
        await db.commit()
    return added
