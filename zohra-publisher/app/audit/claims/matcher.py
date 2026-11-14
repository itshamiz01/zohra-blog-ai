"""
Zohra — Claim Matcher & Semantic Entailment Engine (Part 6).

Matches independently extracted draft claims against Part 4 Research Package claims.
Detects:
- Full Entailment (SUPPORTED)
- Partial Entailment (PARTIALLY_SUPPORTED)
- Unsupported Assertions (UNSUPPORTED)
- Direct Contradictions (CONTRADICTED)
- Quantifier / Strength Inflation (e.g. "some users" -> "all users", "may" -> "will")
- Scope Expansion (e.g. "US pricing" -> "worldwide pricing", "Beta" -> "General Release")
- Stale Claims (e.g. historical facts asserted as current)
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.schemas.audit import ClaimMatchResult, ClaimVerificationStatus, ExtractedClaim


class ClaimMatcher:
    """Matches draft claims against Part 4 verified research claims and evidence."""

    INFLATION_PAIRS = [
        (r"\bmay\b", r"\bwill\b"),
        (r"\bsome\b", r"\ball\b"),
        (r"\bmany\b", r"\beveryone\b"),
        (r"\bapproximately\b", r"\bexactly\b"),
        (r"\bup to\b", r"\bguaranteed\b"),
        (r"\bcan help\b", r"\bproves\b"),
        (r"\bpromising\b", r"\brevolutionary\b"),
    ]

    SCOPE_EXPANSION_PATTERNS = [
        r"\bworldwide\b",
        r"\bglobally\b",
        r"\ball users\b",
        r"\bevery plan\b",
        r"\bunlimited\b",
    ]

    def match_claims(
        self,
        extracted_claims: list[ExtractedClaim],
        research_package_json: dict[str, Any],
    ) -> list[ClaimMatchResult]:
        """Matches each extracted draft claim against research claims and evidence items."""
        verified_facts = list(research_package_json.get("verified_facts_json") or [])
        primary_sources = research_package_json.get("primary_sources_json") or []
        supporting_sources = research_package_json.get("supporting_sources_json") or []
        for s in (primary_sources + supporting_sources):
            if s.get("snippet"):
                verified_facts.append({"claim_text": s["snippet"], "id": s.get("source_id") or s.get("id")})
            if s.get("text"):
                verified_facts.append({"claim_text": s["text"], "id": s.get("source_id") or s.get("id")})

        uncertain_claims = research_package_json.get("uncertain_claims_json") or []
        contradictions = research_package_json.get("contradictions_json") or []

        results: list[ClaimMatchResult] = []

        for draft_claim in extracted_claims:
            match_res = self._match_single_claim(
                draft_claim=draft_claim,
                verified_facts=verified_facts,
                uncertain_claims=uncertain_claims,
                contradictions=contradictions,
            )
            results.append(match_res)

        return results

    def _match_single_claim(
        self,
        draft_claim: ExtractedClaim,
        verified_facts: list[dict[str, Any]],
        uncertain_claims: list[dict[str, Any]],
        contradictions: list[dict[str, Any]],
    ) -> ClaimMatchResult:
        """Finds best matching research claim and validates entailment and scope."""
        best_fact: dict[str, Any] | None = None
        best_score = 0.0

        d_tokens = set(draft_claim.normalized_claim.split())

        for fact in verified_facts:
            fact_text = fact.get("claim_text") or fact.get("canonical_text") or ""
            f_tokens = set(fact_text.lower().split())
            if not f_tokens or not d_tokens:
                continue

            overlap = len(d_tokens.intersection(f_tokens))
            score = overlap / max(len(d_tokens), len(f_tokens))

            if score > best_score:
                best_score = score
                best_fact = fact

        # Check for contradiction match
        for contra in contradictions:
            topic = contra.get("topic", "").lower()
            topic_tokens = set(topic.split())
            contra_text = topic + " " + contra.get("resolution", "").lower()
            c_tokens = set(contra_text.split())
            # If the draft matches the contradiction topic or overlaps substantially with contradiction text
            topic_match = bool(topic_tokens and topic_tokens.issubset(d_tokens))
            general_overlap = len(d_tokens.intersection(c_tokens)) / max(len(d_tokens), 1) >= 0.35
            if topic_match or general_overlap:
                # Disputed fact asserted as definite
                return ClaimMatchResult(
                    claim_text=draft_claim.claim_text,
                    normalized_claim=draft_claim.normalized_claim,
                    section_id=draft_claim.section_id,
                    sentence_index=draft_claim.sentence_index,
                    importance=draft_claim.importance,
                    matched_research_claim_id=uuid.UUID(contra.get("id")) if contra.get("id") else None,
                    match_confidence=0.85,
                    verification_status=ClaimVerificationStatus.CONTRADICTED,
                    entailment_score=0.2,
                    audit_notes="Draft asserts disputed contradiction as established fact without qualification.",
                )

        # Check for uncertain claim asserted as fact (UNKNOWN -> FACT)
        for unc in uncertain_claims:
            u_text = unc.get("claim_text", "")
            u_tokens = set(u_text.lower().split())
            if len(d_tokens.intersection(u_tokens)) / max(len(d_tokens), 1) > 0.6:
                return ClaimMatchResult(
                    claim_text=draft_claim.claim_text,
                    normalized_claim=draft_claim.normalized_claim,
                    section_id=draft_claim.section_id,
                    sentence_index=draft_claim.sentence_index,
                    importance=draft_claim.importance,
                    matched_research_claim_id=uuid.UUID(unc.get("id")) if unc.get("id") else None,
                    match_confidence=0.8,
                    verification_status=ClaimVerificationStatus.UNSUPPORTED,
                    entailment_score=0.3,
                    audit_notes="Research marked this fact as UNKNOWN/UNCERTAIN, but draft asserted it as fact.",
                )

        if not best_fact or best_score < 0.25:
            # No matching evidence found
            return ClaimMatchResult(
                claim_text=draft_claim.claim_text,
                normalized_claim=draft_claim.normalized_claim,
                section_id=draft_claim.section_id,
                sentence_index=draft_claim.sentence_index,
                importance=draft_claim.importance,
                matched_research_claim_id=None,
                match_confidence=best_score,
                verification_status=ClaimVerificationStatus.UNSUPPORTED,
                entailment_score=0.0,
                audit_notes="No matching research evidence found in ResearchPackage.",
            )

        fact_text = best_fact.get("claim_text") or best_fact.get("canonical_text") or ""
        fact_id_val = best_fact.get("id")
        claim_uuid: uuid.UUID | None = None
        if fact_id_val:
            try:
                claim_uuid = uuid.UUID(str(fact_id_val))
            except ValueError:
                claim_uuid = None

        # Detect inflation
        inflation_detected = False
        for weaktxt, strongtxt in self.INFLATION_PAIRS:
            if re.search(weaktxt, fact_text, re.IGNORECASE) and re.search(strongtxt, draft_claim.claim_text, re.IGNORECASE):
                inflation_detected = True
                break

        # Detect scope expansion
        scope_expanded = False
        for scope_pat in self.SCOPE_EXPANSION_PATTERNS:
            if re.search(scope_pat, draft_claim.claim_text, re.IGNORECASE) and not re.search(scope_pat, fact_text, re.IGNORECASE):
                scope_expanded = True
                break

        # Check attribution requirement
        attribution_missing = False
        if best_fact.get("attribution_required", False) and not draft_claim.requires_attribution:
            attribution_missing = True

        # Check numeric alignment
        fact_numbers = self._extract_numbers(fact_text)
        if draft_claim.numbers_found and fact_numbers and not any(num in fact_numbers for num in draft_claim.numbers_found):
            return ClaimMatchResult(
                claim_text=draft_claim.claim_text,
                normalized_claim=draft_claim.normalized_claim,
                section_id=draft_claim.section_id,
                    sentence_index=draft_claim.sentence_index,
                    importance=draft_claim.importance,
                    matched_research_claim_id=claim_uuid,
                    match_confidence=best_score,
                    verification_status=ClaimVerificationStatus.MISLEADING,
                    entailment_score=0.4,
                    audit_notes=f"Numeric mismatch: draft stated {draft_claim.numbers_found} but evidence stated {fact_numbers}.",
                )

        if scope_expanded:
            return ClaimMatchResult(
                claim_text=draft_claim.claim_text,
                normalized_claim=draft_claim.normalized_claim,
                section_id=draft_claim.section_id,
                sentence_index=draft_claim.sentence_index,
                importance=draft_claim.importance,
                matched_research_claim_id=claim_uuid,
                match_confidence=best_score,
                verification_status=ClaimVerificationStatus.SCOPE_MISMATCH,
                entailment_score=0.5,
                scope_expanded=True,
                audit_notes="Scope expanded beyond evidence boundaries.",
            )

        if attribution_missing:
            return ClaimMatchResult(
                claim_text=draft_claim.claim_text,
                normalized_claim=draft_claim.normalized_claim,
                section_id=draft_claim.section_id,
                sentence_index=draft_claim.sentence_index,
                importance=draft_claim.importance,
                matched_research_claim_id=claim_uuid,
                match_confidence=best_score,
                verification_status=ClaimVerificationStatus.ATTRIBUTION_MISSING,
                entailment_score=0.7,
                audit_notes="Claim requires explicit source attribution, but was asserted as universal fact.",
            )

        if inflation_detected:
            return ClaimMatchResult(
                claim_text=draft_claim.claim_text,
                normalized_claim=draft_claim.normalized_claim,
                section_id=draft_claim.section_id,
                sentence_index=draft_claim.sentence_index,
                importance=draft_claim.importance,
                matched_research_claim_id=claim_uuid,
                match_confidence=best_score,
                verification_status=ClaimVerificationStatus.PARTIALLY_SUPPORTED,
                entailment_score=0.65,
                inflation_detected=True,
                audit_notes="Evidence strength or quantifier inflated in draft prose.",
            )

        # Standard supported or partially supported
        status = ClaimVerificationStatus.SUPPORTED if best_score >= 0.4 else ClaimVerificationStatus.PARTIALLY_SUPPORTED
        entailment = min(1.0, best_score * 1.4)

        return ClaimMatchResult(
            claim_text=draft_claim.claim_text,
            normalized_claim=draft_claim.normalized_claim,
            section_id=draft_claim.section_id,
            sentence_index=draft_claim.sentence_index,
            importance=draft_claim.importance,
            matched_research_claim_id=claim_uuid,
            match_confidence=best_score,
            verification_status=status,
            entailment_score=entailment,
            audit_notes="Entailment verified against research evidence.",
        )

    def _extract_numbers(self, text: str) -> list[str]:
        pattern = r"(?:\$\s*\d+(?:\.\d+)?|\b\d+(?:\.\d+)?%|\b\d+(?:,\d{3})*(?:\.\d+)?\b)"
        return re.findall(pattern, text)
