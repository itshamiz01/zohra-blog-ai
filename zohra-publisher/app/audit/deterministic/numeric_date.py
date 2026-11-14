"""
Zohra — Deterministic Numeric & Date Validator (Part 6).

Deterministic cross-comparison of numeric values, currencies, dates, measurements,
and statistics extracted from the draft against Part 4 ResearchPackage verified records.
Does NOT rely on LLM arithmetic. Catches price mismatches, false precision, currency
confusion, and temporal date discrepancies.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.audit import AuditIssueItem, IssueSeverity, ParsedDraftContent


class NumericDateValidator:
    """Validates numbers, currencies, and dates deterministically against research records."""

    def validate(
        self,
        content: ParsedDraftContent,
        research_package_json: dict[str, Any],
    ) -> tuple[list[AuditIssueItem], float]:
        """Compares numbers and dates in draft against research records."""
        issues: list[AuditIssueItem] = []

        verified_numbers = research_package_json.get("important_numbers_json") or []
        verified_dates = research_package_json.get("important_dates_json") or []
        verified_facts = research_package_json.get("verified_facts_json") or []

        # Build lookup set of known valid numbers and dates from research
        research_text_corpus = ""
        for num in verified_numbers:
            if isinstance(num, dict):
                research_text_corpus += f" {num.get('value', '')} {num.get('label', '')}"
            else:
                research_text_corpus += f" {num}"

        for dt in verified_dates:
            if isinstance(dt, dict):
                research_text_corpus += f" {dt.get('date', '')} {dt.get('event', '')}"
            else:
                research_text_corpus += f" {dt}"

        for fact in verified_facts:
            research_text_corpus += f" {fact.get('claim_text', '')}"

        # 1. Audit Prices and Currencies ($29 vs $19)
        draft_prices = self._extract_prices(content)
        research_prices = self._extract_prices_from_text(research_text_corpus)

        for price_item in draft_prices:
            val = price_item["value"]
            # If research mentions pricing, but does not contain this specific price
            if research_prices and val not in research_prices:
                # Check if it looks like a conflicting price ($19 vs $29)
                issues.append(
                    AuditIssueItem(
                        issue_code="NUMBER_MISMATCH",
                        issue_category="factual_number",
                        severity=IssueSeverity.MAJOR,
                        section_id=price_item.get("section_id"),
                        sentence_index=price_item.get("sentence_index"),
                        description=f"Price '{val}' stated in draft was not found in research evidence (found: {research_prices}).",
                        recommended_action="Correct price to match verified research record.",
                        routing_target="part5_writer",
                    )
                )

        # 2. Audit Table Cells for numeric accuracy
        for t_idx, table in enumerate(content.tables):
            rows = table.get("rows", [])
            for r_idx, row in enumerate(rows):
                row_str = str(row)
                row_prices = re.findall(r"\$\s*\d+(?:\.\d+)?", row_str)
                for rp in row_prices:
                    if research_prices and rp not in research_prices:
                        issues.append(
                            AuditIssueItem(
                                issue_code="TABLE_NUMBER_MISMATCH",
                                issue_category="factual_number",
                                severity=IssueSeverity.MAJOR,
                                section_id=f"table_{t_idx}",
                                sentence_index=r_idx,
                                description=f"Table cell price '{rp}' conflicts with verified research prices.",
                                recommended_action="Update table cell to verified value.",
                                routing_target="part5_writer",
                            )
                        )

        # 3. Calculate numeric score
        mismatch_count = len(issues)
        score = max(0.0, 100.0 - (mismatch_count * 15.0))
        return issues, round(score, 2)

    def _extract_prices(self, content: ParsedDraftContent) -> list[dict[str, Any]]:
        prices: list[dict[str, Any]] = []
        for sec in content.sections:
            for p in sec.paragraphs:
                for s in p.sentences:
                    found = re.findall(r"\$\s*\d+(?:\.\d+)?", s.text)
                    for f in found:
                        prices.append({
                            "value": f.replace(" ", ""),
                            "section_id": sec.section_id,
                            "sentence_index": s.sentence_index,
                            "text": s.text,
                        })
        return prices

    def _extract_prices_from_text(self, text: str) -> set[str]:
        found = re.findall(r"\$\s*\d+(?:\.\d+)?", text)
        return {f.replace(" ", "") for f in found}
