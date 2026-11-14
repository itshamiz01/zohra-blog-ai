"""
Zohra — Article Image Prompt Builder.

Assembles detailed, high-quality, professional image prompts for AI providers (DALL-E-3).
Strictly enforces NO TEXT inside hero images, prevents generic tropes, and incorporates failure feedback.
"""

from __future__ import annotations

from app.media.models import BrandProfile, ImageConcept, ImagePrompt


class ArticleImagePromptBuilder:
    """Constructs production-grade image generation prompts."""

    @classmethod
    def build_prompt(
        cls,
        concept: ImageConcept,
        brand: BrandProfile | None = None,
        retry_count: int = 0,
        failure_feedback: str | None = None,
    ) -> ImagePrompt:
        """
        Builds a comprehensive prompt string and negative constraints.
        """
        effective_brand = brand or BrandProfile()

        # Target dimensions for 16:9 hero image: 1792x1024 (standard DALL-E-3 16:9)
        aspect_ratio = effective_brand.aspect_ratio or "16:9"
        target_width = 1792 if aspect_ratio == "16:9" else 1024
        target_height = 1024 if aspect_ratio == "16:9" else 1024

        parts: list[str] = []

        # 1. Main visual subject and story
        parts.append(f"A high-resolution editorial photograph: {concept.subject}.")
        parts.append(f"Setting: {concept.environment}.")
        parts.append(f"Story: {concept.visual_story}.")

        # 2. Composition and Lighting
        parts.append(f"Composition: {concept.composition}.")
        parts.append(f"Lighting: {concept.lighting}.")
        parts.append(f"Mood and Style: {concept.mood}, {concept.style}.")

        # 3. Important elements
        if concept.important_objects:
            objs = ", ".join(concept.important_objects)
            parts.append(f"Key visible details: {objs}.")

        # 4. Strict Quality and Anti-Artifact Rules
        parts.append(
            "Ultra-clean editorial magazine quality, balanced colors, sharp focal focus, realistic natural textures."
        )

        # 5. Strict Negative Constraints (NO TEXT rule is paramount)
        negative_rules = [
            "DO NOT include any text, typography, letters, headlines, words, watermarks, or logos in the image",
            "no fake computer interface popups with illegible text",
            "no distorted hands, unnatural fingers, or awkward anatomy",
            "no generic glowing blue AI holograms or floating robots",
        ]
        if concept.avoid:
            negative_rules.extend(concept.avoid[:4])

        parts.append(f"Constraints: {'; '.join(negative_rules)}.")

        # 6. Failure Feedback adjustment (if regenerating after quality rejection)
        if failure_feedback:
            parts.append(f"CRITICAL CORRECTION FROM PREVIOUS ATTEMPT: {failure_feedback}")

        full_prompt = " ".join(parts).strip()

        negative_prompt = (
            "text, typography, watermark, logo, words, letters, headline, title, blurry, "
            "distorted anatomy, extra fingers, cartoonish, low resolution, noise, artifacts"
        )

        return ImagePrompt(
            prompt_text=full_prompt,
            negative_prompt=negative_prompt,
            target_aspect_ratio=aspect_ratio,
            target_width=target_width,
            target_height=target_height,
            quality=effective_brand.quality or "standard",
            style_notes=concept.style,
            retry_count=retry_count,
            failure_feedback=failure_feedback,
        )
