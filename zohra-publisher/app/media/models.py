"""
Zohra — Pydantic Schemas for Automatic Article Image Engine.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ImageType(str, Enum):
    EDITORIAL_PHOTOGRAPHY = "EDITORIAL_PHOTOGRAPHY"
    CONCEPTUAL_ILLUSTRATION = "CONCEPTUAL_ILLUSTRATION"
    EDUCATIONAL_VISUAL = "EDUCATIONAL_VISUAL"
    TECH_VISUALIZATION = "TECH_VISUALIZATION"
    INFOGRAPHIC = "INFOGRAPHIC"
    DIAGRAM = "DIAGRAM"
    DATA_VISUALIZATION = "DATA_VISUALIZATION"
    ABSTRACT_CONCEPT = "ABSTRACT_CONCEPT"
    PRODUCT_VISUAL = "PRODUCT_VISUAL"
    LOCATION_VISUAL = "LOCATION_VISUAL"


class ImageGenerationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    PROMPT_READY = "PROMPT_READY"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    REGENERATING = "REGENERATING"
    OPTIMIZING = "OPTIMIZING"
    READY = "READY"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    MEDIA_BLOCKED = "MEDIA_BLOCKED"


class VisualAnalysis(BaseModel):
    article_topic: str
    primary_subject: str
    main_entities: list[str] = Field(default_factory=list)
    article_category: str = "Technology"
    audience: str = "General"
    tone: str = "Informative"
    important_concepts: list[str] = Field(default_factory=list)
    location: str | None = None
    time_period: str | None = None
    visualizable_elements: list[str] = Field(default_factory=list)
    things_to_avoid: list[str] = Field(default_factory=list)
    brand_identity: str = "Professional Editorial"


class ImageConcept(BaseModel):
    subject: str
    environment: str
    visual_story: str
    composition: str
    mood: str
    lighting: str
    style: str
    important_objects: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    article_relationship: str
    image_type: ImageType = ImageType.EDITORIAL_PHOTOGRAPHY


class ImagePrompt(BaseModel):
    prompt_text: str
    negative_prompt: str | None = None
    target_aspect_ratio: str = "16:9"
    target_width: int = 1536
    target_height: int = 864
    quality: str = "standard"
    style_notes: str = ""
    retry_count: int = 0
    failure_feedback: str | None = None


class ValidationResult(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=100.0)
    subject_relevance: float = Field(ge=0.0, le=100.0)
    topic_relevance: float = Field(ge=0.0, le=100.0)
    visual_clarity: float = Field(ge=0.0, le=100.0)
    brand_suitability: float = Field(ge=0.0, le=100.0)
    safety_score: float = Field(ge=0.0, le=100.0)
    misleading_risk_score: float = Field(ge=0.0, le=100.0)
    failure_reasons: list[str] = Field(default_factory=list)
    suggested_prompt_fix: str | None = None


class ResponsiveVariant(BaseModel):
    label: str
    width: int
    height: int
    file_size_bytes: int
    local_path: str
    public_url: str


class OptimizationResult(BaseModel):
    primary_bytes: bytes
    content_hash: str
    perceptual_hash: str
    width: int
    height: int
    file_size_bytes: int
    mime_type: str = "image/webp"
    filename: str
    alt_text: str
    caption: str | None = None
    local_storage_path: str
    public_url: str
    responsive_variants: list[ResponsiveVariant] = Field(default_factory=list)


class BrandProfile(BaseModel):
    site_id: str | None = None
    visual_style: str = "Modern clean editorial, authentic, balanced depth and natural light"
    preferred_composition: str = "Rule of thirds, clear focal subject, uncluttered background"
    preferred_mood: str = "Professional, intelligent, inviting, authentic"
    photography_preference: float = 0.7
    illustration_preference: float = 0.3
    logo_policy: str = "NO_LOGOS"
    text_overlay_policy: str = "NO_TEXT"
    aspect_ratio: str = "16:9"
    quality: str = "standard"
