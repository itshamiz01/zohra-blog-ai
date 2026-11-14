"""Media Intelligence, SEO Packaging & WordPress Publishing Engine: Part 7 models.

Revision ID: 006_publishing_engine
Revises: 005_audit_engine
Create Date: 2026-10-02 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "006_publishing_engine"
down_revision = "005_audit_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Extend sites table with Part 7 fields ───────────────────────
    with op.batch_alter_table("sites") as batch_op:
        batch_op.add_column(sa.Column("wordpress_base_url", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("wordpress_api_url", sa.String(length=1024), nullable=True))
        batch_op.add_column(sa.Column("credential_ref", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"))
        batch_op.add_column(sa.Column("default_author_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("default_category_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("default_post_status", sa.String(length=32), nullable=False, server_default="draft"))
        batch_op.add_column(sa.Column("publishing_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("autonomous_publishing_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("media_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("internal_linking_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("schema_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("indexing_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("max_posts_per_day", sa.Integer(), nullable=False, server_default="5"))
        batch_op.add_column(sa.Column("minimum_publish_interval_minutes", sa.Integer(), nullable=False, server_default="60"))
        batch_op.add_column(sa.Column("publication_windows", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("brand_profile_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("seo_profile_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("media_policy_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("risk_policy_id", sa.String(length=64), nullable=True))

    # ── 2. publication_authorizations ──────────────────────────────────
    op.create_table(
        "publication_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("audit_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("authorized_action", sa.String(length=32), nullable=False, server_default="PUBLISH"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pub_auth_audit_status", "publication_authorizations", ["audit_id", "status"])
    op.create_index("ix_pub_auth_hash", "publication_authorizations", ["content_hash"])

    # ── 3. visual_brand_profiles ───────────────────────────────────────
    op.create_table(
        "visual_brand_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("visual_style", sa.String(length=128), nullable=False, server_default="modern_editorial"),
        sa.Column("composition_preferences", sa.Text(), nullable=True),
        sa.Column("typography_policy", sa.Text(), nullable=True),
        sa.Column("logo_policy", sa.Text(), nullable=True),
        sa.Column("preferred_aspect_ratios", sa.JSON(), nullable=True),
        sa.Column("forbidden_visual_patterns", sa.JSON(), nullable=True),
        sa.Column("image_text_policy", sa.String(length=64), nullable=False, server_default="disallow_baked_text"),
        sa.Column("photorealism_policy", sa.String(length=64), nullable=False, server_default="authentic_editorial"),
        sa.Column("illustration_policy", sa.String(length=64), nullable=False, server_default="minimalist_vector"),
        sa.Column("palette_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id"),
    )
    op.create_index("ix_vbp_site_id", "visual_brand_profiles", ["site_id"])

    # ── 4. publication_jobs ────────────────────────────────────────────
    op.create_table(
        "publication_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_id", sa.Uuid(), nullable=False),
        sa.Column("audit_id", sa.Uuid(), nullable=False),
        sa.Column("authorization_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("publication_mode", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("desired_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wordpress_post_id", sa.Integer(), nullable=True),
        sa.Column("wordpress_post_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CREATED"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preview_json", sa.JSON(), nullable=True),
        sa.Column("rendered_html", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audit_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["authorization_id"], ["publication_authorizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_pub_job_site_status", "publication_jobs", ["site_id", "status"])
    op.create_index("ix_pub_job_article", "publication_jobs", ["article_id"])

    # ── 5. publication_schedules ───────────────────────────────────────
    op.create_table(
        "publication_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_local_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("scheduled_utc_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_job_id"], ["publication_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pub_sched_time", "publication_schedules", ["scheduled_utc_time", "status"])

    # ── 6. publication_events ──────────────────────────────────────────
    op.create_table(
        "publication_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("previous_state", sa.String(length=64), nullable=True),
        sa.Column("new_state", sa.String(length=64), nullable=False),
        sa.Column("wordpress_post_id", sa.Integer(), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=64), nullable=False, server_default="system"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["publication_job_id"], ["publication_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pub_events_job_type", "publication_events", ["publication_job_id", "event_type"])

    # ── 7. media_plans ─────────────────────────────────────────────────
    op.create_table(
        "media_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=False),
        sa.Column("placement", sa.String(length=64), nullable=False, server_default="featured"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("source_strategy", sa.String(length=64), nullable=False, server_default="AI_GENERATED"),
        sa.Column("generation_prompt", sa.Text(), nullable=True),
        sa.Column("preferred_aspect_ratio", sa.String(length=32), nullable=False, server_default="16:9"),
        sa.Column("target_width", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("target_height", sa.Integer(), nullable=False, server_default="675"),
        sa.Column("alt_text_plan", sa.Text(), nullable=True),
        sa.Column("caption_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rights_requirement", sa.String(length=64), nullable=False, server_default="COMMERCIAL_ALLOWED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_plan_job_asset", "media_plans", ["publication_job_id", "asset_type"])

    # ── 8. media_assets ────────────────────────────────────────────────
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("media_plan_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("origin_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("creator", sa.String(length=255), nullable=True),
        sa.Column("license_type", sa.String(length=64), nullable=False, server_default="PROPRIETARY_AI"),
        sa.Column("license_url", sa.String(length=2048), nullable=True),
        sa.Column("attribution_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attribution_text", sa.Text(), nullable=True),
        sa.Column("commercial_use_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("modification_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rights_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rights_notes", sa.Text(), nullable=True),
        sa.Column("local_storage_path", sa.String(length=1024), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("perceptual_hash", sa.String(length=64), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=False, server_default="image/webp"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="675"),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alt_text", sa.String(length=512), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("provenance_metadata", sa.JSON(), nullable=True),
        sa.Column("wordpress_media_id", sa.Integer(), nullable=True),
        sa.Column("wordpress_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["media_plan_id"], ["media_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("media_plan_id"),
    )
    op.create_index("ix_media_asset_hash", "media_assets", ["content_hash"])
    op.create_index("ix_media_asset_wp_id", "media_assets", ["wordpress_media_id"])

    # ── 9. seo_publication_packages ────────────────────────────────────
    op.create_table(
        "seo_publication_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("meta_title", sa.String(length=512), nullable=False),
        sa.Column("meta_description", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("primary_topic", sa.String(length=255), nullable=True),
        sa.Column("primary_keyword", sa.String(length=255), nullable=True),
        sa.Column("robots_directive", sa.String(length=64), nullable=False, server_default="index,follow"),
        sa.Column("schema_types", sa.JSON(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=True),
        sa.Column("open_graph_title", sa.String(length=512), nullable=True),
        sa.Column("open_graph_description", sa.Text(), nullable=True),
        sa.Column("open_graph_image_url", sa.String(length=2048), nullable=True),
        sa.Column("twitter_title", sa.String(length=512), nullable=True),
        sa.Column("twitter_description", sa.Text(), nullable=True),
        sa.Column("twitter_image_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_job_id"),
    )
    op.create_index("ix_seo_pkg_slug", "seo_publication_packages", ["site_id", "slug"])

    # ── 10. publication_approvals ──────────────────────────────────────
    op.create_table(
        "publication_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["publication_job_id"], ["publication_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pub_approval_job", "publication_approvals", ["publication_job_id"])

    # ── 11. published_articles ─────────────────────────────────────────
    op.create_table(
        "published_articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("article_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("draft_version_id", sa.Uuid(), nullable=False),
        sa.Column("audit_id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("wordpress_post_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("slug", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("featured_media_id", sa.Integer(), nullable=True),
        sa.Column("category_ids", sa.JSON(), nullable=False),
        sa.Column("tag_ids", sa.JSON(), nullable=False),
        sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="VERIFIED"),
        sa.Column("verification_details_json", sa.JSON(), nullable=True),
        sa.Column("package_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audit_id"], ["audit_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_job_id"], ["publication_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_job_id"),
    )
    op.create_index("ix_pub_art_site_slug", "published_articles", ["site_id", "slug"])
    op.create_index("ix_pub_art_wp_id", "published_articles", ["site_id", "wordpress_post_id"], unique=True)

    # ── 12. indexing_jobs ──────────────────────────────────────────────
    op.create_table(
        "indexing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("publication_job_id", sa.Uuid(), nullable=False),
        sa.Column("published_article_id", sa.Uuid(), nullable=True),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("search_console_property", sa.String(length=512), nullable=True),
        sa.Column("first_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sitemap_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["publication_job_id"], ["publication_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["published_article_id"], ["published_articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indexing_job_site_status", "indexing_jobs", ["site_id", "status"])

    # ── 13. site_health ────────────────────────────────────────────────
    op.create_table(
        "site_health",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("api_status", sa.String(length=32), nullable=False, server_default="HEALTHY"),
        sa.Column("auth_status", sa.String(length=32), nullable=False, server_default="VALID"),
        sa.Column("media_status", sa.String(length=32), nullable=False, server_default="HEALTHY"),
        sa.Column("last_success", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("circuit_state", sa.String(length=32), nullable=False, server_default="CLOSED"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id"),
    )

    # ── 14. orphan_media_records ───────────────────────────────────────
    op.create_table(
        "orphan_media_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("wordpress_media_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING_CLEANUP"),
        sa.Column("cleaned_up", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("orphan_media_records")
    op.drop_table("site_health")
    op.drop_table("indexing_jobs")
    op.drop_table("published_articles")
    op.drop_table("publication_approvals")
    op.drop_table("seo_publication_packages")
    op.drop_table("media_assets")
    op.drop_table("media_plans")
    op.drop_table("publication_events")
    op.drop_table("publication_schedules")
    op.drop_table("publication_jobs")
    op.drop_table("visual_brand_profiles")
    op.drop_table("publication_authorizations")

    with op.batch_alter_table("sites") as batch_op:
        batch_op.drop_column("risk_policy_id")
        batch_op.drop_column("media_policy_id")
        batch_op.drop_column("seo_profile_id")
        batch_op.drop_column("brand_profile_id")
        batch_op.drop_column("publication_windows")
        batch_op.drop_column("minimum_publish_interval_minutes")
        batch_op.drop_column("max_posts_per_day")
        batch_op.drop_column("indexing_enabled")
        batch_op.drop_column("schema_enabled")
        batch_op.drop_column("internal_linking_enabled")
        batch_op.drop_column("media_enabled")
        batch_op.drop_column("autonomous_publishing_enabled")
        batch_op.drop_column("publishing_enabled")
        batch_op.drop_column("default_post_status")
        batch_op.drop_column("default_category_id")
        batch_op.drop_column("default_author_id")
        batch_op.drop_column("timezone")
        batch_op.drop_column("credential_ref")
        batch_op.drop_column("wordpress_api_url")
        batch_op.drop_column("wordpress_base_url")
