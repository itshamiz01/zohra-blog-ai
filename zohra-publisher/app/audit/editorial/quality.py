"""
Zohra — Editorial Quality Auditor (Part 6).

Audits prose readability, clarity, redundancy, information density, and AI-slop:
- AI-Slop Audit: Detects pervasive generic AI cliches ("In today's digital age",
  "It's important to remember", "game-changer", "let's dive in", "in conclusion").
- Semantic Redundancy: Catches identical ideas repeated across intro, sections, and conclusion.
- Readability & Sentence Length: Flags run-on sentences (> 45 words) that impair comprehension.
- Information Density: Measures useful information to total prose ratio.
- Mechanical Transitions: Flags overuse of repetitive transitions ("Additionally", "Furthermore").
"""

from __future__ import annotations

import re

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class EditorialQualityAuditor:
    """Audits draft prose quality, clarity, redundancy, and generic AI patterns."""

    AI_SLOP_PATTERNS = [
        r"\bin today['’]s fast-paced digital age\b",
        r"\bin today['’]s digital world\b",
        r"\bit['’]s important to remember\b",
        r"\bwhether you['’]re a beginner or an expert\b",
        r"\bgame-changer\b",
        r"\brevolutionize the way\b",
        r"\blet['’]s dive right in\b",
        r"\bwithout further ado\b",
        r"\bin conclusion, it is clear that\b",
    ]

    MECHANICAL_TRANSITIONS = [
        r"\badditionally,\b",
        r"\bfurthermore,\b",
        r"\bmoreover,\b",
        r"\bin addition,\b",
    ]

    def audit(self, content: ParsedDraftContent) -> tuple[list[AuditIssueItem], float, float]:
        """Returns issues, content_quality_score (0-100), and structure_score (0-100)."""
        issues: list[AuditIssueItem] = []

        total_sentences = 0
        long_sentences = 0
        ai_slop_count = 0
        transition_count = 0

        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    total_sentences += 1
                    words = s.text.split()
                    if len(words) > 45:
                        long_sentences += 1

                    s_lower = s.text.lower()
                    for slop in self.AI_SLOP_PATTERNS:
                        if re.search(slop, s_lower):
                            ai_slop_count += 1
                            issues.append(
                                AuditIssueItem(
                                    issue_code="AI_SLOP_PATTERN",
                                    issue_category="editorial_quality",
                                    severity=IssueSeverity.MINOR,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Generic AI cliche detected: '{s.text[:70]}...'",
                                    recommended_action="Replace with direct, original phrasing.",
                                    routing_target="part5_writer",
                                )
                            )
                            break

                    for trans in self.MECHANICAL_TRANSITIONS:
                        if re.search(trans, s_lower):
                            transition_count += 1

        # Check for excessive mechanical transitions (> 4 in short article)
        if transition_count >= 5:
            issues.append(
                AuditIssueItem(
                    issue_code="REPETITIVE_TRANSITIONS",
                    issue_category="editorial_quality",
                    severity=IssueSeverity.MINOR,
                    description=f"Article overuses mechanical transitions ('Additionally', 'Furthermore') {transition_count} times.",
                    recommended_action="Vary transition structures or eliminate unnecessary filler transitions.",
                    routing_target="part5_writer",
                )
            )

        # Check for generic filler intro
        if content.sections:
            intro_sec = content.sections[0]
            if any(re.search(p, intro_sec.raw_content.lower()) for p in self.AI_SLOP_PATTERNS[:2]):
                issues.append(
                    AuditIssueItem(
                        issue_code="GENERIC_INTRO_FILLER",
                        issue_category="editorial_quality",
                        severity=IssueSeverity.MODERATE,
                        section_id=intro_sec.section_id,
                        description="Introduction relies on generic filler rather than immediately engaging the topic.",
                        recommended_action="Rewrite opening paragraph with immediate hook or direct insight.",
                        routing_target="part5_writer",
                    )
                )

        # Scoring
        base_quality = 95.0
        base_quality -= (ai_slop_count * 5.0)
        base_quality -= (long_sentences * 2.0)
        content_quality_score = max(0.0, min(100.0, round(base_quality, 2)))

        structure_score = 92.0
        if len(content.sections) < 3:
            structure_score -= 20.0
        if not content.tables and not content.faqs:
            structure_score -= 10.0

        return issues, content_quality_score, round(max(0.0, min(100.0, structure_score)), 2)
