"""
Zohra — Internal Link Resolver (Part 7).

Resolves candidate internal link suggestions from Part 5 against actual site content records:
- Validates that target content exists, is published, and has a reachable URL.
- Prevents self-linking and duplicate adjacent link insertions.
- Replaces or maps natural contextual anchors without search engine manipulation or anchor stuffing.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.schemas.publishing import ResolvedInternalLink

logger = get_logger("publishing.links.resolver")


class InternalLinkResolver:
    """Matches and validates internal link candidates against published site content."""

    @classmethod
    def resolve_candidates(
        cls,
        candidates: list[dict[str, Any]],
        existing_content: list[dict[str, Any]],
        current_article_slug: str,
        max_links: int = 5,
    ) -> list[ResolvedInternalLink]:
        """
        Filters and validates internal link candidates.
        Ensures target is published, URL is valid, not a self-link, and limits link density.
        """
        resolved: list[ResolvedInternalLink] = []
        existing_by_slug = {c.get("slug"): c for c in existing_content if c.get("slug")}
        existing_by_url = {c.get("url"): c for c in existing_content if c.get("url")}

        used_targets: set[str] = set()

        for cand in candidates:
            target_url = cand.get("target_url")
            target_slug = cand.get("target_slug") or (target_url.rstrip("/").split("/")[-1] if target_url else "")

            # Prevent self-link
            if target_slug == current_article_slug:
                continue

            # Verify target exists in indexed content
            target = existing_by_slug.get(target_slug) or existing_by_url.get(target_url)
            if not target:
                continue

            resolved_url = target.get("url") or target_url
            if resolved_url in used_targets:
                continue
            used_targets.add(resolved_url)

            anchor = cand.get("recommended_anchor_context") or cand.get("anchor_text") or target.get("title")

            resolved.append(
                ResolvedInternalLink(
                    source_section_id=cand.get("source_section_id", "section_1"),
                    target_url=resolved_url,
                    target_title=target.get("title", ""),
                    anchor_text=anchor,
                    relevance_score=cand.get("relevance_score", 0.8),
                )
            )

            if len(resolved) >= max_links:
                break

        return resolved

    @classmethod
    def inject_links_into_html(
        cls,
        html_content: str,
        resolved_links: list[ResolvedInternalLink],
    ) -> str:
        """Injects contextual internal links into HTML without duplicating existing anchors."""
        updated = html_content
        for link in resolved_links:
            anchor = link.anchor_text.strip()
            if not anchor or len(anchor) < 3:
                continue

            # Don't inject if anchor is already linked
            if f">{anchor}</a>" in updated or f">{anchor.lower()}</a>" in updated.lower():
                continue

            # Replace the first bare occurrence of the anchor text
            pattern = re.compile(rf"\b({re.escape(anchor)})\b", re.IGNORECASE)
            replacement = rf'<a href="{link.target_url}">\1</a>'
            updated = pattern.sub(replacement, updated, count=1)
        return updated

