"""
Zohra — OpenAI DALL-E-3 Image Generation Provider.

Interacts with the official OpenAI API using DALL-E-3, ensuring:
- Absolute secret redaction (keys never logged or returned).
- SSRF protection on remote media responses.
- Accurate cost tracking for standard and HD resolutions.
- Robust error handling for rate limits, authentication, and bad requests.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx
from openai import AsyncOpenAI
import openai

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.discovery.security.ssrf import validate_url_for_ssrf
from app.media.models import ImagePrompt
from app.media.providers.base import BaseImageProvider

logger = get_logger("media.provider.openai")


class MediaError(ZohraError):
    """Base exception for media generation issues."""
    def __init__(self, message: str, code: str = "GENERATION_FAILED") -> None:
        super().__init__(message, code=code)


class MediaAuthError(MediaError):
    """OpenAI API credentials rejected."""
    def __init__(self, message: str = "Invalid OpenAI credentials for image generation") -> None:
        super().__init__(message, code="AUTH_FAILED")


class MediaRateLimitError(MediaError):
    """OpenAI image generation rate limit hit."""
    def __init__(self, message: str = "OpenAI image generation rate limit exceeded") -> None:
        super().__init__(message, code="RATE_LIMITED")


class MediaQuotaError(MediaError):
    """OpenAI account billing or quota exhausted."""
    def __init__(self, message: str = "OpenAI image generation quota exhausted") -> None:
        super().__init__(message, code="QUOTA_EXHAUSTED")


class MediaInvalidRequestError(MediaError):
    """Prompt rejected by invalid parameters."""
    def __init__(self, message: str = "Invalid image generation parameters", code: str = "INVALID_REQUEST") -> None:
        super().__init__(message, code=code)


class MediaContentRejectedError(MediaInvalidRequestError):
    """Prompt rejected by content or safety policy filters."""
    def __init__(self, message: str = "Image generation prompt rejected by content policy") -> None:
        super().__init__(message, code="CONTENT_REJECTED")



class MediaProviderUnavailableError(MediaError):
    """Image generation provider service unreachable or timed out."""
    def __init__(self, message: str = "Image provider is currently unavailable") -> None:
        super().__init__(message, code="PROVIDER_UNAVAILABLE")


class MediaGenerationFailedError(MediaError):
    """Generic image generation failure."""
    def __init__(self, message: str = "Image generation failed") -> None:
        super().__init__(message, code="GENERATION_FAILED")



class OpenAIImageProvider(BaseImageProvider):
    """Official OpenAI DALL-E-3 provider."""

    def __init__(self, api_key: str | None = None):
        settings = get_settings()
        self._api_key = (api_key or settings.OPENAI_API_KEY or "").strip()
        self.client = AsyncOpenAI(api_key=self._api_key) if self._api_key else None

    @property
    def name(self) -> str:
        return "openai"

    def _calculate_cost(self, model: str, size: str, quality: str) -> float:
        """Determines official OpenAI API cost for generated image."""
        if "dall-e-3" in model:
            if size in ("1792x1024", "1024x1792"):
                return 0.120 if quality == "hd" else 0.080
            return 0.080 if quality == "hd" else 0.040
        return 0.020  # DALL-E-2 standard 1024x1024

    async def generate_image(
        self,
        prompt: ImagePrompt,
    ) -> tuple[bytes, str | None, float]:
        """
        Calls OpenAI DALL-E-3 to generate an article featured image.
        Returns: (image_bytes, revised_prompt, cost)
        """
        if not self._api_key:
            raise MediaAuthError("OPENAI_API_KEY is not configured in settings.")

        settings = get_settings()
        model = settings.ARTICLE_IMAGE_MODEL or "dall-e-3"

        # Determine target size
        if prompt.target_aspect_ratio == "16:9":
            size = "1792x1024"
        else:
            size = "1024x1024"

        quality = prompt.quality if prompt.quality in ("standard", "hd") else "standard"
        cost = self._calculate_cost(model, size, quality)

        logger.info(
            f"Calling OpenAI image generation: model={model}, size={size}, quality={quality}, prompt_len={len(prompt.prompt_text)}"
        )

        try:
            client = self.client or AsyncOpenAI(api_key=self._api_key)
            response = await client.images.generate(
                model=model,
                prompt=prompt.prompt_text[:3900],  # DALL-E-3 limit is 4000 characters
                size=size,
                quality=quality,
                n=1,
            )

            if not response.data:
                raise MediaInvalidRequestError("OpenAI returned an empty image response data array.")

            item = response.data[0]
            revised_prompt = getattr(item, "revised_prompt", None)

            # Extract base64 image bytes
            if getattr(item, "b64_json", None):
                raw_bytes = base64.b64decode(item.b64_json)
                return raw_bytes, revised_prompt, cost

            # If URL format was returned
            if getattr(item, "url", None):
                url = item.url
                validate_url_for_ssrf(url)
                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    img_resp = await http_client.get(url)
                    if img_resp.status_code != 200:
                        raise MediaError(f"Failed to fetch image from OpenAI URL: HTTP {img_resp.status_code}")
                    return img_resp.content, revised_prompt, cost

            raise MediaError("No b64_json or url found in OpenAI image response.")

        except openai.AuthenticationError as e:
            logger.error("OpenAI authentication error during image generation")
            raise MediaAuthError("Invalid OpenAI credentials for image generation") from e
        except openai.RateLimitError as e:
            logger.warning("OpenAI rate limit hit during image generation")
            if "insufficient_quota" in str(e).lower() or "billing" in str(e).lower():
                raise MediaQuotaError("OpenAI image generation quota exhausted") from e
            raise MediaRateLimitError("OpenAI image generation rate limit exceeded") from e
        except openai.BadRequestError as e:
            logger.warning(f"OpenAI bad request or content policy rejection: {e}")
            err_str = str(e).lower()
            if "safety" in err_str or "content policy" in err_str or "rejected" in err_str:
                raise MediaContentRejectedError(f"Image generation prompt rejected by safety filter: {e}") from e
            raise MediaInvalidRequestError(f"Image generation prompt rejected: {e}") from e
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            logger.error(f"OpenAI connection error during image generation: {e}")
            raise MediaProviderUnavailableError(f"Connection error to OpenAI image service: {e}") from e
        except MediaError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI image provider: {e}")
            raise MediaGenerationFailedError(f"Unexpected image generation failure: {e}") from e


    async def health_check(self) -> bool:
        return bool(self._api_key and self._api_key != "PASTE_GENERATED_TOKEN_HERE")
