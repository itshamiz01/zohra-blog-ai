"""
Zohra — Internal Link Planner (Part 5).

Identifies contextual internal linking candidates based on site topic clusters
and existing content without exact-match anchor text spam.
Prepares internal link recommendations for Part 7 finalization.
"""

from __future__ import annotations

from typing import Any

from app.schemas.editorial import InternalLinkCandidateResponse


class InternalLinkPlanner:
    """Plans natural, context-rich internal linking opportunities."""

    @classmethod
    def identify_candidates(
        cls,
        sections_content: list[dict[str, str]],
        existing_site_content: list[dict[str, Any]] | None = None,
    ) -> list[InternalLinkCandidateResponse]:
        candidates: list[InternalLinkCandidateResponse] = []
        if not existing_site_content:
            return candidates

        for sec in sections_content:
            sec_id = sec.get("section_id", "sec_body")
            sec_text = sec.get("content", "").lower()

            for page in existing_site_content:
                title = page.get("title", "")
                slug = page.get("slug", "")
                url = page.get("url", f"/{slug}")
                target_id = page.get("id")

                # Check if page primary concept is mentioned in the section
                page_words = [w.lower() for w in title.split() if len(w) > 4 and w.lower() not in ("guide", "complete", "everything", "overview")]
                if page_words and any(w in sec_text for w in page_words):
                    candidates.append(
                        InternalLinkCandidateResponse(
                            source_section_id=sec_id,
                            target_content_id=str(target_id) if target_id else None,
                            target_url=url,
                            recommended_anchor_context=f"For broader background, see our guide on {title}",
                            relevance_score=85.0,
                            reason=f"Topical cluster connection to existing pillar resource '{title}'",
                        )
                    )

        return candidates
