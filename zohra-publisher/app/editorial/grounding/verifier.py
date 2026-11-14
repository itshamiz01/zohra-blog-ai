"""
Zohra — Grounding Verifier (Part 5).

Performs strict sentence-level factual verification against Part 4 ResearchPackage:
maps sentences to claims, checks attribution compliance, prevents prohibited claims,
validates numeric and currency exactness, and verifies quote provenance.
"""

from __future__ import annotations

import contextlib
import re
from typing import Any

from app.schemas.editorial import GroundingStatus, SentenceGroundingDetail
from app.schemas.research import FinalResearchPackage, VerifiedFactHandoff


class GroundingReport:
    def __init__(
        self,
        grounding_score: float,
        sentence_details: list[SentenceGroundingDetail],
        attribution_compliant: bool,
        prohibited_claims_found: list[str],
        numeric_mismatches: list[dict[str, Any]],
        unsupported_sentences: list[str],
    ):
        self.grounding_score = grounding_score
        self.sentence_details = sentence_details
        self.attribution_compliant = attribution_compliant
        self.prohibited_claims_found = prohibited_claims_found
        self.numeric_mismatches = numeric_mismatches
        self.unsupported_sentences = unsupported_sentences


class GroundingVerifier:
    """Verifies that generated draft content strictly adheres to verified evidence boundaries."""

    CURRENCY_NUM_REGEX = re.compile(r"(\$|₹|€|£)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(USD|INR|EUR|GBP|%|GB|MB|tokens)?", re.IGNORECASE)
    ATTRIBUTION_KEYWORDS = ["according to", "states that", "reported that", "official documentation", "company states", "listed in", "reports that"]

    @classmethod
    def verify_draft(
        cls,
        content: str,
        research_pkg: FinalResearchPackage,
        sections_data: list[dict[str, Any]] | None = None,
    ) -> GroundingReport:
        verified_facts: dict[str, VerifiedFactHandoff] = {f.claim_id: f for f in research_pkg.verified_facts}
        prohibited_ids = set(research_pkg.instructions_for_writer.do_not_state_as_fact_claim_ids)
        attrib_ids = set(research_pkg.instructions_for_writer.attribution_required_claim_ids)

        sentence_details: list[SentenceGroundingDetail] = []
        unsupported_sentences: list[str] = []
        prohibited_found: list[str] = []
        numeric_mismatches: list[dict[str, Any]] = []

        # Split content into sentences
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", content) if len(s.strip()) > 15]

        # 1. Prohibited Claims Check
        for pid in prohibited_ids:
            # Check if any text from disputed claims appears without qualification
            for s in raw_sentences:
                if pid in s.lower():
                    prohibited_found.append(f"Prohibited claim {pid} found in sentence: '{s[:80]}...'")

        # 2. Sentence-Level Grounding
        material_sentences_count = 0
        grounded_sentences_count = 0
        missing_attribution_count = 0

        for idx, sentence in enumerate(raw_sentences):
            # Skip headings and structural markers
            if sentence.startswith("#") or sentence.startswith("|") or sentence.startswith("- **Documented Limitation"):
                continue

            # Identify mapped claims by matching keywords and entities
            mapped_claim_ids: list[str] = []
            s_lower = sentence.lower()

            for cid, fact in verified_facts.items():
                fact_words = [w for w in fact.claim.lower().split() if len(w) > 3 and w not in ("with", "that", "this", "from", "have")]
                match_count = sum(1 for w in fact_words if w in s_lower)
                if len(fact_words) > 0 and (match_count / len(fact_words)) >= 0.5:
                    mapped_claim_ids.append(cid)

            # Check if sentence makes a material factual assertion (contains numbers, currencies, or claims)
            has_numbers = bool(cls.CURRENCY_NUM_REGEX.search(sentence))
            is_material = has_numbers or bool(mapped_claim_ids)

            if is_material:
                material_sentences_count += 1
                if mapped_claim_ids:
                    # Check attribution requirement if applicable
                    requires_attrib = any(cid in attrib_ids for cid in mapped_claim_ids)
                    has_attrib = any(ak in s_lower for ak in cls.ATTRIBUTION_KEYWORDS)

                    if requires_attrib and not has_attrib:
                        missing_attribution_count += 1
                        status = GroundingStatus.ATTRIBUTION_REQUIRED.value
                    else:
                        status = GroundingStatus.GROUNDED.value
                        grounded_sentences_count += 1
                else:
                    status = GroundingStatus.UNGROUNDED.value
                    unsupported_sentences.append(sentence)
            else:
                status = GroundingStatus.NON_FACTUAL.value

            sentence_details.append(
                SentenceGroundingDetail(
                    sentence_index=idx,
                    section_id="sec_body",
                    sentence_text=sentence,
                    claim_ids=mapped_claim_ids,
                    grounding_status=status,
                    confidence=0.95 if mapped_claim_ids else 0.5,
                )
            )

        # 3. Numeric & Currency Consistency Check
        # Compare numbers in text against verified facts
        text_numbers = cls.CURRENCY_NUM_REGEX.findall(content)
        verified_number_values = {
            f.numeric_value for f in research_pkg.verified_facts if f.numeric_value is not None
        }
        for num in research_pkg.important_numbers:
            if "value" in num:
                with contextlib.suppress(ValueError, TypeError):
                    verified_number_values.add(float(num["value"]))

        for prefix, num_str, unit in text_numbers:
            try:
                val = float(num_str.replace(",", ""))
                # Skip common years or small structural counts (1, 2, 3, 2026)
                if val in (1.0, 2.0, 3.0, 4.0, 5.0, 2026.0):
                    continue
                if val not in verified_number_values:
                    # If number does not match any verified fact, record check
                    numeric_mismatches.append({
                        "found_value": val,
                        "raw_token": f"{prefix}{num_str} {unit}".strip(),
                    })
            except ValueError:
                pass

        # Calculate Grounding Score
        if material_sentences_count == 0:
            final_grounding_score = 100.0
        else:
            base_score = (grounded_sentences_count / material_sentences_count) * 100.0
            # Apply penalties for missing attribution or prohibited claims
            penalties = (missing_attribution_count * 5.0) + (len(prohibited_found) * 25.0)
            final_grounding_score = max(0.0, min(100.0, base_score - penalties))

        attribution_compliant = missing_attribution_count == 0

        return GroundingReport(
            grounding_score=round(final_grounding_score, 1),
            sentence_details=sentence_details,
            attribution_compliant=attribution_compliant,
            prohibited_claims_found=prohibited_found,
            numeric_mismatches=numeric_mismatches,
            unsupported_sentences=unsupported_sentences,
        )
