"""
Zohra — Web Discovery Search Provider Interface.

Provider-independent abstraction for active web discovery searches.
Allows plugging in Google Custom Search, Bing, Brave, Serper, or local mock
without hardcoding any single vendor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from app.discovery.adapters.base import RawFetchedItem


class SearchProvider(ABC):
    """Abstract interface for active web discovery search providers."""

    @abstractmethod
    async def search(
        self,
        query: str,
        language: str | None = None,
        country: str | None = None,
        freshness: str | None = None,
        limit: int = 10,
    ) -> list[RawFetchedItem]:
        """Execute a discovery query and return structured search results."""
        ...


class MockSearchProvider(SearchProvider):
    """
    Deterministic search provider for unit testing, offline execution,
    and end-to-end simulation.
    """

    def __init__(self, predefined_results: dict[str, list[RawFetchedItem]] | None = None) -> None:
        self.predefined_results = predefined_results or {}
        self.call_history: list[dict] = []

    def set_results_for_query(self, query: str, items: list[RawFetchedItem]) -> None:
        """Register deterministic items for a specific query."""
        self.predefined_results[query.lower().strip()] = items

    async def search(
        self,
        query: str,
        language: str | None = None,
        country: str | None = None,
        freshness: str | None = None,
        limit: int = 10,
    ) -> list[RawFetchedItem]:
        self.call_history.append(
            {
                "query": query,
                "language": language,
                "country": country,
                "freshness": freshness,
                "limit": limit,
            }
        )

        q_key = query.lower().strip()
        if q_key in self.predefined_results:
            return self.predefined_results[q_key][:limit]

        # Generate a deterministic mock result if no explicit fixture exists
        now = datetime.now(UTC)
        return [
            RawFetchedItem(
                url=f"https://example.com/search-result/{i}",
                title=f"Search Result {i}: {query}",
                summary=f"Automated mock result for discovery query: {query}",
                content_text=f"Full article text regarding {query} with extensive details.",
                published_at=now,
                raw_metadata={"provider": "mock", "rank": i},
            )
            for i in range(1, min(limit + 1, 4))
        ]
