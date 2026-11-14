"""Zohra — Discovery Adapters package."""

from app.discovery.adapters.base import FetchResult, RawFetchedItem, SourceAdapter
from app.discovery.adapters.rss import RSSAdapter
from app.discovery.adapters.search import MockSearchProvider, SearchProvider

__all__ = [
    "RawFetchedItem",
    "FetchResult",
    "SourceAdapter",
    "RSSAdapter",
    "SearchProvider",
    "MockSearchProvider",
]
