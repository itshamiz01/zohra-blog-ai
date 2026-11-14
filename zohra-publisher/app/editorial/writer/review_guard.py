"""
Zohra — Review Restriction Guard (Part 5).

Enforces strict compliance with Section 14:
Prohibits the generation of fake hands-on testing claims ("We tested this for 3 weeks",
"In our hands-on lab evaluation") when no physical test occurred.
Rewrites or sanitizes statements to reflect evidence-based analysis of documented facts.
"""

from __future__ import annotations

import re


class ReviewRestrictionGuard:
    """Detects and cleanses unauthorized first-hand testing assertions."""

    FAKE_EXPERIENCE_PATTERNS = [
        (re.compile(r"\b(we tested|we reviewed|in our testing|during our tests|our hands-on testing|in our lab|our benchmark tests)\b", re.IGNORECASE), "based on documented specifications and independent reports"),
        (re.compile(r"\b(we bought|we purchased|our team ordered)\b", re.IGNORECASE), "according to verified commercial listings"),
        (re.compile(r"\b(we interviewed|we spoke with the founders|in our conversation with)\b", re.IGNORECASE), "in officially released statements"),
        (re.compile(r"\b(we noticed during our daily use|in our personal experience)\b", re.IGNORECASE), "according to user reports and documented workflows"),
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> tuple[str, bool]:
        """Scans and replaces fake first-hand experience claims with evidence-based framing.

        Returns (sanitized_text, was_modified).
        """
        modified = False
        result = text
        for pat, replacement in cls.FAKE_EXPERIENCE_PATTERNS:
            if pat.search(result):
                result = pat.sub(replacement, result)
                modified = True

        return result, modified

    @classmethod
    def contains_fake_experience(cls, text: str) -> bool:
        """Returns True if text contains prohibited fake first-hand claims."""
        return any(pat.search(text) for pat, _ in cls.FAKE_EXPERIENCE_PATTERNS)
