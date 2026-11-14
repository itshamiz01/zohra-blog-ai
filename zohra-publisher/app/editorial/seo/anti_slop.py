"""
Zohra — AI Slop & Redundancy Detector (Part 5).

Detects generic AI clichés, repetitive transitions, and low-density filler.
Computes slop score, redundancy score, and information density score.
"""

from __future__ import annotations

import re


class AISlopDetector:
    """Detects and penalizes generic AI writing patterns and repetitive filler."""

    SLOP_PATTERNS = [
        re.compile(r"\bin today's (fast-paced|digital|rapidly evolving|ever-changing) (world|landscape|environment)\b", re.IGNORECASE),
        re.compile(r"\bit's important to note( that)?\b", re.IGNORECASE),
        re.compile(r"\bwhether you're a beginner or (an )?expert\b", re.IGNORECASE),
        re.compile(r"\blet's dive in(to)?\b", re.IGNORECASE),
        re.compile(r"\bgame(-|\s)changer\b", re.IGNORECASE),
        re.compile(r"\brevolutionary\b", re.IGNORECASE),
        re.compile(r"\bunlock the (true )?power of\b", re.IGNORECASE),
        re.compile(r"\btake your .* to the next level\b", re.IGNORECASE),
        re.compile(r"\bever-evolving landscape\b", re.IGNORECASE),
        re.compile(r"\bdelve into\b", re.IGNORECASE),
        re.compile(r"\bseamless integration\b", re.IGNORECASE),
        re.compile(r"\bbustling\b", re.IGNORECASE),
    ]

    @classmethod
    def evaluate(cls, text: str) -> dict[str, float]:
        """Evaluates slop, redundancy, and information density.

        Returns:
            slop_penalty: Points to subtract for AI clichés (0-100)
            redundancy_score: 0-100 (100 = completely unique, 0 = highly repetitive)
            information_density: 0-100 (percentage of content adding specific information)
        """
        if not text or not text.strip():
            return {"slop_penalty": 0.0, "redundancy_score": 100.0, "information_density": 100.0}

        # 1. Slop Occurrences
        slop_count = sum(len(pat.findall(text)) for pat in cls.SLOP_PATTERNS)
        slop_penalty = min(50.0, slop_count * 10.0)

        # 2. Redundancy Analysis (Sentence N-Gram duplication)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 15]
        if len(sentences) < 2:
            redundancy_score = 100.0
        else:
            word_sets = [set(s.lower().split()) for s in sentences]
            total_pairs = 0
            high_similarity_pairs = 0
            for i in range(len(word_sets)):
                for j in range(i + 1, min(i + 4, len(word_sets))):
                    total_pairs += 1
                    inter = len(word_sets[i] & word_sets[j])
                    union = len(word_sets[i] | word_sets[j])
                    if union > 0 and (inter / union) > 0.65:
                        high_similarity_pairs += 1

            dup_rate = high_similarity_pairs / max(1, total_pairs)
            redundancy_score = max(0.0, 100.0 - (dup_rate * 100.0))

        # 3. Information Density (Ratio of specific tokens: numbers, capitalized terms, nouns vs filler)
        words = text.split()
        if not words:
            information_density = 100.0
        else:
            specific_count = sum(
                1 for w in words
                if (any(c.isdigit() for c in w) or w[0].isupper() or len(w) > 7)
            )
            density_ratio = specific_count / len(words)
            # Normal density ratio is between 0.15 and 0.45
            information_density = min(100.0, max(20.0, density_ratio * 250.0))

        return {
            "slop_penalty": round(slop_penalty, 1),
            "redundancy_score": round(redundancy_score, 1),
            "information_density": round(information_density, 1),
            "slop_count": slop_count,
        }

    @classmethod
    def cleanse_slop(cls, text: str) -> str:
        """Removes or neutralizes obvious AI cliché phrases."""
        clean = text
        for pat in cls.SLOP_PATTERNS:
            clean = pat.sub("", clean)

        # Clean up double spaces or awkward leftover punctuation
        clean = re.sub(r"\s{2,}", " ", clean)
        clean = re.sub(r"\s+([,.;])", r"\1", clean)
        return clean.strip()
