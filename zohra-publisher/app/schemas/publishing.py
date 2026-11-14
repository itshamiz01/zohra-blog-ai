"""
Zohra — Pydantic Schemas for Part 7 Publishing Engine.

Defines schemas for:
- Publication authorization & validation
- Site profiles & health
- Media planning, generation, and rights
- Internal link candidate resolution
- Final SEO packaging and structured schema
- Publication jobs, preview, scheduling, and approvals
- Published articles & indexing handoffs
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Enums ────────────────────────────────────────────────────────────

class PublicationMode(str, Enum):
    DRAFT = "DRAFT"
    SCHEDULE = "SCHEDULE"
    PUBLISH_NOW = "PUBLISH_NOW"


class PublicationJobStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    MEDIA_PREPARING = "MEDIA_PREPARING"
    MEDIA_READY = "MEDIA_READY"
    LINKS_RESOLVING = "LINKS_RESOLVING"
    SEO_PACKAGING = "SEO_PACKAGING"
    RENDERING = "RENDERING"
    PREVIEW_READY = "PREVIEW_READY"
    SCHEDULED_FOR_PUBLICATION = "SCHEDULED_FOR_PUBLICATION"
    PUBLISHING = "PUBLISHING"
    VERIFYING = "VERIFYING"
    PUBLISHED = "PUBLISHED"
    INDEXING_HANDOFF = "INDEXING_HANDOFF"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    CANCELLED = "CANCELLED"


class AssetType(str, Enum):
    FEATURED_IMAGE = "FEATURED_IMAGE"
    ORIGINAL_CHART = "ORIGINAL_CHART"
    ORIGINAL_DIAGRAM = "ORIGINAL_DIAGRAM"
    SCREENSHOT = "SCREENSHOT"
    ILLUSTRATION = "ILLUSTRATION"
    INFOGRAPHIC = "INFOGRAPHIC"


class MediaSourceStrategy(str, Enum):
    AI_GENERATED = "AI_GENERATED"
    ORIGINAL_CHART = "ORIGINAL_CHART"
    ORIGINAL_DIAGRAM = "ORIGINAL_DIAGRAM"
    SCREENSHOT = "SCREENSHOT"
    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    LICENSED_LIBRARY = "LICENSED_LIBRARY"
    USER_PROVIDED = "USER_PROVIDED"
    NO_MEDIA = "NO_MEDIA"


class MediaStatus(str, Enum):
    PLANNED = "PLANNED"
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"


# ── Schemas ──────────────────────────────────────────────────────────

class SiteProfileCreate(BaseModel):
    name: str = Field(..., max_length=255)
    domain: str = Field(..., max_length=255)
    default_language: str = Field("en", max_length=10)
    primary_country: str = Field("global", max_length=50)
    niche: str = Field(..., max_length=255)
    description: str | None = None
    target_audiences: list[str] = Field(default_factory=list)

    wordpress_base_url: str | None = None
    wordpress_api_url: str | None = None
    credential_ref: str | None = None

    timezone: str = "UTC"
    default_author_id: int | None = None
    default_category_id: int | None = None
    default_post_status: str = "draft"

    publishing_enabled: bool = False
    autonomous_publishing_enabled: bool = False
    media_enabled: bool = True
    internal_linking_enabled: bool = True
    schema_enabled: bool = True
    indexing_enabled: bool = True

    max_posts_per_day: int = 5
    minimum_publish_interval_minutes: int = 60
    publication_windows: list[str] = Field(default_factory=lambda: ["06:00-10:00", "14:00-18:00"])


class SiteProfileUpdate(BaseModel):
    name: str | None = None
    niche: str | None = None
    description: str | None = None
    target_audiences: list[str] | None = None

    wordpress_base_url: str | None = None
    wordpress_api_url: str | None = None
    credential_ref: str | None = None

    timezone: str | None = None
    default_author_id: int | None = None
    default_category_id: int | None = None
    default_post_status: str | None = None

    publishing_enabled: bool | None = None
    autonomous_publishing_enabled: bool | None = None
    media_enabled: bool | None = None
    internal_linking_enabled: bool | None = None
    schema_enabled: bool | None = None
    indexing_enabled: bool | None = None

    max_posts_per_day: int | None = None
    minimum_publish_interval_minutes: int | None = None
    publication_windows: list[str] | None = None


class SiteHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    site_id: uuid.UUID
    api_status: str
    auth_status: str
    media_status: str
    circuit_state: str
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    checked_at: datetime


class MediaPlanItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | None = None
    asset_type: AssetType
    purpose: str
    placement: str = "featured"
    required: bool = True
    source_strategy: MediaSourceStrategy = MediaSourceStrategy.AI_GENERATED
    generation_prompt: str | None = None
    preferred_aspect_ratio: str = "16:9"
    target_width: int = 1200
    target_height: int = 675
    alt_text_plan: str | None = None
    caption_required: bool = False
    rights_requirement: str = "COMMERCIAL_ALLOWED"
    status: MediaStatus = MediaStatus.PLANNED


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    media_plan_id: uuid.UUID
    asset_type: str
    origin_type: str
    source_url: str | None = None
    source_name: str | None = None
    creator: str | None = None
    license_type: str
    attribution_required: bool
    attribution_text: str | None = None
    commercial_use_allowed: bool
    modification_allowed: bool
    rights_verified: bool
    rights_notes: str | None = None
    content_hash: str
    mime_type: str
    width: int
    height: int
    file_size_bytes: int
    alt_text: str
    caption: str | None = None
    description: str | None = None
    cost: float
    wordpress_media_id: int | None = None
    wordpress_url: str | None = None


class ResolvedInternalLink(BaseModel):
    source_section_id: str
    target_url: str
    target_title: str
    anchor_text: str
    relevance_score: float


class SEOPackageData(BaseModel):
    title: str
    meta_title: str
    meta_description: str
    slug: str
    canonical_url: str
    primary_topic: str | None = None
    primary_keyword: str | None = None
    robots_directive: str = "index,follow"
    schema_types: list[str] = Field(default_factory=list)
    structured_data_json: dict[str, Any] = Field(default_factory=dict)
    open_graph_title: str | None = None
    open_graph_description: str | None = None
    open_graph_image_url: str | None = None
    twitter_title: str | None = None
    twitter_description: str | None = None
    twitter_image_url: str | None = None



class PublicationPreviewData(BaseModel):
    title: str
    slug: str
    rendered_html: str
    category_id: int | None = None
    category_name: str | None = None
    tag_names: list[str] = Field(default_factory=list)
    author_id: int | None = None
    featured_image_url: str | None = None
    featured_media_id: int | None = None
    seo_package: SEOPackageData
    schema_package: dict[str, Any]
    internal_links: list[ResolvedInternalLink] = Field(default_factory=list)
    external_citations_count: int = 0
    scheduled_for: datetime | None = None
    publication_mode: PublicationMode


class PublicationCreateRequest(BaseModel):
    site_id: uuid.UUID
    draft_version_id: uuid.UUID
    audit_id: uuid.UUID
    publication_mode: PublicationMode = PublicationMode.DRAFT
    scheduled_for: datetime | None = None
    desired_status: str = "draft"


class PublicationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    site_id: uuid.UUID
    article_id: uuid.UUID
    draft_version_id: uuid.UUID
    audit_id: uuid.UUID
    authorization_id: uuid.UUID | None = None
    idempotency_key: str
    content_hash: str
    publication_mode: str
    desired_status: str
    scheduled_for: datetime | None = None
    wordpress_post_id: int | None = None
    wordpress_post_url: str | None = None
    status: str
    attempt_count: int
    last_error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class PublicationApprovalRequest(BaseModel):
    action: ApprovalAction
    reason: str | None = None


class PublishedArticlePackage(BaseModel):
    article_id: str
    site_id: str
    draft_version_id: str
    audit_id: str
    publication_job_id: str

    wordpress: dict[str, Any] = Field(default_factory=dict)
    heavenly: dict[str, Any] | None = None
    publisher_target: str = "wordpress"
    published_at: str | None = None
    scheduled_at: str | None = None

    content: dict[str, str]
    taxonomy: dict[str, list[int]]
    media: dict[str, Any]
    seo: dict[str, Any]
    links: dict[str, int]
    verification: dict[str, Any]
    indexing_handoff: dict[str, Any]
    publication_cost: dict[str, Any]
