"""
Zohra — Temporal & Freshness Validator (Part 6).

Audits the draft for temporal validity and information freshness:
- Deadline Check: Enforces revalidate_after deadlines from Part 4 / Part 5.
- Stale Source Detection: Checks if newer evidence supersedes older documents.
- Historical vs Current Confusion: Detects former leadership or launch prices asserted as current.
- Relative Date Language: Flags unstable relative terms like "today", "yesterday", "this week"
  when an evergreen or concrete date is required.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class TemporalFreshnessValidator:
    """Validates temporal accuracy and source freshness."""

    RELATIVE_DATE_TERMS = [
        r"\btoday\b",
        r"\byesterday\b",
        r"\bthis week\b",
        r"\blast week\b",
        r"\bthis month\b",
        r"\bright now\b",
    ]

    def validate(
        self,
        content: ParsedDraftContent,
        research_package_json: dict[str, Any],
        revalidate_after: str | datetime | None = None,
    ) -> tuple[list[AuditIssueItem], float]:
        """Audits draft for expired deadlines, stale facts, and unstable relative dates."""
        issues: list[AuditIssueItem] = []

        now = datetime.now(UTC)

        # 1. Enforce Revalidation Deadline
        if revalidate_after:
            if isinstance(revalidate_after, str):
                try:
                    reval_dt = datetime.fromisoformat(revalidate_after.replace("Z", "+00:00"))
                except ValueError:
                    reval_dt = None
            else:
                reval_dt = revalidate_after

            if reval_dt:
                # If naive, make timezone-aware
                if reval_dt.tzinfo is None:
                    reval_dt = reval_dt.replace(tzinfo=UTC)

                if now > reval_dt:
                    issues.append(
                        AuditIssueItem(
                            issue_code="RESEARCH_DEADLINE_EXPIRED",
                            issue_category="temporal",
                            severity=IssueSeverity.MAJOR,
                            description=f"Draft revalidation deadline ({reval_dt.isoformat()}) has expired. Fresh research is required.",
                            recommended_action="Route to Part 4 for targeted freshness re-check.",
                            routing_target="part4_research",
                        )
                    )

        # 2. Check for outdated historical facts (e.g. CEO changes or historical prices)
        timeline = research_package_json.get("timeline_json") or []
        verified_facts = research_package_json.get("verified_facts_json") or []
        stale_timeline_entities = {t.get("entity", "").lower() for t in timeline if t.get("superseded")}

        for fact in verified_facts:
            if fact.get("is_stale") or fact.get("superseded_by"):
                stale_subject = fact.get("subject", "").lower()
                for sec in content.sections:
                    for p in sec.paragraphs:
                        for s in p.sentences:
                            s_low = s.text.lower()
                            if (stale_subject and stale_subject in s_low) or any(ste in s_low for ste in stale_timeline_entities):
                                issues.append(
                                    AuditIssueItem(
                                        issue_code="FACT_OUTDATED",
                                        issue_category="temporal",
                                        severity=IssueSeverity.MAJOR,
                                        section_id=sec.section_id,
                                        sentence_index=s.sentence_index,
                                        description=f"Statement references superseded/stale information regarding '{stale_subject}'.",
                                        recommended_action="Update to the latest verified fact from timeline.",
                                        routing_target="part5_writer",
                                    )
                                )

        # 3. Relative Date Audit
        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    s_lower = s.text.lower()
                    for term in self.RELATIVE_DATE_TERMS:
                        if re.search(term, s_lower):
                            issues.append(
                                AuditIssueItem(
                                    issue_code="UNSTABLE_RELATIVE_DATE",
                                    issue_category="temporal",
                                    severity=IssueSeverity.MINOR,
                                    section_id=sec.section_id,
                                    sentence_index=s.sentence_index,
                                    description=f"Sentence uses unstable temporal term '{term}' which ages quickly.",
                                    recommended_action="Replace with explicit date or month/year.",
                                    routing_target="part5_writer",
                                )
                            )

        maj_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        min_count = sum(1 for i in issues if i.severity == IssueSeverity.MINOR)
        score = max(0.0, 100.0 - (maj_count * 20.0) - (min_count * 5.0))
        return issues, round(score, 2)
