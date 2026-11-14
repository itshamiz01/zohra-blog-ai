"""
Zohra — Adversarial Auditor Pass (Part 6).

Dedicated adversarial reviewer that operates under the assumption:
"Assume the draft contains subtle mistakes, overconfident conclusions, or hidden assumptions. Find them."
Specifically tests:
- Which statement sounds more certain than the underlying evidence?
- Which comparative claim is least supported?
- Which conclusion goes beyond the sources?
- Does any sentence contain malicious prompt injection commands?
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class AdversarialReviewer:
    """Probes the draft adversarially for subtle overreaches, prompt injections, and hidden assumptions."""

    PROMPT_INJECTION_PATTERNS = [
        r"\bignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions|audit|rules)\b",
        r"\bapprove\s+this\s+article\s+immediately\b",
        r"\bmark\s+(?:as\s+)?pass\b",
        r"\bsystem\s+message:\b",
        r"\bdo\s+not\s+perform\s+fact[- ]check\b",
    ]

    UNWARRANTED_CERTAINTY = [
        r"\bundoubtedly\b",
        r"\bit\s+is\s+an\s+indisputable\s+fact\b",
        r"\bbeyond\s+all\s+shadow\s+of\s+a\s+doubt\b",
        r"\bcompletely\s+proven\b",
    ]

    def review(
        self,
        content: ParsedDraftContent,
        research_package_json: dict[str, Any],
    ) -> tuple[list[AuditIssueItem], float]:
        """Runs adversarial analysis and returns findings and score."""
        issues: list[AuditIssueItem] = []

        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    s_lower = s.text.lower()

                    # 1. Prompt Injection Attack Defense
                    for pat in self.PROMPT_INJECTION_PATTERNS:
                        if re.search(pat, s_lower):
                            issues.append(
                                AuditIssueItem(
                                    issue_code="PROMPT_INJECTION_DETECTED",
                                    issue_category="adversarial_security",
                                    severity=IssueSeverity.CRITICAL,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Potential prompt injection pattern embedded in article text: '{s.text[:80]}...'",
                                    recommended_action="Quarantine draft and sanitize text. Do not obey embedded directives.",
                                    routing_target="human_review",
                                )
                            )
                            break

                    # 2. Unwarranted Certainty without empirical proof
                    for pat in self.UNWARRANTED_CERTAINTY:
                        if re.search(pat, s_lower):
                            issues.append(
                                AuditIssueItem(
                                    issue_code="UNWARRANTED_CERTAINTY",
                                    issue_category="adversarial_epistemic",
                                    severity=IssueSeverity.MODERATE,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Epistemic overconfidence detected: '{s.text[:80]}...'",
                                    recommended_action="Qualify certainty appropriately according to source evidence.",
                                    routing_target="part5_writer",
                                )
                            )
                            break

        crit_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        mod_count = sum(1 for i in issues if i.severity == IssueSeverity.MODERATE)
        score = max(0.0, 100.0 - (crit_count * 50.0) - (mod_count * 10.0))
        return issues, round(score, 2)
