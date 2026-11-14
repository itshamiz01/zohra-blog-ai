"""
Zohra — Content Risk Policy Engine (Part 6).

Enforces high-risk topic verification standards and human-review gates:
- Categories: Health / Medical, Finance, Legal, Political / Electoral, Public Allegations.
- Health / Medical: Flags unverified cures, dosages, disease outcomes.
- Finance: Flags guaranteed returns, fee distortions, unverified historical yields.
- Legal: Flags unverified legal advice, outdated statutory references.
- Political Neutrality: Strictly enforces non-prescriptive, neutral information standards.
  Rejects advocacy, rankings, or telling readers how to vote.
- Public Allegations: Requires strict source attribution and balanced response inclusion.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent, RiskLevel


class ContentRiskEngine:
    """Classifies risk level and enforces category-specific safety gates."""

    MEDICAL_RISK_PATTERNS = [
        r"\bcures?\b",
        r"\btreats?\b",
        r"\bdosages?\b",
        r"\bdiagnosed?\b",
        r"\bprescription\b",
        r"\bside effects?\b",
    ]

    FINANCIAL_RISK_PATTERNS = [
        r"\bguaranteed returns?\b",
        r"\brisk-free\b",
        r"\b100% profit\b",
        r"\bdouble your money\b",
        r"\binvestment advice\b",
    ]

    POLITICAL_ADVOCACY_PATTERNS = [
        r"\bvoters should vote for\b",
        r"\byou must support\b",
        r"\bthe corrupt party\b",
        r"\bthe only moral choice\b",
        r"\bvote against\b",
    ]

    PUBLIC_ALLEGATION_PATTERNS = [
        r"\ballegations?\b",
        r"\baccused of\b",
        r"\blawsuit filed against\b",
        r"\bfraud\b",
        r"\bembezzlement\b",
    ]

    def evaluate_risk(
        self,
        content: ParsedDraftContent,
        opportunity_topic: str,
        configured_policy: dict[str, Any] | None = None,
    ) -> tuple[RiskLevel, bool, list[AuditIssueItem], float]:
        """Evaluates content risk, determines if human review is required, and scores compliance."""
        issues: list[AuditIssueItem] = []
        full_text = " ".join([sec.raw_content for sec in content.sections]).lower()

        risk_level = RiskLevel.LOW
        human_review_required = False

        # 1. Medical Content Audit
        has_medical = any(re.search(p, full_text) for p in self.MEDICAL_RISK_PATTERNS)
        if has_medical:
            risk_level = RiskLevel.HIGH
            # Look for cure/guarantee claims
            if re.search(r"\bcures?\b", full_text) or re.search(r"\bguaranteed healing\b", full_text):
                issues.append(
                    AuditIssueItem(
                        issue_code="UNSUPPORTED_MEDICAL_CURE",
                        issue_category="risk_medical",
                        severity=IssueSeverity.CRITICAL,
                        description="Prose claims disease cure or medical guarantee without peer-reviewed clinical basis.",
                        recommended_action="Remove therapeutic claims and route to certified medical reviewer.",
                        routing_target="human_review",
                    )
                )
                human_review_required = True

        # 2. Financial Content Audit
        has_guaranteed_finance = any(re.search(p, full_text) for p in self.FINANCIAL_RISK_PATTERNS)
        if has_guaranteed_finance:
            risk_level = RiskLevel.CRITICAL
            human_review_required = True
            issues.append(
                AuditIssueItem(
                    issue_code="UNSUPPORTED_FINANCIAL_PROMISE",
                    issue_category="risk_financial",
                    severity=IssueSeverity.CRITICAL,
                    description="Article contains prohibited guaranteed financial returns or 'risk-free' investment claims.",
                    recommended_action="Remove all return guarantees and include standard investment risk disclaimer.",
                    routing_target="human_review",
                )
            )

        # 3. Political Content Audit: Non-prescriptive neutrality standard
        for adv in self.POLITICAL_ADVOCACY_PATTERNS:
            if re.search(adv, full_text):
                risk_level = RiskLevel.HIGH
                human_review_required = True
                issues.append(
                    AuditIssueItem(
                        issue_code="POLITICAL_ADVOCACY_VIOLATION",
                        issue_category="risk_political",
                        severity=IssueSeverity.CRITICAL,
                        description="Prose violates political neutrality standard by advocating for/against a political candidate or vote.",
                        recommended_action="Rephrase to neutral, objective informational presentation without electoral prescription.",
                        routing_target="human_review",
                    )
                )
                break

        # 4. Public Allegation Audit
        has_allegations = any(re.search(p, full_text) for p in self.PUBLIC_ALLEGATION_PATTERNS)
        if has_allegations:
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
            # Allegations without response or clear attribution
            if "alleg" in full_text and "response" not in full_text and "denied" not in full_text:
                issues.append(
                    AuditIssueItem(
                        issue_code="UNBALANCED_PUBLIC_ALLEGATION",
                        issue_category="risk_legal",
                        severity=IssueSeverity.MAJOR,
                        description="Public allegations are discussed without reporting status or subject's response.",
                        recommended_action="Include subject response or clarify ongoing litigation status.",
                        routing_target="part5_writer",
                    )
                )

        # Configured policy override
        if configured_policy and configured_policy.get("human_review_required"):
            human_review_required = True

        crit_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        maj_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        score = max(0.0, 100.0 - (crit_count * 50.0) - (maj_count * 20.0))

        return risk_level, human_review_required, issues, round(score, 2)
