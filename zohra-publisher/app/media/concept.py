"""
Zohra — Image Concept Generator.

Transforms visual analysis into a rich, structured visual concept
matching the site's brand profile and editorial style.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.media.models import BrandProfile, ImageConcept, ImageType, VisualAnalysis

logger = get_logger("media.concept")


class ImageConceptGenerator:
    """Generates structured visual concepts for article featured hero images."""

    @classmethod
    def determine_image_type(
        cls,
        analysis: VisualAnalysis,
        brand: BrandProfile,
    ) -> ImageType:
        """Selects the most suitable image type based on topic and brand preferences."""
        topic_lower = (analysis.article_topic + " " + analysis.article_category).lower()

        if "code" in topic_lower or "cloud" in topic_lower or "infrastructure" in topic_lower or "architecture" in topic_lower:
            return ImageType.TECH_VISUALIZATION
        elif "diagram" in topic_lower or "workflow" in topic_lower or "process" in topic_lower:
            return ImageType.EDUCATIONAL_VISUAL
        elif "concept" in topic_lower or "future" in topic_lower or "ethics" in topic_lower:
            return ImageType.CONCEPTUAL_ILLUSTRATION
        elif brand.photography_preference >= brand.illustration_preference:
            return ImageType.EDITORIAL_PHOTOGRAPHY
        else:
            return ImageType.CONCEPTUAL_ILLUSTRATION

    @classmethod
    def generate_concept(
        cls,
        analysis: VisualAnalysis,
        brand: BrandProfile | None = None,
    ) -> ImageConcept:
        """
        Creates a structured, validated visual concept for the image generation provider.
        """
        effective_brand = brand or BrandProfile()
        image_type = cls.determine_image_type(analysis, effective_brand)

        topic = analysis.article_topic
        primary_subject = analysis.primary_subject

        if image_type == ImageType.EDITORIAL_PHOTOGRAPHY:
            subject = f"An authentic, focused person thoughtfully engaged with tools related to {topic}"
            environment = "A contemporary, sunlit studio or library workspace with warm wood surfaces and orderly desk materials"
            visual_story = f"Captures genuine mastery and balanced workflow when applying {topic} in practice"
            composition = "Medium close-up shot, rule of thirds, shallow depth of field with soft bokeh in background"
            mood = "Thoughtful, calm, productive, authentic"
            lighting = "Soft natural window daylight coming from the left with subtle rim lighting"
            style = "High-end editorial lifestyle photography, shot on 35mm lens, natural color grading, no post-processed HDR artifacts"
        elif image_type == ImageType.TECH_VISUALIZATION:
            subject = f"Clean, elegant spatial visualization of structured digital architecture for {topic}"
            environment = "Minimalist modern tech workspace with subtle architectural elements"
            visual_story = f"Demonstrates clarity, robustness, and systematic structure in {topic}"
            composition = "Isometric or wide three-quarter perspective, geometric harmony, balanced negative space"
            mood = "Sophisticated, precise, forward-looking"
            lighting = "Clean diffused studio lighting with elegant tonal contrast"
            style = "Modern architectural technology render, matte finish, restrained palette"
        elif image_type == ImageType.EDUCATIONAL_VISUAL:
            subject = f"Clear, engaging study setup demonstrating practical application of {topic}"
            environment = "Organized modern study environment with tactile learning materials and tablet interface"
            visual_story = f"Shows progressive learning and clarity in mastering {topic}"
            composition = "Overhead flat-lay or high-angle perspective, meticulous organization, clear visual hierarchy"
            mood = "Inspiring, approachable, educational"
            lighting = "Bright, even daylight illumination without harsh shadows"
            style = "Premium educational editorial visual, crisp focal details"
        else:
            subject = f"Evocative conceptual metaphor representing the balance and potential of {topic}"
            environment = "Abstract architectural space with clean geometry and atmospheric depth"
            visual_story = f"Communicates the underlying transformation and insight behind {topic}"
            composition = "Centered or dynamic diagonal balance, bold silhouette against refined background"
            mood = "Inspirational, visionary, contemplative"
            lighting = "Dramatic golden-hour directional light casting gentle linear shadows"
            style = "Refined conceptual editorial art, tactile textures, rich earthy and slate tones"

        # Combine important objects
        objects = analysis.visualizable_elements[:4] if analysis.visualizable_elements else [
            "neatly arranged workspace essentials",
            "reference materials",
            "ambient desk lamp",
        ]

        # Combine avoid lists
        avoid_items = list(dict.fromkeys(analysis.things_to_avoid + [
            "text of any kind",
            "words",
            "letters",
            "watermarks",
            "logos",
            "distorted hands",
            "unnatural facial expressions",
        ]))

        relationship = f"Visually represents the core thesis of the article: {analysis.primary_subject}"

        return ImageConcept(
            subject=subject,
            environment=environment,
            visual_story=visual_story,
            composition=composition,
            mood=mood,
            lighting=lighting,
            style=style,
            important_objects=objects,
            avoid=avoid_items,
            article_relationship=relationship,
            image_type=image_type,
        )
