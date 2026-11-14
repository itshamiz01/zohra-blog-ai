"""
Zohra — Procedural Fallback Image Provider.

Generates emergency procedural placeholder visuals for development, test mocks,
and disaster fallback. Strictly marked as PROCEDURAL so it cannot bypass generative gates.
"""

from __future__ import annotations

import io
from PIL import Image, ImageDraw

from app.core.logging import get_logger
from app.media.models import ImagePrompt
from app.media.providers.base import BaseImageProvider

logger = get_logger("media.provider.procedural")


class ProceduralFallbackProvider(BaseImageProvider):
    """
    Emergency placeholder generator creating clean procedural geometric gradients.
    Explicitly distinct from generative AI models.
    """

    @property
    def name(self) -> str:
        return "procedural"

    @property
    def is_generative_ai(self) -> bool:
        return False

    async def generate_image(
        self, prompt: ImagePrompt
    ) -> tuple[bytes, str | None, float]:
        """
        Creates a procedural placeholder image.
        Returns: (png_bytes, None, 0.0)
        """
        logger.warning(
            "ProceduralFallbackProvider invoked. This is a non-generative placeholder visual."
        )

        width = prompt.target_width if prompt.target_width else 1536
        height = prompt.target_height if prompt.target_height else 864

        # Generate a balanced editorial gradient
        img = Image.new("RGB", (width, height), color=(18, 24, 38))
        draw = ImageDraw.Draw(img)

        # Smooth vertical gradient overlay
        for y in range(height):
            ratio = y / height
            r = int(24 + (15 * ratio))
            g = int(32 + (40 * ratio))
            b = int(55 + (70 * ratio))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Soft diagonal accent
        draw.polygon(
            [(0, height), (width, int(height * 0.4)), (width, height)],
            fill=(30, 50, 85),
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        return image_bytes, None, 0.0

    async def health_check(self) -> bool:
        """Procedural provider is always healthy as it requires no external models or keys."""
        return True

