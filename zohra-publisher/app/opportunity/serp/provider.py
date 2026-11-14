"""
Zohra — SERP Provider Abstraction & Mock Implementation.

Provides vendor-agnostic interface for querying search engine result pages (SERPs),
caching expensive queries in Redis, and parsing normalized SERP results.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.constants import SearchIntent, SERPResultType
from app.core.logging import get_logger
from app.utils.redis import get_redis

logger = get_logger(__name__, component="serp_provider")


@dataclass
class NormalizedSERPResult:
    position: int
    url: str
    domain: str
    title: str
    snippet: str
    result_type: SERPResultType
    published_date: datetime | None = None
    is_official_domain: bool = False
    is_forum: bool = False
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class SERPSnapshotData:
    query: str
    query_hash: str
    provider: str
    country: str
    language: str
    device: str
    total_results_estimate: int | None
    dominant_intent: SearchIntent
    intent_alignment_score: float
    features: dict[str, Any]
    results: list[NormalizedSERPResult]
    retrieved_at: datetime
    cost_usd: float = 0.0


class SERPProvider(ABC):
    """Abstract interface for SERP providers (ValueSERP, SerpAPI, DataForSEO, Mock)."""

    @abstractmethod
    async def search(
        self,
        query: str,
        country: str = "global",
        language: str = "en",
        device: str = "desktop",
    ) -> SERPSnapshotData:
        """Executes a search and returns normalized SERP results."""
        pass


class MockSERPProvider(SERPProvider):
    """
    Deterministic mock SERP provider for testing, local simulation,
    and fallback when external SERP APIs are not configured.
    """

    KNOWN_OFFICIAL_DOMAINS = {
        "openai.com", "anthropic.com", "google.com", "microsoft.com",
        "github.com", "apple.com", "runwayml.com", "stability.ai",
        "pika.art", "midjourney.com", "adobe.com"
    }

    FORUM_DOMAINS = {
        "reddit.com", "quora.com", "stackoverflow.com", "news.ycombinator.com",
        "discord.com", "community.openai.com", "github.com/discussions"
    }

    def __init__(self, cost_per_query: float = 0.005) -> None:
        self.cost_per_query = cost_per_query

    def compute_query_hash(self, query: str, country: str, language: str) -> str:
        key = f"{query.strip().lower()}:{country.lower()}:{language.lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def search(
        self,
        query: str,
        country: str = "global",
        language: str = "en",
        device: str = "desktop",
    ) -> SERPSnapshotData:
        q_clean = query.strip().lower()
        q_hash = self.compute_query_hash(q_clean, country, language)

        # Check Redis Cache
        cache_key = f"serp:cache:{q_hash}"
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                results = [
                    NormalizedSERPResult(
                        position=r["position"],
                        url=r["url"],
                        domain=r["domain"],
                        title=r["title"],
                        snippet=r["snippet"],
                        result_type=SERPResultType(r["result_type"]),
                        published_date=datetime.fromisoformat(r["published_date"]) if r.get("published_date") else None,
                        is_official_domain=r["is_official_domain"],
                        is_forum=r["is_forum"],
                        features=r.get("features", {}),
                    )
                    for r in data["results"]
                ]
                return SERPSnapshotData(
                    query=data["query"],
                    query_hash=data["query_hash"],
                    provider=data["provider"],
                    country=data["country"],
                    language=data["language"],
                    device=data["device"],
                    total_results_estimate=data.get("total_results_estimate"),
                    dominant_intent=SearchIntent(data["dominant_intent"]),
                    intent_alignment_score=data["intent_alignment_score"],
                    features=data["features"],
                    results=results,
                    retrieved_at=datetime.fromisoformat(data["retrieved_at"]),
                    cost_usd=0.0,  # Cache hit is free
                )
        except Exception as exc:
            logger.debug("Redis SERP cache lookup failed, falling through to generation: %s", exc)

        # Generate realistic mock results based on query characteristics
        is_navigational = any(term in q_clean for term in ("login", "sign in", "portal", "official", "app store"))
        is_pricing = any(term in q_clean for term in ("pricing", "price", "cost", "free"))
        is_vs = " vs " in q_clean or " compared to " in q_clean
        is_tutorial = any(term in q_clean for term in ("how to", "tutorial", "guide", "setup"))

        detected_intent = SearchIntent.INFORMATIONAL
        if is_navigational:
            detected_intent = SearchIntent.NAVIGATIONAL
        elif is_pricing:
            detected_intent = SearchIntent.COMMERCIAL_INVESTIGATION
        elif is_vs:
            detected_intent = SearchIntent.COMPARISON
        elif is_tutorial:
            detected_intent = SearchIntent.TUTORIAL

        # Extract primary brand/product if available
        brand = q_clean.split()[0] if q_clean else "tool"

        results: list[NormalizedSERPResult] = []

        # Position 1: Official page or primary authority
        pos = 1
        if is_navigational or "official" in q_clean or brand in ("chatgpt", "openai", "claude", "runway", "model"):
            official_dom = f"{brand}.com" if f"{brand}.com" in self.KNOWN_OFFICIAL_DOMAINS else "openai.com"
            results.append(
                NormalizedSERPResult(
                    position=pos,
                    url=f"https://{official_dom}/{brand}-overview",
                    domain=official_dom,
                    title=f"{brand.capitalize()} Official Portal — Overview & Access",
                    snippet=f"Official {brand} home page. Get started, view documentation, or log into your account.",
                    result_type=SERPResultType.ORGANIC,
                    is_official_domain=True,
                    is_forum=False,
                )
            )
            pos += 1

        # Position 2: Industry tech blog / guide
        results.append(
            NormalizedSERPResult(
                position=pos,
                url=f"https://techcrunch.com/2026/01/{brand}-deep-dive",
                domain="techcrunch.com",
                title=f"{query.capitalize()} — Everything You Need to Know",
                snippet=f"Comprehensive breakdown of {brand}. Key features, background analysis, and industry impact.",
                result_type=SERPResultType.ORGANIC,
                published_date=datetime.now(UTC),
                is_official_domain=False,
                is_forum=False,
            )
        )
        pos += 1

        # Position 3: Specialized comparison or tutorial publisher
        results.append(
            NormalizedSERPResult(
                position=pos,
                url=f"https://zapier.com/blog/{brand}-guide",
                domain="zapier.com",
                title=f"The Complete Guide to {brand.capitalize()}: Hands-on Review",
                snippet=f"We tested {brand} in real-world workflows. Here is how it compares to top alternatives.",
                result_type=SERPResultType.FEATURED_SNIPPET if is_tutorial else SERPResultType.ORGANIC,
                is_official_domain=False,
                is_forum=False,
            )
        )
        pos += 1

        # Position 4: Community forum discussion (e.g. Reddit)
        results.append(
            NormalizedSERPResult(
                position=pos,
                url=f"https://reddit.com/r/ArtificialIntelligence/comments/{brand}_discussion",
                domain="reddit.com",
                title=f"Is {brand} actually worth it? Real user experiences and complaints : r/AI",
                snippet=f"Discussion on {brand}: Pricing seems steep, missing regional support, but workflow speed is impressive.",
                result_type=SERPResultType.FORUM,
                is_official_domain=False,
                is_forum=True,
            )
        )
        pos += 1

        # Position 5: Video demonstration (YouTube)
        results.append(
            NormalizedSERPResult(
                position=pos,
                url=f"https://youtube.com/watch?v={q_hash[:8]}",
                domain="youtube.com",
                title=f"{brand.capitalize()} Full Tutorial for Beginners (Step-by-Step)",
                snippet=f"Watch how to set up {brand} from scratch. Complete workflow walkthrough and live demo.",
                result_type=SERPResultType.VIDEO,
                is_official_domain=False,
                is_forum=False,
            )
        )
        pos += 1

        # Positions 6-8: Additional secondary competitors
        for i, comp_dom in enumerate(["theverge.com", "medium.com", "tomshardware.com"]):
            results.append(
                NormalizedSERPResult(
                    position=pos,
                    url=f"https://{comp_dom}/{brand}-analysis-{i}",
                    domain=comp_dom,
                    title=f"{brand.capitalize()} vs Competitors: Benchmarks & Breakdown",
                    snippet=f"Testing {brand} performance against rival tools in the creator and developer ecosystem.",
                    result_type=SERPResultType.ORGANIC,
                    is_official_domain=False,
                    is_forum=False,
                )
            )
            pos += 1

        features = {
            "has_featured_snippet": is_tutorial,
            "has_video_carousel": True,
            "has_forum_results": True,
            "has_people_also_ask": True,
            "people_also_ask": [
                f"How much does {brand} cost?",
                f"Is {brand} available in India and Europe?",
                f"How to use {brand} for YouTube video creation?",
                f"What are the best alternatives to {brand}?",
            ],
        }

        snapshot = SERPSnapshotData(
            query=query,
            query_hash=q_hash,
            provider="mock_serp",
            country=country,
            language=language,
            device=device,
            total_results_estimate=1250000,
            dominant_intent=detected_intent,
            intent_alignment_score=0.92,
            features=features,
            results=results,
            retrieved_at=datetime.now(UTC),
            cost_usd=self.cost_per_query,
        )

        # Cache in Redis with configurable TTL
        try:
            redis = await get_redis()
            ttl = get_settings().SERP_CACHE_TTL_SECONDS
            cache_payload = {
                "query": snapshot.query,
                "query_hash": snapshot.query_hash,
                "provider": snapshot.provider,
                "country": snapshot.country,
                "language": snapshot.language,
                "device": snapshot.device,
                "total_results_estimate": snapshot.total_results_estimate,
                "dominant_intent": snapshot.dominant_intent.value,
                "intent_alignment_score": snapshot.intent_alignment_score,
                "features": snapshot.features,
                "retrieved_at": snapshot.retrieved_at.isoformat(),
                "results": [
                    {
                        "position": r.position,
                        "url": r.url,
                        "domain": r.domain,
                        "title": r.title,
                        "snippet": r.snippet,
                        "result_type": r.result_type.value,
                        "published_date": r.published_date.isoformat() if r.published_date else None,
                        "is_official_domain": r.is_official_domain,
                        "is_forum": r.is_forum,
                        "features": r.features,
                    }
                    for r in snapshot.results
                ],
            }
            await redis.setex(cache_key, ttl, json.dumps(cache_payload))
        except Exception as exc:
            logger.debug("Redis SERP cache write failed, continuing without cache: %s", exc)

        return snapshot


def get_serp_provider() -> SERPProvider:
    """Factory returning configured SERP provider."""
    return MockSERPProvider()
