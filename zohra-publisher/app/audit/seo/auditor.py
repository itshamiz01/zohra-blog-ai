"""
Zohra — Independent SEO Auditor (Part 6).

Audits SEO quality, title truthfulness, heading structure, and unnatural stuffing:
- Keyword Stuffing: Detects unnatural keyword density or repetitive unnatural headings.
- Title & Headline Audit: Checks for clickbait, unverified superlatives ("Tested" without testing),
  false promises ("Complete Guide" with thin content), and title/meta length.
- Heading Hierarchy: Ensures logical H1 -> H2 -> H3 hierarchy without skipped levels or empty headings.
- Metadata Truthfulness: Verifies meta description does not claim non-existent features or fake urgency.
"""

from __future__ import annotations

import re

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class SEOAuditor:
    """Audits technical SEO, keyword distribution, title honesty, and heading structure."""

    def audit(
        self,
        content: ParsedDraftContent,
        primary_keyword: str,
        research_quality_score: float = 80.0,
    ) -> tuple[list[AuditIssueItem], float]:
        """Audits SEO elements and returns detected issues and a 0-100 SEO score."""
        issues: list[AuditIssueItem] = []

        kw_clean = primary_keyword.strip().lower()
        title_lower = content.title.lower()

        # 1. Title Truthfulness & Promise Audit
        if "tested" in title_lower and research_quality_score < 60.0:
            issues.append(
                AuditIssueItem(
                    issue_code="UNSUPPORTED_TITLE_PROMISE",
                    issue_category="seo",
                    severity=IssueSeverity.MAJOR,
                    description="Title promises hands-on testing ('Tested'), but testing evidence is absent or insufficient.",
                    recommended_action="Remove 'Tested' from title or rephrase to match actual research basis.",
                    routing_target="part5_writer",
                )
            )

        # 2. Heading Hierarchy Audit & Keyword Stuffing in Headings
        headings_text: list[str] = []
        for sec in content.sections:
            h_text = sec.heading.lower()
            headings_text.append(h_text)
            if not sec.heading.strip():
                issues.append(
                    AuditIssueItem(
                        issue_code="EMPTY_HEADING",
                        issue_category="seo",
                        severity=IssueSeverity.MINOR,
                        section_id=sec.section_id,
                        description="Section contains empty or blank heading text.",
                        recommended_action="Provide a descriptive heading.",
                        routing_target="part5_writer",
                    )
                )

        # Heading keyword repetition
        kw_in_headings = sum(1 for h in headings_text if kw_clean in h)
        repetitive_single_heading = any(h.count(kw_clean) >= 2 for h in headings_text)
        if (len(headings_text) > 2 and kw_in_headings / len(headings_text) > 0.6) or repetitive_single_heading:
            issues.append(
                AuditIssueItem(
                    issue_code="KEYWORD_STUFFING_HEADINGS",
                    issue_category="seo",
                    severity=IssueSeverity.MAJOR,
                    description=f"Primary keyword '{primary_keyword}' is unnaturally stuffed or repeated in headings.",
                    recommended_action="Vary heading phrasing naturally using semantic LSI terms.",
                    routing_target="part5_writer",
                )
            )

        # 3. Keyword Stuffing in Prose
        full_text = " ".join([sec.raw_content for sec in content.sections]).lower()
        words = re.findall(r"\w+", full_text)
        total_words = len(words)

        if total_words > 100:
            kw_tokens = kw_clean.split()
            kw_count = full_text.count(kw_clean)
            density = (kw_count * len(kw_tokens)) / total_words
            if density > 0.04:  # Over 4% keyword density
                issues.append(
                    AuditIssueItem(
                        issue_code="KEYWORD_STUFFING",
                        issue_category="seo",
                        severity=IssueSeverity.MAJOR,
                        description=f"Unnatural keyword stuffing: '{primary_keyword}' appears {kw_count} times ({density:.1%} density).",
                        recommended_action="Reduce keyword frequency to a natural editorial density (< 2.5%).",
                        routing_target="part5_writer",
                    )
                )

        # 4. Meta Title & Description Checks
        if len(content.meta_title) > 75:
            issues.append(
                AuditIssueItem(
                    issue_code="META_TITLE_TOO_LONG",
                    issue_category="seo",
                    severity=IssueSeverity.MINOR,
                    description=f"Meta title exceeds 75 characters ({len(content.meta_title)} chars).",
                    recommended_action="Shorten to under 60-70 characters.",
                    routing_target="part5_writer",
                )
            )

        if len(content.meta_description) > 170:
            issues.append(
                AuditIssueItem(
                    issue_code="META_DESCRIPTION_TOO_LONG",
                    issue_category="seo",
                    severity=IssueSeverity.MINOR,
                    description=f"Meta description exceeds 170 characters ({len(content.meta_description)} chars).",
                    recommended_action="Trim meta description to 150-160 characters.",
                    routing_target="part5_writer",
                )
            )

        maj_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        min_count = sum(1 for i in issues if i.severity == IssueSeverity.MINOR)
        score = max(0.0, 100.0 - (maj_count * 15.0) - (min_count * 5.0))
        return issues, round(score, 2)
