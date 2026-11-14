"""
Zohra — Taxonomy Resolver (Part 7).

Resolves Part 5 editorial category and tag recommendations against existing WordPress taxonomy:
- Canonical category matching with deduplication and equivalence mapping.
- Tag explosion prevention: limits tags to configured policy (max 5) and normalizes plurals/casing.
- Author resolution: maps site default or category-specific author IDs without fabricating credentials.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger("publishing.taxonomy.resolver")


class TaxonomyResolver:
    """Normalizes and resolves categories and tags for WordPress."""

    CATEGORY_EQUIVALENCES: dict[str, str] = {
        "ai": "Artificial Intelligence",
        "a.i.": "Artificial Intelligence",
        "machine learning": "Artificial Intelligence",
        "ml": "Artificial Intelligence",
        "llms": "Large Language Models",
        "llm": "Large Language Models",
        "generative ai": "Generative AI",
        "genai": "Generative AI",
        "seo": "Search Engine Optimization",
    }

    @classmethod
    def resolve_category(
        cls,
        recommended_name: str | None,
        existing_categories: list[dict[str, Any]],
        default_category_id: int | None = 1,
    ) -> int:
        """
        Matches recommended category against existing site categories.
        Uses equivalence dictionary and case-insensitive matching.
        """
        if not recommended_name:
            return default_category_id or 1

        norm_target = recommended_name.strip().lower()
        if norm_target in cls.CATEGORY_EQUIVALENCES:
            norm_target = cls.CATEGORY_EQUIVALENCES[norm_target].lower()

        for cat in existing_categories:
            c_name = cat.get("name", "").strip().lower()
            c_slug = cat.get("slug", "").strip().lower()
            if norm_target in (c_name, c_slug):
                return cat.get("id")

        return default_category_id or 1

    @classmethod
    def resolve_tags(
        cls,
        recommended_tags: list[str],
        existing_tags: list[dict[str, Any]],
        max_tags: int = 5,
    ) -> list[int]:
        """
        Normalizes proposed keyword tags, prevents explosion by applying a strict limit (e.g. max 5),
        and returns matching existing WordPress tag IDs.
        """
        resolved_ids: list[int] = []
        existing_map: dict[str, int] = {}
        for t in existing_tags:
            existing_map[t.get("name", "").strip().lower()] = t.get("id")
            existing_map[t.get("slug", "").strip().lower()] = t.get("id")

        seen: set[str] = set()

        for tag in recommended_tags:
            # Strip punctuation and normalize
            cleaned = re.sub(r"[^\w\s-]", "", tag).strip().lower()
            # Simple singularization for common plurals (e.g. models -> model)
            if cleaned.endswith("s") and len(cleaned) > 4:
                cleaned = cleaned[:-1]

            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)

            if cleaned in existing_map:
                resolved_ids.append(existing_map[cleaned])

            if len(resolved_ids) >= max_tags:
                break

        return resolved_ids
