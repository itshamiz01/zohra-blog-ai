"""
Zohra — Site model (Extended for Part 7).

Represents a website/publication profile served by the autonomous publishing engine.
Defines primary niche, target audiences, language/country, WordPress API connection,
publication cadence limits, publication windows, media policies, and SEO/Brand profiles.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import JSON_FIELD, ZohraBase


class Site(ZohraBase):
    __tablename__ = "sites"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    default_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    primary_country: Mapped[str] = mapped_column(String(50), nullable=False, default="global")

    niche: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    target_audiences: Mapped[list | None] = mapped_column(
        JSON_FIELD, nullable=True, default=list
    )  # e.g. ["developers", "tech enthusiast", "creators"]

    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    config_json: Mapped[dict | None] = mapped_column(JSON_FIELD, nullable=True, default=dict)

    # ── Part 7 WordPress & Publishing Profile Configuration ─────────────────
    wordpress_base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    wordpress_api_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    credential_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)

    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")

    default_author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_post_status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

    publishing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    autonomous_publishing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    media_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    internal_linking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    schema_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    indexing_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    max_posts_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    minimum_publish_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    publication_windows: Mapped[list | None] = mapped_column(
        JSON_FIELD, nullable=True, default=lambda: ["06:00-10:00", "14:00-18:00"]
    )

    brand_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    seo_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_policy_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    topics = relationship("SiteTopic", back_populates="site", cascade="all, delete-orphan")
    content_items = relationship("SiteContent", back_populates="site", cascade="all, delete-orphan")
    opportunities = relationship("ContentOpportunity", back_populates="site", cascade="all, delete-orphan")
    topic_clusters = relationship("TopicCluster", back_populates="site", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sites_domain_enabled", "domain", "enabled"),
    )
