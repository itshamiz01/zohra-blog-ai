"""
Zohra — Base Image Provider Interface.
"""

from __future__ import annotations

import abc
from typing import Any

from app.media.models import ImagePrompt


class BaseImageProvider(abc.ABC):
    """Abstract interface for image generation providers."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'openai', 'local', 'mock')."""
        pass

    @abc.abstractmethod
    async def generate_image(
        self,
        prompt: ImagePrompt,
    ) -> tuple[bytes, str | None, float]:
        """
        Generates an image.
        Returns:
            (raw_image_bytes, revised_prompt_or_asset_id, estimated_cost)
        """
        pass

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """Verifies provider connectivity and credential status."""
        pass
