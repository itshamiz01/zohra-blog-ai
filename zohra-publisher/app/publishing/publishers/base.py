"""
Zohra — Base Publishing Provider Interface.
"""

from __future__ import annotations

import abc
from typing import Any


class BasePublishingProvider(abc.ABC):
    """Abstract interface for publication targets (WordPress, Heavenly, Git/Static)."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @abc.abstractmethod
    async def publish_article(
        self,
        prepared_payload: dict[str, Any],
        site_data: dict[str, Any],
        draft_project_data: dict[str, Any] | None = None,
        final_audit_package_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Publishes the article and associates its featured media.
        Returns a dict summarizing publication details (url, post_id, media_status, etc.).
        """
        pass

    @abc.abstractmethod
    async def attach_featured_media(
        self,
        media_data: dict[str, Any],
        post_identifier: Any,
        site_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Attaches or updates featured media for a publication."""
        pass

    @abc.abstractmethod
    async def verify_publication(
        self,
        publication_result: dict[str, Any],
        expected_title: str,
        expected_media_url: str | None = None,
    ) -> dict[str, Any]:
        """Verifies that published article and associated media are accessible."""
        pass
