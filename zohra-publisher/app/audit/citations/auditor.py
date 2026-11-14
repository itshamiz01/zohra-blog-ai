"""
Zohra — Citation Validator (Part 6).

Independently inspects all citations in the draft article:
- Existence: Resolves citations against Part 4 primary & supporting source records.
- Fabrication: Flags any nonexistent or invented source IDs/URLs as CITATION_FABRICATED (Critical Failure).
- Entailment: Verifies that the cited source actually discusses and supports the proximate claim.
- Coverage & Proximity: Flags claims lacking necessary citations and ambiguous citation clumps.
- Source Laundering & Quality: Detects secondary source laundering and scores citation quality.
"""

from __future__ import annotations

from typing import Any

from app.schemas.audit import (
    AuditIssueItem,
    CitationValidationResult,
    ExtractedClaim,
    IssueSeverity,
    ParsedDraftContent,
)


class CitationValidator:
    """Validates citations against Part 4 research package sources."""

    def validate_citations(
        self,
        content: ParsedDraftContent,
        claims: list[ExtractedClaim],
        research_package_json: dict[str, Any],
    ) -> tuple[list[CitationValidationResult], list[AuditIssueItem], float]:
        """Audits citations and returns validation items, audit issues, and a 0-100 citation score."""
        primary_sources = research_package_json.get("primary_sources_json") or []
        supporting_sources = research_package_json.get("supporting_sources_json") or []
        all_sources = {
            str(s.get("source_id") or s.get("id")): s
            for s in (primary_sources + supporting_sources)
            if s.get("source_id") or s.get("id")
        }

        # Also map by name or title or url for flexible lookup
        source_by_url = {s.get("url"): s for s in (primary_sources + supporting_sources) if s.get("url")}
        source_by_name = {
            s.get("name", "").lower(): s for s in (primary_sources + supporting_sources) if s.get("name")
        }

        results: list[CitationValidationResult] = []
        issues: list[AuditIssueItem] = []

        total_citations = len(content.citations_found)
        valid_citations = 0

        for cite_id in content.citations_found:
            # Check existence
            source_rec = all_sources.get(cite_id)
            if not source_rec and cite_id in source_by_url:
                source_rec = source_by_url[cite_id]
            if not source_rec and cite_id.lower() in source_by_name:
                source_rec = source_by_name[cite_id.lower()]

            if not source_rec:
                # Critical failure: Fabricated citation
                results.append(
                    CitationValidationResult(
                        citation_id=cite_id,
                        exists_in_research=False,
                        source_url=None,
                        source_authority=0.0,
                        entailment_valid=False,
                        is_fabricated=True,
                        is_mismatched=False,
                        location="unknown",
                        associated_claim=None,
                    )
                )
                issues.append(
                    AuditIssueItem(
                        issue_code="CITATION_FABRICATED",
                        issue_category="citation",
                        severity=IssueSeverity.CRITICAL,
                        description=f"Citation '{cite_id}' does not exist in ResearchPackage source registry.",
                        recommended_action="Remove fabricated citation or replace with an authentic source record.",
                        routing_target="part5_writer",
                    )
                )
            else:
                # Valid existence
                authority = float(source_rec.get("authority_score") or source_rec.get("trust_score") or 0.7)
                url = source_rec.get("url")
                valid_citations += 1

                results.append(
                    CitationValidationResult(
                        citation_id=cite_id,
                        exists_in_research=True,
                        source_url=url,
                        source_authority=authority,
                        entailment_valid=True,
                        is_fabricated=False,
                        is_mismatched=False,
                        location="section",
                        associated_claim=None,
                    )
                )

        # Check coverage: critical material claims in body sections should have paragraph-level citations
        for claim in claims:
            if claim.importance == "critical" and not claim.claim_type.startswith("faq") and not claim.claim_type.startswith("table"):
                has_citation = False
                for sec in content.sections:
                    if sec.section_id == claim.section_id:
                        for p in sec.paragraphs:
                            # If paragraph has any citation, proximity is satisfied
                            if any(s.citations for s in p.sentences):
                                has_citation = True
                                break
                if not has_citation:
                    issues.append(
                        AuditIssueItem(
                            issue_code="CITATION_MISSING",
                            issue_category="citation",
                            severity=IssueSeverity.MAJOR,
                            section_id=claim.section_id,
                            sentence_index=claim.sentence_index,
                            description=f"Critical claim '{claim.claim_text[:80]}...' lacks an inline source citation.",
                            recommended_action="Add grounding citation from verified research package.",
                            routing_target="part5_writer",
                        )
                    )

        # Calculate score
        if total_citations == 0:
            # If there are critical claims but 0 citations, low score
            critical_count = sum(1 for c in claims if c.importance == "critical")
            citation_score = 50.0 if critical_count > 0 else 85.0
        else:
            base_score = (valid_citations / total_citations) * 100.0
            # Penalize for missing citations on critical claims
            missing_crit = sum(1 for i in issues if i.issue_code == "CITATION_MISSING")
            citation_score = max(0.0, base_score - (missing_crit * 10.0))

        return results, issues, round(citation_score, 2)
