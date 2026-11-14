"""
Zohra — Image Provider Router.

Routes image generation requests to the configured provider (Local AI, OpenAI, Pollinations, Procedural),
enforcing free-first routing, generative AI requirements, and paid API boundaries.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.media.providers.base import BaseImageProvider
from app.media.providers.local_generative_provider import LocalGenerativeImageProvider
from app.media.providers.local_provider import LocalImageProvider
from app.media.providers.openai_provider import OpenAIImageProvider
from app.media.providers.pollinations_provider import PollinationsGenerativeProvider
from app.media.providers.procedural_provider import ProceduralFallbackProvider

logger = get_logger("media.provider.router")


class ImageProviderRouter:
    """Manages image generation providers and free-first routing policies."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseImageProvider] = {}
        # Core generative and fallback providers
        self.register_provider(LocalGenerativeImageProvider())
        self.register_provider(OpenAIImageProvider())
        self.register_provider(LocalImageProvider())
        self.register_provider(ProceduralFallbackProvider())
        self.register_provider(PollinationsGenerativeProvider())

    def register_provider(self, provider: BaseImageProvider) -> None:
        self._providers[provider.name.lower()] = provider

    def get_provider(self, name: str | None = None) -> BaseImageProvider:
        """
        Retrieves provider by name, applying free-first routing and policy gates.
        """
        settings = get_settings()

        target_name = (name or getattr(settings, "ARTICLE_IMAGE_PROVIDER", "local_ai") or "local_ai").lower()

        # 1. Check OpenAI paid policy / missing key
        if target_name == "openai":
            has_key = bool(getattr(settings, "OPENAI_API_KEY", None))
            if not has_key:
                logger.warning("OpenAI requested for image generation but OPENAI_API_KEY is not set. Routing to fallback.")
                fallback = "local" if "local" in self._providers else "local_ai"
                return self._providers[fallback]
            return self._providers["openai"]

        # If a specific registered provider is explicitly requested by name, return it
        if name and name.lower() in self._providers:
            return self._providers[name.lower()]


        # 2. Check Procedural fallback policy
        if target_name in ("procedural", "local"):
            require_gen = getattr(settings, "ARTICLE_IMAGE_REQUIRE_GENERATIVE_AI", False)
            allow_proc = getattr(settings, "ARTICLE_IMAGE_ALLOW_PROCEDURAL_FALLBACK", False)
            if require_gen and not allow_proc and target_name == "procedural":
                logger.warning("Procedural provider requested but generative AI is required and procedural fallback is disabled.")
                return self._providers["local_ai"]
            return self._providers.get(target_name, self._providers["procedural"])

        # 3. Known registered provider
        if target_name in self._providers:
            return self._providers[target_name]

        logger.warning(f"Image provider '{target_name}' not registered. Using local_ai provider.")
        return self._providers.get("local_ai", LocalGenerativeImageProvider())



_router_instance: ImageProviderRouter | None = None


def get_image_provider_router() -> ImageProviderRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = ImageProviderRouter()
    return _router_instance
