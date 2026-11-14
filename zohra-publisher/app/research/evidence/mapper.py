"""
Zohra — Evidence Mapper.

Maps extracted claims to source document passages, evaluates support direction
(supports, contradicts, partially_supports, context_only), and calculates evidence strength.
"""

from __future__ import annotations

import re
from typing import Any

from app.schemas.research import SupportDirection


class EvidenceMapper:
    """Evaluates the alignment between a claim and an excerpt from a source document."""

    @classmethod
    def evaluate_support(
        cls,
        claim_text: str,
        excerpt: str,
        is_primary_source: bool = False,
        source_research_value: float = 70.0,
    ) -> dict[str, Any]:
        c_words = set(re.findall(r"\b[a-z0-9]+\b", claim_text.lower()))
        e_words = set(re.findall(r"\b[a-z0-9]+\b", excerpt.lower()))

        if not c_words or not e_words:
            return {
                "support_direction": SupportDirection.CONTEXT_ONLY.value,
                "relevance_score": 0.2,
                "evidence_strength_score": 0.2,
            }

        overlap = len(c_words.intersection(e_words))
        overlap_ratio = overlap / len(c_words)

        # Check for direct negation/contradiction markers
        negation_markers = ("not", "never", "no longer", "untrue", "false", "denies", "refutes")
        has_negation = any(m in excerpt.lower() for m in negation_markers)

        # Check for conflicting numbers if both have numbers
        c_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", claim_text))
        e_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", excerpt))
        num_mismatch = bool(c_nums and e_nums and not c_nums.intersection(e_nums))

        if has_negation and overlap_ratio >= 0.5 or num_mismatch and overlap_ratio >= 0.6:
            direction = SupportDirection.CONTRADICTS.value
        elif overlap_ratio >= 0.65:
            direction = SupportDirection.SUPPORTS.value
        elif overlap_ratio >= 0.35:
            direction = SupportDirection.PARTIALLY_SUPPORTS.value
        else:
            direction = SupportDirection.CONTEXT_ONLY.value

        # Calculate evidence strength (0.0 to 1.0)
        base_strength = (source_research_value / 100.0) * overlap_ratio
        if is_primary_source:
            base_strength = min(1.0, base_strength * 1.25)

        strength = round(max(0.1, min(1.0, base_strength)), 2)

        return {
            "support_direction": direction,
            "relevance_score": round(min(1.0, overlap_ratio), 2),
            "evidence_strength_score": strength,
        }
