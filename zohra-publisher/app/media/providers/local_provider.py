"""
Zohra — Local / Mock Image Generation Provider.

Generates high-resolution, valid WebP images locally using Pillow.
Used for deterministic unit testing, offline development, and zero-cost dry runs.
"""

from __future__ import annotations

import io
from PIL import Image, ImageDraw

from app.core.logging import get_logger
from app.media.models import ImagePrompt
from app.media.providers.base import BaseImageProvider
from app.media.providers.procedural_provider import ProceduralFallbackProvider

logger = get_logger("media.provider.local")


class LocalImageProvider(ProceduralFallbackProvider):
    """
    Procedural fallback image provider generating clean geometric gradient canvases.
    Retained for unit test fixtures, development, and emergency fallback.
    """

    @property
    def name(self) -> str:
        return "local"

    @property
    def is_generative_ai(self) -> bool:
        return False

    async def generate_image(
        self,
        prompt: ImagePrompt,
    ) -> tuple[bytes, str | None, float]:
        """
        Creates a high-resolution 16:9 editorial canvas with subtle gradients.
        Guaranteed to produce a valid, parseable WebP binary.
        """
        width = prompt.target_width or 1536
        height = prompt.target_height or 864

        # Generate a rich slate-to-navy gradient with subtle warm accents
        img = Image.new("RGB", (width, height), color=(26, 32, 44))
        draw = ImageDraw.Draw(img)

        # Draw smooth vertical gradient
        for y in range(height):
            ratio = y / height
            r = int(18 + (34 - 18) * ratio)
            g = int(24 + (48 - 24) * ratio)
            b = int(38 + (72 - 38) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Draw subtle geometric aesthetic elements (soft circles / editorial framing)
        draw.rounded_rectangle(
            [(int(width * 0.08), int(height * 0.08)), (int(width * 0.92), int(height * 0.92))],
            radius=24,
            outline=(60, 80, 110),
            width=2,
        )
        draw.ellipse(
            [(int(width * 0.65), int(height * 0.15)), (int(width * 0.88), int(height * 0.55))],
            fill=(45, 65, 95),
            outline=(80, 110, 150),
            width=1,
        )

        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=90, method=6)
        raw_bytes = buffer.getvalue()

        revised_prompt = f"Local synthetic visual: {prompt.prompt_text[:120]}"
        return raw_bytes, revised_prompt, 0.0

    async def health_check(self) -> bool:
        return True
