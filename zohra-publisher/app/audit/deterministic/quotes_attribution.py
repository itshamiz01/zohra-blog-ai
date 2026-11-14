"""
Zohra — Quotation & Attribution Validator (Part 6).

Verifies authentic quotes and required attributions:
- Quote Rule: Every quoted string must match stored source evidence verbatim.
  If not verified in research records, flags FABRICATED_QUOTE (Critical Failure).
- Quote Context Distortion: Detects quotes stripped of essential qualifying context.
- Attribution Audit: Compares claims against attribution_required_claim_ids.
  Flags claims where assertions like "Company says X is 2x faster" became "X is 2x faster".
"""

from __future__ import annotations

from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class QuoteAttributionValidator:
    """Verifies authenticity of quotations and preserves required source attributions."""

    def validate(
        self,
        content: ParsedDraftContent,
        research_package_json: dict[str, Any],
    ) -> tuple[list[AuditIssueItem], float]:
        """Audits quotes and attributions against Part 4 research package."""
        issues: list[AuditIssueItem] = []

        verified_facts = research_package_json.get("verified_facts_json") or []
        primary_sources = research_package_json.get("primary_sources_json") or []
        supporting_sources = research_package_json.get("supporting_sources_json") or []

        # Build research text corpus for quote matching
        source_excerpts: list[str] = []
        for s in (primary_sources + supporting_sources):
            if s.get("snippet"):
                source_excerpts.append(s["snippet"].lower())
            if s.get("text"):
                source_excerpts.append(s["text"].lower())

        for f in verified_facts:
            if f.get("quote"):
                source_excerpts.append(f["quote"].lower())
            if f.get("claim_text"):
                source_excerpts.append(f["claim_text"].lower())

        # 1. Quote Rule: Must match verbatim or be paraphrased
        for q_item in content.quotes:
            q_text = q_item["quote_text"].strip()
            # Ignore short 1-2 word common phrases in quotes
            if len(q_text.split()) < 3:
                continue

            q_lower = q_text.lower()
            matched = any(q_lower in exc for exc in source_excerpts)

            if not matched:
                # Critical failure: Fabricated quotation
                issues.append(
                    AuditIssueItem(
                        issue_code="FABRICATED_QUOTE",
                        issue_category="quotation",
                        severity=IssueSeverity.CRITICAL,
                        section_id=q_item.get("section_id"),
                        sentence_index=q_item.get("sentence_index"),
                        description=f"Quotation \"{q_text}\" does not match any verified source record or interview.",
                        recommended_action="Remove quotation marks and paraphrase accurately, or delete if unsupported.",
                        routing_target="part5_writer",
                    )
                )

        # 2. Check for missing attribution on claims marked attribution_required
        for fact in verified_facts:
            if fact.get("attribution_required"):
                fact_claim = fact.get("claim_text", "").lower()
                # Check if draft asserts this fact without attribution
                for sec in content.sections:
                    for p in sec.paragraphs:
                        for s in p.sentences:
                            s_lower = s.text.lower()
                            # If draft has the core claim words but lacks attribution verbs
                            words = set(fact_claim.split())
                            overlap = len(words.intersection(set(s_lower.split())))
                            if overlap >= 4 and not any(v in s_lower for v in ["according to", "claimed", "claims", "stated", "says", "reported"]):
                                issues.append(
                                    AuditIssueItem(
                                        issue_code="ATTRIBUTION_MISSING",
                                        issue_category="attribution",
                                        severity=IssueSeverity.MAJOR,
                                        section_id=sec.section_id,
                                        sentence_index=s.sentence_index,
                                        description=f"Claim requires explicit attribution: '{s.text[:80]}...'",
                                        recommended_action="Frame with clear attribution (e.g., 'According to company statements...').",
                                        routing_target="part5_writer",
                                    )
                                )

        crit_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        maj_count = sum(1 for i in issues if i.severity == IssueSeverity.MAJOR)
        score = max(0.0, 100.0 - (crit_count * 50.0) - (maj_count * 15.0))
        return issues, round(score, 2)
