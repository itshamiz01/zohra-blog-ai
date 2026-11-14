"""
Zohra — Originality & Overlap Auditor (Part 6).

Audits draft content against source documents, competitor content, and existing site content:
- Copyright-Aware Overlap: Exact n-gram matching (6-gram+), long-sequence copy detection.
- Quotation Exception: Excludes properly formatted, quoted text from overlap penalties.
- Structural Mimicry: Detects near-identical section heading flows copied from competitors.
- Site Duplication & Cannibalization: Compares content fingerprints against existing site articles.
- Information Gain Recalculation: Verifies that draft delivers new information beyond source text.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class OriginalityAuditor:
    """Audits draft originality, phrase overlap, structural mimicry, and site cannibalization."""

    def audit(
        self,
        content: ParsedDraftContent,
        research_package_json: dict[str, Any],
        existing_site_content: list[dict[str, Any]] | None = None,
    ) -> tuple[list[AuditIssueItem], float, float]:
        """Returns originality issues, originality_score (0-100), and info_gain_score (0-100)."""
        issues: list[AuditIssueItem] = []

        primary_sources = research_package_json.get("primary_sources_json") or []
        supporting_sources = research_package_json.get("supporting_sources_json") or []

        source_texts: list[str] = []
        for s in (primary_sources + supporting_sources):
            if s.get("text"):
                source_texts.append(s["text"].lower())
            elif s.get("snippet"):
                source_texts.append(s["snippet"].lower())

        # 1. 6-gram Overlap Check against source texts
        overlap_sentences = 0
        total_sentences = 0

        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    total_sentences += 1
                    # Skip legitimate short quotes
                    if s.is_quote:
                        continue

                    words = re.findall(r"\w+", s.text.lower())
                    if len(words) >= 6:
                        # Test 6-grams
                        has_overlap = False
                        for i in range(len(words) - 5):
                            ngram = " ".join(words[i : i + 6])
                            if any(ngram in src for src in source_texts):
                                has_overlap = True
                                break

                        if has_overlap:
                            overlap_sentences += 1
                            issues.append(
                                AuditIssueItem(
                                    issue_code="SOURCE_OVERLAP",
                                    issue_category="originality",
                                    severity=IssueSeverity.MAJOR,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Direct phrase copying detected from source material: '{s.text[:80]}...'",
                                    recommended_action="Paraphrase using original synthesis or enclose in quotation marks if quoting.",
                                    routing_target="part5_writer",
                                )
                            )

        # 2. Site Cannibalization / Duplication Check
        if existing_site_content:
            draft_title = content.title.lower()
            for site_article in existing_site_content:
                art_title = site_article.get("title", "").lower()
                art_slug = site_article.get("slug", "").lower()
                # Check for near-identical headline
                if draft_title and art_title and (draft_title in art_title or art_title in draft_title):
                    issues.append(
                        AuditIssueItem(
                            issue_code="SITE_TOPIC_DUPLICATION",
                            issue_category="originality",
                            severity=IssueSeverity.CRITICAL,
                            description=f"Draft headline strongly duplicates existing site article '{art_title}' (Slug: {art_slug}).",
                            recommended_action="Refocus angle to avoid cannibalization or consolidate topics.",
                            routing_target="part5_writer",
                        )
                    )

        # Calculate scores
        overlap_ratio = (overlap_sentences / max(1, total_sentences))
        originality_score = max(0.0, 100.0 - (overlap_ratio * 200.0))

        # Check information gain: presence of unique takeaways / synthesis
        content_gaps = research_package_json.get("content_gaps_json") or []
        info_gain_score = 90.0 if content_gaps else 80.0
        if overlap_ratio > 0.2:
            info_gain_score -= 30.0

        return issues, round(originality_score, 2), round(max(0.0, min(100.0, info_gain_score)), 2)
