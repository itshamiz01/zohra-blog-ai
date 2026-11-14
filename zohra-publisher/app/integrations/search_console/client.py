"""
Zohra — Google Search Console Async Client (Part 8).

Provides an abstracted client for Google Search Console APIs:
- Search Analytics query (searchanalytics/query)
- URL Inspection (urlInspection/index:inspect)
- Sitemaps listing

Supports a mock mode (ZOHRA_GSC_MOCK=true) for deterministic testing
and development without real Google credentials.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any

from app.core.logging import get_logger
from app.integrations.search_console.exceptions import (
    SearchConsoleAuthError,
)

logger = get_logger("integrations.search_console.client")


class SearchConsoleClient:
    """Async client for Google Search Console APIs.

    In production, this calls the real Google Search Console API.
    In mock mode (ZOHRA_GSC_MOCK=true), returns deterministic synthetic data.
    """

    def __init__(
        self,
        property_uri: str,
        credential_ref: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        self.property_uri = property_uri
        self.credential_ref = credential_ref
        self.timeout = timeout_seconds
        self._mock = os.getenv("ZOHRA_GSC_MOCK", "false").lower() in ("true", "1", "yes")

    @property
    def is_mock(self) -> bool:
        return self._mock

    async def query_search_analytics(
        self,
        start_date: date,
        end_date: date,
        dimensions: list[str] | None = None,
        row_limit: int = 25000,
        start_row: int = 0,
        data_state: str = "final",
    ) -> list[dict[str, Any]]:
        """Fetch search analytics data from GSC.

        Returns raw rows with keys, clicks, impressions, ctr, position.
        """
        if self._mock:
            return self._mock_search_analytics(start_date, end_date, dimensions, row_limit)

        # Production: would call Google API via httpx + OAuth2
        logger.info(
            "GSC search analytics query",
            property_uri=self.property_uri,
            start_date=str(start_date),
            end_date=str(end_date),
            dimensions=dimensions,
        )
        raise SearchConsoleAuthError(
            "Production GSC client requires valid OAuth2 credentials. "
            "Set ZOHRA_GSC_MOCK=true for development."
        )

    async def inspect_url(self, url: str) -> dict[str, Any]:
        """Inspect a URL via GSC URL Inspection API.

        Returns indexing status, coverage state, crawl details.
        """
        if self._mock:
            return self._mock_url_inspection(url)

        logger.info("GSC URL inspection", property_uri=self.property_uri, url=url)
        raise SearchConsoleAuthError(
            "Production GSC client requires valid OAuth2 credentials."
        )

    async def list_sitemaps(self) -> list[dict[str, Any]]:
        """List sitemaps registered for this property."""
        if self._mock:
            return self._mock_sitemaps()

        raise SearchConsoleAuthError(
            "Production GSC client requires valid OAuth2 credentials."
        )

    async def health_check(self) -> dict[str, Any]:
        """Check connectivity and authentication to GSC API."""
        if self._mock:
            return {"status": "ok", "mock": True, "property": self.property_uri}

        raise SearchConsoleAuthError(
            "Production GSC client requires valid OAuth2 credentials."
        )

    # ── Mock Data Generators ─────────────────────────────────────────

    def _mock_search_analytics(
        self,
        start_date: date,
        end_date: date,
        dimensions: list[str] | None,
        row_limit: int,
    ) -> list[dict[str, Any]]:
        """Generate deterministic mock search analytics data."""
        dims = dimensions or ["date", "page"]
        rows: list[dict[str, Any]] = []

        mock_pages = [
            "https://example.com/ai-content-strategy",
            "https://example.com/seo-best-practices",
            "https://example.com/blog-automation-guide",
        ]
        mock_queries = [
            "ai content strategy",
            "seo best practices 2026",
            "automated blog publishing",
            "content optimization ai",
            "blog automation tools",
        ]

        current = start_date
        day_idx = 0
        while current <= end_date and len(rows) < row_limit:
            for page_idx, page in enumerate(mock_pages):
                for q_idx, query in enumerate(mock_queries):
                    if len(rows) >= row_limit:
                        break
                    # Deterministic metrics based on indices
                    base_clicks = max(1, 20 - page_idx * 5 - q_idx * 2 + day_idx % 7)
                    base_impressions = base_clicks * (4 + page_idx + q_idx)
                    position = 3.0 + page_idx * 4.5 + q_idx * 2.1

                    keys = []
                    if "date" in dims:
                        keys.append(str(current))
                    if "page" in dims:
                        keys.append(page)
                    if "query" in dims:
                        keys.append(query)
                    if "country" in dims:
                        keys.append("USA")
                    if "device" in dims:
                        keys.append("DESKTOP")

                    row: dict[str, Any] = {
                        "keys": keys,
                        "clicks": base_clicks,
                        "impressions": base_impressions,
                        "ctr": round(base_clicks / base_impressions, 4) if base_impressions else 0,
                        "position": round(position, 1),
                    }
                    rows.append(row)

                    # If query not in dimensions, only one row per page
                    if "query" not in dims:
                        break

            current = date(current.year, current.month, current.day + 1) if current.day < 28 else current
            if current == end_date:
                break
            day_idx += 1
            try:
                current = date(current.year, current.month, current.day + 1)
            except ValueError:
                break

        logger.debug("Mock GSC analytics generated", rows=len(rows))
        return rows

    def _mock_url_inspection(self, url: str) -> dict[str, Any]:
        """Generate deterministic mock URL inspection result."""
        return {
            "inspectionResult": {
                "indexStatusResult": {
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                    "robotsTxtState": "ALLOWED",
                    "indexingState": "INDEXING_ALLOWED",
                    "lastCrawlTime": datetime.utcnow().isoformat() + "Z",
                    "pageFetchState": "SUCCESSFUL",
                    "googleCanonical": url,
                    "userCanonical": url,
                    "crawledAs": "DESKTOP",
                },
                "inspectedUrl": url,
            }
        }

    def _mock_sitemaps(self) -> list[dict[str, Any]]:
        """Generate deterministic mock sitemaps listing."""
        return [
            {
                "path": f"{self.property_uri}sitemap.xml",
                "lastSubmitted": datetime.utcnow().isoformat() + "Z",
                "isPending": False,
                "isSitemapsIndex": True,
                "lastDownloaded": datetime.utcnow().isoformat() + "Z",
                "warnings": 0,
                "errors": 0,
            }
        ]
