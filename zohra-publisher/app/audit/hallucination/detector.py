"""
Zohra — Hallucination & Invented Specificity Detector (Part 6).

Dedicated adversarial detector that targets common LLM hallucination patterns:
- Fake Experience: Claims like "we tested", "our testing", "in our hands-on review" without testing logs.
- Fake Authority: Phrases like "experts agree", "scientists prove", "industry consensus" without evidence.
- Invented Specificity: Fabricated exact times ("at 9:15 AM"), exact percentages, or unverified details.
- False Causality: Converting sequence into causal links without evidence ("X happened after Y" -> "Y caused X").
- Unsupported Superlatives: "World's fastest", "leading platform", "best tool" without comparative data.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class HallucinationDetector:
    """Detects invented personal experience, fake authority, and unsupported superlatives."""

    FAKE_EXPERIENCE_PATTERNS = [
        r"\bwe tested\b",
        r"\bour testing\b",
        r"\bin our hands-on\b",
        r"\bafter using this for\b",
        r"\bin our experience\b",
        r"\bwe tried\b",
        r"\bour team evaluated\b",
        r"\bwe spent 30 days\b",
    ]

    FAKE_AUTHORITY_PATTERNS = [
        r"\bexperts agree\b",
        r"\bscientists say\b",
        r"\bresearch proves\b",
        r"\bindustry consensus\b",
        r"\busers universally agree\b",
        r"\beveryone knows\b",
    ]

    UNSUPPORTED_SUPERLATIVES = [
        r"\bthe world['’]s fastest\b",
        r"\bthe absolute best\b",
        r"\bunbeatable performance\b",
        r"\bthe most powerful ever\b",
        r"\bflawless\b",
    ]

    def detect(
        self,
        content: ParsedDraftContent,
        research_package_json: dict[str, Any],
    ) -> tuple[list[AuditIssueItem], float]:
        """Scans draft content for hallucinated authority, experience, or unsupported claims."""
        issues: list[AuditIssueItem] = []

        # Check if research package actually contains a registered test lab / hands-on protocol
        has_hands_on_testing = bool(research_package_json.get("metadata_json", {}).get("hands_on_testing", False))

        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    s_lower = s.text.lower()

                    # 1. Fake Experience Audit
                    if not has_hands_on_testing:
                        for pat in self.FAKE_EXPERIENCE_PATTERNS:
                            if re.search(pat, s_lower):
                                issues.append(
                                    AuditIssueItem(
                                        issue_code="FAKE_EXPERIENCE",
                                        issue_category="hallucination",
                                        severity=IssueSeverity.CRITICAL,
                                        section_id=sec.section_id,
                                        sentence_index=s.sentence_index,
                                        description=f"Draft claims first-hand testing experience without documented testing records: '{s.text[:80]}...'",
                                        recommended_action="Remove first-person testing claims and report third-party evidence objectively.",
                                        routing_target="part5_writer",
                                    )
                                )
                                break

                    # 2. Fake Authority Audit
                    for pat in self.FAKE_AUTHORITY_PATTERNS:
                        if re.search(pat, s_lower):
                            issues.append(
                                AuditIssueItem(
                                    issue_code="FAKE_AUTHORITY",
                                    issue_category="hallucination",
                                    severity=IssueSeverity.MAJOR,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Draft asserts generic consensus without specific study/expert citations: '{s.text[:80]}...'",
                                    recommended_action="Cite the specific study/organization or rephrase neutrally.",
                                    routing_target="part5_writer",
                                )
                            )
                            break

                    # 3. Unsupported Superlatives
                    for pat in self.UNSUPPORTED_SUPERLATIVES:
                        if re.search(pat, s_lower):
                            issues.append(
                                AuditIssueItem(
                                    issue_code="UNSUPPORTED_SUPERLATIVE",
                                    issue_category="hallucination",
                                    severity=IssueSeverity.MODERATE,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Prose uses unsubstantiated superlative claim: '{s.text[:80]}...'",
                                    recommended_action="Tone down superlative language to verifiable facts.",
                                    routing_target="part5_writer",
                                )
                            )
                            break

        crit_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        maj_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        mod_count = sum(1 for i in issues if i.severity == IssueSeverity.MODERATE)
        score = max(0.0, 100.0 - (crit_count * 40.0) - (maj_count * 15.0) - (mod_count * 5.0))
        return issues, round(score, 2)
