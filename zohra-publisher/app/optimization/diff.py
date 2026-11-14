"""
Zohra — Part 9 Content Diff Engine.

Implements Sections 20, 21, 22 of Part 9 Master Prompt:
- Generates structural, granular, and auditable diffs between ContentSnapshots
- Tracks titles, meta descriptions, headings, body text paragraphs, links, media, and schema
- Classifies whether a change includes factual modifications requiring verification
"""

from __future__ import annotations

import difflib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.db.models.optimization import ContentSnapshot


@dataclass
class StructuredDiff:
    """Auditable diff between two states of an article."""

    title_changed: bool
    old_title: str
    new_title: str

    meta_title_changed: bool
    old_meta_title: str | None
    new_meta_title: str | None

    meta_description_changed: bool
    old_meta_description: str | None
    new_meta_description: str | None

    headings_added: list[str] = field(default_factory=list)
    headings_removed: list[str] = field(default_factory=list)
    headings_modified: list[dict[str, str]] = field(default_factory=list)

    paragraphs_added: list[str] = field(default_factory=list)
    paragraphs_removed: list[str] = field(default_factory=list)

    internal_links_added: list[dict[str, Any]] = field(default_factory=list)
    internal_links_removed: list[dict[str, Any]] = field(default_factory=list)

    schema_changed: bool = False
    media_changed: bool = False

    word_count_before: int = 0
    word_count_after: int = 0
    word_count_diff: int = 0

    is_factual_change: bool = False
    text_unified_diff: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ContentDiffEngine:
    """Computes exact, transparent diffs between article content versions."""

    @classmethod
    def compute_diff(
        cls,
        before: ContentSnapshot | dict[str, Any],
        after: ContentSnapshot | dict[str, Any],
    ) -> StructuredDiff:
        """
        Compares two content states and returns a StructuredDiff.
        """
        b_dict = before if isinstance(before, dict) else cls._snapshot_to_dict(before)
        a_dict = after if isinstance(after, dict) else cls._snapshot_to_dict(after)

        # 1. Title Diff
        old_title = str(b_dict.get("title", ""))
        new_title = str(a_dict.get("title", ""))
        title_changed = old_title != new_title

        # 2. Meta Title Diff
        old_meta_title = b_dict.get("meta_title")
        new_meta_title = a_dict.get("meta_title")
        meta_title_changed = old_meta_title != new_meta_title

        # 3. Meta Description Diff
        old_meta_desc = b_dict.get("meta_description")
        new_meta_desc = a_dict.get("meta_description")
        meta_desc_changed = old_meta_desc != new_meta_desc

        # 4. Heading Diff
        b_headings = [str(h) for h in b_dict.get("headings_json", [])]
        a_headings = [str(h) for h in a_dict.get("headings_json", [])]
        headings_added = [h for h in a_headings if h not in b_headings]
        headings_removed = [h for h in b_headings if h not in a_headings]

        # 5. Body Text & Paragraph Diffs
        b_body = str(b_dict.get("article_body", ""))
        a_body = str(a_dict.get("article_body", ""))

        b_paragraphs = [p.strip() for p in b_body.split("\n\n") if p.strip()]
        a_paragraphs = [p.strip() for p in a_body.split("\n\n") if p.strip()]

        paragraphs_added = [p for p in a_paragraphs if p not in b_paragraphs]
        paragraphs_removed = [p for p in b_paragraphs if p not in a_paragraphs]

        # Word counts
        b_words = len(re.findall(r"\w+", b_body))
        a_words = len(re.findall(r"\w+", a_body))
        word_count_diff = a_words - b_words

        # Unified text diff
        unified_diff_lines = list(
            difflib.unified_diff(
                b_body.splitlines(keepends=True),
                a_body.splitlines(keepends=True),
                fromfile="before",
                tofile="after",
                n=3,
            )
        )
        text_unified_diff = "".join(unified_diff_lines)

        # 6. Internal Links Diff
        b_links = b_dict.get("internal_links_json", [])
        a_links = a_dict.get("internal_links_json", [])
        b_link_urls = {str(l.get("url") if isinstance(l, dict) else l) for l in b_links}
        a_link_urls = {str(l.get("url") if isinstance(l, dict) else l) for l in a_links}

        links_added = [l for l in a_links if str(l.get("url") if isinstance(l, dict) else l) not in b_link_urls]
        links_removed = [l for l in b_links if str(l.get("url") if isinstance(l, dict) else l) not in a_link_urls]

        # 7. Schema & Media Diffs
        schema_changed = b_dict.get("schema_json") != a_dict.get("schema_json")
        media_changed = b_dict.get("featured_image_json") != a_dict.get("featured_image_json")

        # 8. Factual Change Detection
        # A change is considered factual if substantial paragraph additions/deletions occurred
        # or if word count shifts significantly (> 50 words change), rather than purely title/meta/formatting.
        is_factual = bool(
            len(paragraphs_added) > 0
            or len(paragraphs_removed) > 0
            or abs(word_count_diff) > 40
            or len(headings_added) > 0
        )

        return StructuredDiff(
            title_changed=title_changed,
            old_title=old_title,
            new_title=new_title,
            meta_title_changed=meta_title_changed,
            old_meta_title=old_meta_title,
            new_meta_title=new_meta_title,
            meta_description_changed=meta_desc_changed,
            old_meta_description=old_meta_desc,
            new_meta_description=new_meta_desc,
            headings_added=headings_added,
            headings_removed=headings_removed,
            paragraphs_added=paragraphs_added,
            paragraphs_removed=paragraphs_removed,
            internal_links_added=links_added,
            internal_links_removed=links_removed,
            schema_changed=schema_changed,
            media_changed=media_changed,
            word_count_before=b_words,
            word_count_after=a_words,
            word_count_diff=word_count_diff,
            is_factual_change=is_factual,
            text_unified_diff=text_unified_diff,
        )

    @classmethod
    def _snapshot_to_dict(cls, snapshot: ContentSnapshot) -> dict[str, Any]:
        return {
            "title": snapshot.title,
            "meta_title": snapshot.meta_title,
            "meta_description": snapshot.meta_description,
            "article_body": snapshot.article_body,
            "headings_json": snapshot.headings_json or [],
            "internal_links_json": snapshot.internal_links_json or [],
            "external_links_json": snapshot.external_links_json or [],
            "schema_json": snapshot.schema_json or {},
            "featured_image_json": snapshot.featured_image_json or {},
        }
