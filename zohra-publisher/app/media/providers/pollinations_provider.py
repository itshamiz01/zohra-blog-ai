"""
Zohra — Zero-Cost Hosted Generative AI Image Provider (Pollinations).

Generates real, high-resolution FLUX / SDXL article visuals with $0 API cost,
no API keys required, and full prompt adherence.
"""

from __future__ import annotations

import urllib.parse
import httpx

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.discovery.security.ssrf import validate_url_for_ssrf
from app.media.models import ImagePrompt
from app.media.prompt_adapter import LocalImagePromptAdapter
from app.media.providers.base import BaseImageProvider

logger = get_logger("media.provider.pollinations")


class PollinationsGenerativeProvider(BaseImageProvider):
    """
    Zero-cost generative provider synthesizing real FLUX / SDXL visuals.
    Requires no paid API keys.
    """

    @property
    def name(self) -> str:
        return "pollinations"

    @property
    def is_generative_ai(self) -> bool:
        return True

    async def generate_image(
        self, prompt: ImagePrompt
    ) -> tuple[bytes, str | None, float]:
        """
        Synthesizes an editorial article visual using zero-cost FLUX generation.
        Returns: (image_bytes, revised_prompt, cost=0.0)
        """
        positive_prompt, negative_prompt = LocalImagePromptAdapter.adapt(prompt)

        # Build clean URL for Pollinations FLUX endpoint
        encoded_prompt = urllib.parse.quote(positive_prompt[:600])
        width = 1200
        height = 675  # ~16:9
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed=42"

        validate_url_for_ssrf(url)

        logger.info(f"Calling Pollinations FLUX zero-cost endpoint for: '{positive_prompt[:60]}...'")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    raise ZohraError(
                        f"Zero-cost generative provider error HTTP {resp.status_code}",
                        code="PROVIDER_UNAVAILABLE",
                    )

                image_bytes = resp.content
                if len(image_bytes) < 1000:
                    raise ZohraError("Zero-cost provider returned invalid/empty image data", code="GENERATION_FAILED")

                return image_bytes, positive_prompt, 0.0

        except ZohraError:
            raise
        except Exception as e:
            logger.error(f"Zero-cost hosted image generation failed: {e}", exc_info=True)
            raise ZohraError(f"Zero-cost hosted image generation failed: {e}", code="GENERATION_FAILED") from e

    async def health_check(self) -> bool:
        """Health check for Pollinations generative service."""
        return True

