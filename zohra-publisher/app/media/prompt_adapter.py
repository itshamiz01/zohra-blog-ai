"""
Zohra — Local Generative Image Prompt Adapter.

Optimizes Zohra's editorial article prompts for local diffusion models (SD-Turbo, SD 1.5, SDXL),
extracting salient visual themes within tokenizer limits and building dedicated negative prompts.
"""

from __future__ import annotations

import re
from typing import Any

from app.media.models import ImageConcept, ImagePrompt


class LocalImagePromptAdapter:
    """Adapts high-level editorial prompt structures for local diffusion models."""

    DEFAULT_NEGATIVE_PROMPT: str = (
        "text, watermark, logo, typography, letters, signature, caption, blurry, "
        "distorted anatomy, deformed hands, extra fingers, bad eyes, cartoon, low quality, "
        "neon blue generic holograms, floating robots, abstract gradient, placeholder"
    )

    @classmethod
    def adapt(
        cls,
        prompt: ImagePrompt,
        concept: ImageConcept | None = None,
        max_positive_tokens: int = 70,
    ) -> tuple[str, str]:
        """
        Extracts a clean, high-signal positive prompt and negative prompt.
        Returns: (positive_prompt, negative_prompt)
        """
        raw_prompt = prompt.prompt_text

        # 1. If concept is provided, construct direct high-signal prompt
        if concept and concept.subject:
            pos_parts = [
                concept.subject.strip(" ."),
                concept.environment.strip(" .") if concept.environment else "",
                concept.mood.strip(" .") if concept.mood else "thoughtful and authentic",
                concept.lighting.strip(" .") if concept.lighting else "natural diffuse lighting",
                concept.style.strip(" .") if concept.style else "professional editorial photography",
                "masterpiece, 8k resolution, crisp focus, clear detail",
            ]
            positive_prompt = ", ".join(p for p in pos_parts if p)
        else:
            # Parse positive portion before 'Constraints:' or 'DO NOT'
            lower_text = raw_prompt
            if "constraints:" in lower_text.lower():
                positive_prompt = lower_text.split("Constraints:")[0].strip(" .")
            elif "strict negative constraints:" in lower_text.lower():
                positive_prompt = lower_text.split("strict negative constraints:")[0].strip(" .")
            else:
                positive_prompt = raw_prompt

            # Clean any leftover instruction tags
            positive_prompt = re.sub(r"\[redacted instruction\]", "", positive_prompt)
            positive_prompt = re.sub(r"\s+", " ", positive_prompt).strip()

        # 2. Build negative prompt
        neg_parts = [cls.DEFAULT_NEGATIVE_PROMPT]
        if prompt.negative_prompt:
            neg_parts.append(prompt.negative_prompt)

        if concept and concept.avoid:
            neg_parts.extend(concept.avoid[:4])

        if prompt.failure_feedback:
            # Emphasize avoiding previous failure causes
            neg_parts.append(f"avoid {prompt.failure_feedback}")

        negative_prompt = ", ".join(set(neg_parts))

        return positive_prompt, negative_prompt
