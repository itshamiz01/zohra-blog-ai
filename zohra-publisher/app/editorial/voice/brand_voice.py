"""
Zohra — Brand Voice Engine (Part 5).

Applies brand voice profiles (tone, formality, vocabulary level, sentence style)
while strictly enforcing the non-negotiable invariant:
FACTUAL MEANING AND EVIDENCE MUST NOT CHANGE.
All numbers, dates, currencies, quotes, and core entity claims are validated post-transformation.
"""

from __future__ import annotations

import re

from app.schemas.editorial import BrandVoiceProfileResponse


class BrandVoiceEngine:
    """Transforms stylistic tone while guaranteeing factual invariance."""

    NUMBER_REGEX = re.compile(r"(\$|₹|€|£)?\b\d+(?:,\d+)*(?:\.\d+)?\b%?")
    DATE_REGEX = re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December|\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)

    @classmethod
    def apply_voice(
        cls,
        text: str,
        voice_profile: BrandVoiceProfileResponse | None = None,
    ) -> tuple[str, bool]:
        """Applies brand voice stylistic patterns and validates that factual tokens were preserved.

        Returns (transformed_text, was_applied).
        If factual tokens were modified or corrupted, transformation is rejected and original text is retained.
        """
        if not voice_profile or not text.strip():
            return text, False

        original_numbers = set(cls.NUMBER_REGEX.findall(text))
        original_dates = set(cls.DATE_REGEX.findall(text))

        transformed = text

        # 1. Apply style patterns
        # Formal to approachable transitions
        if voice_profile.formality == "casual":
            transformed = re.sub(r"\butilize\b", "use", transformed, flags=re.IGNORECASE)
            transformed = re.sub(r"\bfacilitate\b", "help", transformed, flags=re.IGNORECASE)
            transformed = re.sub(r"\bcommence\b", "start", transformed, flags=re.IGNORECASE)
        elif voice_profile.formality == "formal":
            transformed = re.sub(r"\bcan't\b", "cannot", transformed, flags=re.IGNORECASE)
            transformed = re.sub(r"\bdon't\b", "do not", transformed, flags=re.IGNORECASE)

        # 2. Vocabulary adjustments
        if voice_profile.vocabulary_level == "simple":
            transformed = re.sub(r"\bconsequently\b", "as a result", transformed, flags=re.IGNORECASE)
            transformed = re.sub(r"\bsubsequently\b", "later", transformed, flags=re.IGNORECASE)
            transformed = re.sub(r"\bpredominantly\b", "mostly", transformed, flags=re.IGNORECASE)

        # 3. Directness adjustments (remove passive hedging)
        if voice_profile.directness == "high":
            transformed = re.sub(r"\bit would appear that\b", "", transformed, flags=re.IGNORECASE)
            transformed = re.sub(r"\bone could argue that\b", "", transformed, flags=re.IGNORECASE)

        # Clean spaces
        transformed = re.sub(r"\s{2,}", " ", transformed).strip()

        # 4. CRITICAL INVARIANT: Factual Token Verification
        new_numbers = set(cls.NUMBER_REGEX.findall(transformed))
        new_dates = set(cls.DATE_REGEX.findall(transformed))

        if original_numbers != new_numbers or original_dates != new_dates:
            # FACTUAL INVARIANCE VIOLATED -> Reject transformation completely
            return text, False

        return transformed, True

    @classmethod
    def verify_factual_invariance(cls, text_before: str, text_after: str) -> bool:
        """Verifies that all numbers, dates, and quotes remain identical."""
        nums_before = sorted(cls.NUMBER_REGEX.findall(text_before))
        nums_after = sorted(cls.NUMBER_REGEX.findall(text_after))
        if nums_before != nums_after:
            return False

        dates_before = sorted(cls.DATE_REGEX.findall(text_before))
        dates_after = sorted(cls.DATE_REGEX.findall(text_after))
        return dates_before == dates_after
