"""Article Featured Media & Brand Image Engine: Part 12 models.

Revision ID: 011_article_image_engine
Revises: 010_reddit_engine
Create Date: 2026-10-03 21:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "011_article_image_engine"
down_revision = "010_reddit_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. article_featured_media ──────────────────────────────────────
    op.create_table(
        "article_featured_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="openai"),
        sa.Column("model", sa.String(length=64), nullable=False, server_default="dall-e-3"),
        sa.Column("generation_status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("revised_prompt", sa.Text(), nullable=True),
        sa.Column("visual_concept_json", sa.JSON(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("validation_details_json", sa.JSON(), nullable=True),
        sa.Column("local_storage_path", sa.String(length=1024), nullable=True),
        sa.Column("public_url", sa.String(length=2048), nullable=True),
        sa.Column("wordpress_media_id", sa.Integer(), nullable=True),
        sa.Column("wordpress_url", sa.String(length=2048), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False, server_default="image/webp"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1536"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="864"),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alt_text", sa.String(length=512), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("perceptual_hash", sa.String(length=64), nullable=True),
        sa.Column("responsive_variants_json", sa.JSON(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("provenance_metadata", sa.JSON(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_afm_site_article", "article_featured_media", ["site_id", "article_id"])
    op.create_index("ix_afm_content_hash", "article_featured_media", ["content_hash"])
    op.create_index("ix_afm_wp_media_id", "article_featured_media", ["wordpress_media_id"])
    op.create_index("ix_afm_status", "article_featured_media", ["generation_status"])

    # ── 2. article_image_brand_profiles ───────────────────────────────
    op.create_table(
        "article_image_brand_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("visual_style", sa.String(length=255), nullable=False),
        sa.Column("preferred_composition", sa.String(length=255), nullable=False),
        sa.Column("preferred_mood", sa.String(length=255), nullable=False),
        sa.Column("photography_preference", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("illustration_preference", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("logo_policy", sa.String(length=64), nullable=False, server_default="NO_LOGOS"),
        sa.Column("text_overlay_policy", sa.String(length=64), nullable=False, server_default="NO_TEXT"),
        sa.Column("aspect_ratio", sa.String(length=32), nullable=False, server_default="16:9"),
        sa.Column("quality", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id"),
    )
    op.create_index("ix_aibp_site", "article_image_brand_profiles", ["site_id"])


def downgrade() -> None:
    op.drop_table("article_image_brand_profiles")
    op.drop_table("article_featured_media")
