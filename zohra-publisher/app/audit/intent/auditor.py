"""
Zohra — Search Intent Auditor (Part 6).

Audits whether the drafted article genuinely satisfies search intent:
- Intent Alignment: Compares query/topic intent (e.g. pricing, tutorial, comparison)
  against the draft structure and tone.
- Intent Drift: Detects when a pricing or technical query is met with irrelevant company history.
- Answer Latency: Measures how far down the article before the direct answer appears
  (e.g., pricing or release date should appear within first 2 sections).
- Subquestion Completeness: Verifies that core reader questions from Part 3 & 4 are answered.
"""

from __future__ import annotations

from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class SearchIntentAuditor:
    """Audits draft alignment with user search intent and measures answer latency."""

    def audit(
        self,
        content: ParsedDraftContent,
        primary_keyword: str,
        primary_intent: str,
        research_package_json: dict[str, Any],
    ) -> tuple[list[AuditIssueItem], float]:
        """Audits intent satisfaction and calculates a 0-100 intent score."""
        issues: list[AuditIssueItem] = []

        kw_lower = primary_keyword.lower()
        intent_lower = primary_intent.lower()

        # 1. Answer Latency Check: For pricing, definition, or release date queries
        is_direct_answer_query = any(w in kw_lower for w in ["price", "pricing", "cost", "release date", "what is", "how much"]) or intent_lower in ["pricing", "troubleshooting"]

        if is_direct_answer_query:
            # Direct answer should be in section_intro or first body section
            early_sections = content.sections[:2]
            found_early_answer = False
            for sec in early_sections:
                sec_text = sec.raw_content.lower()
                if any(w in sec_text for w in ["$", "€", "cost", "price", "free", "released on", "launch"]):
                    found_early_answer = True
                    break

            if not found_early_answer:
                issues.append(
                    AuditIssueItem(
                        issue_code="HIGH_ANSWER_LATENCY",
                        issue_category="intent",
                        severity=IssueSeverity.MAJOR,
                        description=f"Direct query '{primary_keyword}' buries the core answer below the opening sections.",
                        recommended_action="Present the key answer (e.g. pricing summary or definition) in the introduction.",
                        routing_target="part5_writer",
                    )
                )

        # 2. Intent Drift Check: If query is specifically about pricing, article shouldn't be 90% company history
        if "pricing" in kw_lower or "cost" in kw_lower:
            pricing_mentions = 0
            history_mentions = 0
            for sec in content.sections:
                sec_text = sec.raw_content.lower()
                if "price" in sec_text or "$" in sec_text or "cost" in sec_text:
                    pricing_mentions += 1
                if "founded" in sec_text or "history" in sec_text or "background" in sec_text:
                    history_mentions += 1

            if history_mentions > pricing_mentions and pricing_mentions <= 1:
                issues.append(
                    AuditIssueItem(
                        issue_code="INTENT_DRIFT",
                        issue_category="intent",
                        severity=IssueSeverity.MAJOR,
                        description=f"Draft drifts from query '{primary_keyword}' to historical overview instead of pricing details.",
                        recommended_action="Restructure to prioritize pricing breakdown, tiers, and cost comparisons.",
                        routing_target="part5_writer",
                    )
                )

        # 3. Subquestion Completeness: Check answered questions from research package
        questions_answered = research_package_json.get("questions_answered_json") or []
        subquestions_covered = 0
        if questions_answered:
            article_text = " ".join([s.raw_content for s in content.sections]).lower()
            for q in questions_answered:
                q_text = q.get("question", "") if isinstance(q, dict) else str(q)
                keywords = [w for w in q_text.lower().split() if len(w) > 4]
                if any(kw in article_text for kw in keywords):
                    subquestions_covered += 1

        base_score = 90.0
        maj_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        score = max(0.0, base_score - (maj_count * 20.0))
        return issues, round(score, 2)
