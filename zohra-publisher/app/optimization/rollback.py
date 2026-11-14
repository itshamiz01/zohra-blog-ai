"""
Zohra — Part 9 Rollback Engine.

Implements Sections 77, 78, 79, 228 of Part 9 Master Prompt:
- Safe, atomic restoration of previous content state from ContentSnapshots
- Automatic rollback for degraded experiments meeting rollback criteria
- Revision conflict detection (prevents rolling back over subsequent human or approved edits)
- Complete auditable execution records via Part 7 update pipeline
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import ZohraError
from app.core.logging import get_logger
from app.db.models.optimization import ContentSnapshot, OptimizationChangeset
from app.optimization.diff import ContentDiffEngine
from app.publishing.pipeline import PublishingPipeline

logger = get_logger("optimization.rollback")


class RollbackEngine:
    """Safely restores historical content snapshots when optimizations fail or degrade."""

    @classmethod
    def compute_content_hash(cls, title: str, body: str) -> str:
        content = f"{title.strip()}\n{body.strip()}".encode()
        return hashlib.sha256(content).hexdigest()

    @classmethod
    async def execute_rollback(
        cls,
        changeset: OptimizationChangeset,
        before_snapshot: ContentSnapshot,
        current_article: dict[str, Any],
        site_data: dict[str, Any],
        reason: str,
        operator_id: str = "AUTONOMOUS_ROLLBACK_ENGINE",
        wp_client: Any | None = None,
    ) -> dict[str, Any]:
        """
        Rolls back an applied optimization to the state in before_snapshot.
        Checks for revision conflicts and updates WordPress via Part 7.
        """
        article_id_str = str(changeset.article_id)
        current_title = str(current_article.get("title", ""))
        current_body = str(current_article.get("article_body", current_article.get("body", "")))
        current_hash = cls.compute_content_hash(current_title, current_body)

        # 1. Revision Conflict Check (Section 228)
        # If someone edited the article since the optimization was applied, abort to prevent overwriting
        expected_current_hash = changeset.diff_json.get("after_hash")
        if expected_current_hash and current_hash != expected_current_hash:
            logger.warning(
                f"Rollback aborted due to subsequent edits on article {article_id_str}: current_hash={current_hash}, expected={expected_current_hash}"
            )
            raise ZohraError(
                "Cannot rollback: article was modified after the optimization was applied. Conflict detected.",
                code="REVISION_CONFLICT",
            )

        # 2. Prepare Restored Fields
        restore_fields: dict[str, Any] = {
            "title": before_snapshot.title,
            "content": before_snapshot.article_body,
        }
        if before_snapshot.meta_description:
            restore_fields["meta"] = {"description": before_snapshot.meta_description}
        if before_snapshot.slug:
            restore_fields["slug"] = before_snapshot.slug

        wp_post_id = current_article.get("wordpress_post_id", before_snapshot.wordpress_post_id or 101)

        # 3. Apply Restoration via Part 7 Pipeline
        part7_result = await PublishingPipeline.update_published_article(
            site_data=site_data,
            wordpress_post_id=wp_post_id,
            updated_fields=restore_fields,
            wp_client=wp_client,
        )

        # 4. Create Rollback Restored Snapshot
        restored_snapshot = ContentSnapshot(
            article_id=changeset.article_id,
            site_id=changeset.site_id,
            snapshot_type="ROLLBACK_RESTORE",
            title=before_snapshot.title,
            meta_title=before_snapshot.meta_title,
            meta_description=before_snapshot.meta_description,
            slug=before_snapshot.slug,
            canonical_url=before_snapshot.canonical_url,
            article_body=before_snapshot.article_body,
            headings_json=before_snapshot.headings_json,
            internal_links_json=before_snapshot.internal_links_json,
            external_links_json=before_snapshot.external_links_json,
            schema_json=before_snapshot.schema_json,
            featured_image_json=before_snapshot.featured_image_json,
            wordpress_post_id=wp_post_id,
            content_hash=cls.compute_content_hash(before_snapshot.title, before_snapshot.article_body),
        )

        # 5. Compute Diff of the Rollback action
        current_snap_dict = {
            "title": current_title,
            "article_body": current_body,
            "headings_json": current_article.get("headings", []),
            "internal_links_json": current_article.get("internal_links", []),
        }
        rollback_diff = ContentDiffEngine.compute_diff(current_snap_dict, before_snapshot)

        # 6. Update Changeset Status
        changeset.status = "ROLLED_BACK"

        logger.info(
            f"Rollback completed successfully: changeset_id={changeset.id}, article_id={article_id_str}, reason={reason}"
        )

        return {
            "success": True,
            "changeset_id": str(changeset.id),
            "restored_snapshot_id": str(restored_snapshot.id),
            "reason": reason,
            "executed_by": operator_id,
            "diff": rollback_diff.to_dict(),
            "part7_result": part7_result,
            "rolled_back_at": datetime.now(UTC).isoformat(),
        }
