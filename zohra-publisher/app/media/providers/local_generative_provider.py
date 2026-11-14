"""
Zohra — Local Generative AI Image Provider.

Executes genuine on-device text-to-image synthesis using local diffusion models
via LocalImageModelManager and LocalImagePromptAdapter. Zero external API cost.
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.media.local_manager import get_local_model_manager
from app.media.models import ImagePrompt
from app.media.prompt_adapter import LocalImagePromptAdapter
from app.media.providers.base import BaseImageProvider

logger = get_logger("media.provider.local_generative")


class LocalGenerativeImageProvider(BaseImageProvider):
    """
    Production-grade local generative text-to-image provider.
    Runs real open diffusion models on local hardware without paid API keys.
    """

    def __init__(self, model_id: str | None = None) -> None:
        self._model_id = model_id
        self.manager = get_local_model_manager()

    @property
    def name(self) -> str:
        return "local_ai"

    @property
    def is_generative_ai(self) -> bool:
        return True

    async def generate_image(
        self, prompt: ImagePrompt
    ) -> tuple[bytes, str | None, float]:
        """
        Synthesizes a real article image matching the article prompt using local diffusion.
        Returns: (png_bytes, revised_prompt, cost=0.0)
        """
        settings = get_settings()

        # 1. Adapt structured prompt for diffusion model
        positive_prompt, negative_prompt = LocalImagePromptAdapter.adapt(prompt)

        # 2. Extract execution parameters
        width = getattr(settings, "LOCAL_IMAGE_WIDTH", 512)
        height = getattr(settings, "LOCAL_IMAGE_HEIGHT", 512)
        steps = getattr(settings, "LOCAL_IMAGE_STEPS", 1)
        guidance = getattr(settings, "LOCAL_IMAGE_GUIDANCE", 0.0)

        logger.info(
            f"LocalGenerativeImageProvider synthesizing: model={self.manager.model_id or settings.LOCAL_IMAGE_MODEL_ID}, "
            f"dims={width}x{height}, steps={steps}, prompt_len={len(positive_prompt)}"
        )

        t0 = time.time()
        try:
            image_bytes, metadata = await self.manager.generate_image(
                prompt=positive_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                steps=steps,
                guidance_scale=guidance,
            )

            # Phase 17 & 18: High-quality editorial 16:9 dimension strategy
            import io
            from PIL import Image, ImageOps

            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                cur_w, cur_h = pil_img.size
                if cur_w < 800 or cur_h < 450 or abs((cur_w / cur_h) - (16 / 9)) > 0.1:
                    target_w = prompt.target_width if prompt.target_width and prompt.target_width >= 800 else 1024
                    target_h = int(target_w * 9 / 16)
                    adapted = ImageOps.fit(pil_img, (target_w, target_h), method=Image.Resampling.LANCZOS)
                    out_buf = io.BytesIO()
                    adapted.save(out_buf, format="PNG")
                    image_bytes = out_buf.getvalue()

            revised_prompt = f"{positive_prompt} [seed: {metadata.get('seed')}]"
            logger.info(f"Local AI image synthesized and adapted successfully in {time.time() - t0:.2f}s")
            return image_bytes, revised_prompt, 0.0


        except ZohraError:
            raise
        except Exception as e:
            logger.error(f"Local generative image synthesis failed: {e}", exc_info=True)
            raise ZohraError(f"Local image generation failed: {e}", code="GENERATION_FAILED") from e

    async def health_check(self) -> bool:
        """Checks if local generative model manager is healthy."""
        health = self.manager.get_health()
        return health["status"] in ("AVAILABLE", "LOADING")

