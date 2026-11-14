"""
Zohra — Publishing Provider Router.
"""

from __future__ import annotations

from typing import Any

from app.core.exceptions import ZohraError
from app.publishing.publishers.base import BasePublishingProvider
from app.publishing.publishers.git_static import GitStaticPublisher
from app.publishing.publishers.heavenly import HeavenlyPublisher
from app.publishing.publishers.wordpress import WordPressPublisher


class PublishingProviderRouter:
    """Manages available publishing providers and routes according to site configuration."""

    def __init__(self) -> None:
        self._providers: dict[str, BasePublishingProvider] = {
            "wordpress": WordPressPublisher(),
            "heavenly": HeavenlyPublisher(),
            "git_static": GitStaticPublisher(),
            "static": GitStaticPublisher(),
        }

    def register_provider(self, provider: BasePublishingProvider) -> None:
        self._providers[provider.name.lower()] = provider

    def get_provider(self, target: str | None = None, site_data: dict[str, Any] | None = None) -> BasePublishingProvider:
        """Determines active publisher provider from target name or site configuration."""
        site = site_data or {}
        chosen_target = (
            target
            or site.get("publisher_type")
            or site.get("publish_target")
            or ("heavenly" if site.get("heavenly_site_url") else "wordpress")
        ).lower()

        if chosen_target in self._providers:
            return self._providers[chosen_target]

        raise ZohraError(f"Unsupported publishing provider: '{chosen_target}'", code="UNKNOWN_PUBLISHER")


_router_instance: PublishingProviderRouter | None = None


def get_publishing_router() -> PublishingProviderRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = PublishingProviderRouter()
    return _router_instance
