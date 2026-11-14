"""
Zohra — Source Adapter Interfaces.

Defines the contract for external data ingestion adapters:
RSS/Atom, official APIs, news feeds, search engines, and social signals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawFetchedItem:
    """Standardized raw document extracted by an adapter before normalization."""

    url: str
    title: str
    external_id: str | None = None
    summary: str | None = None
    content_text: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResult:
    """Outcome of a source fetch operation."""

    success: bool
    status_code: int | None = None
    items: list[RawFetchedItem] = field(default_factory=list)
    error_message: str | None = None
    response_time_ms: int = 0
    etag: str | None = None
    last_modified: str | None = None


class SourceAdapter(ABC):
    """Abstract base class for all external source adapters."""

    @abstractmethod
    async def fetch(self, source_url: str, metadata: dict[str, Any] | None = None) -> FetchResult:
        """Fetch items from the source endpoint."""
        ...

    @abstractmethod
    async def health_check(self, source_url: str) -> bool:
        """Verify if source endpoint is reachable and responsive."""
        ...
