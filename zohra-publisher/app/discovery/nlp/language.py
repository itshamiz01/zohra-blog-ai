"""
Zohra — Language Detection.

Detects language code and confidence across major scripts and languages:
- Script-based: Hindi (Devanagari), Arabic, Japanese (Kana/Kanji), Korean (Hangul), Chinese, Russian (Cyrillic)
- Stopword/n-gram profiles for Latin script: English, Spanish, French, German
"""

from __future__ import annotations

import re

# Unicode block ranges for script identification
SCRIPT_PATTERNS = [
    ("hi", re.compile(r"[\u0900-\u097F]")),  # Devanagari (Hindi, Marathi, etc.)
    ("ar", re.compile(r"[\u0600-\u06FF\u0750-\u077F]")),  # Arabic
    ("ko", re.compile(r"[\uAC00-\uD7AF\u1100-\u11FF]")),  # Hangul (Korean)
    ("ja", re.compile(r"[\u3040-\u309F\u30A0-\u30FF]")),  # Hiragana/Katakana (Japanese)
    ("zh", re.compile(r"[\u4E00-\u9FFF]")),  # CJK Unified Ideographs (Chinese)
    ("ru", re.compile(r"[\u0400-\u04FF]")),  # Cyrillic (Russian)
]

# High-frequency distinctive stopwords for Latin script languages
LATIN_STOPWORDS = {
    "en": {
        "the",
        "and",
        "is",
        "in",
        "to",
        "of",
        "it",
        "with",
        "for",
        "that",
        "this",
        "from",
        "at",
        "by",
        "an",
        "be",
        "has",
        "are",
    },
    "es": {
        "el",
        "la",
        "de",
        "que",
        "y",
        "en",
        "un",
        "se",
        "no",
        "por",
        "con",
        "para",
        "los",
        "las",
        "del",
        "una",
        "es",
    },
    "fr": {
        "le",
        "la",
        "de",
        "et",
        "en",
        "du",
        "un",
        "les",
        "des",
        "est",
        "une",
        "par",
        "pour",
        "dans",
        "qui",
        "sur",
    },
    "de": {
        "der",
        "die",
        "das",
        "und",
        "in",
        "den",
        "von",
        "zu",
        "mit",
        "ist",
        "des",
        "auf",
        "fuer",
        "für",
        "dem",
        "nicht",
        "ein",
        "eine",
    },
    "pt": {
        "o",
        "a",
        "de",
        "e",
        "do",
        "da",
        "em",
        "um",
        "para",
        "com",
        "não",
        "uma",
        "os",
        "no",
        "se",
        "na",
        "por",
        "mais",
    },
}


def detect_language(text: str) -> tuple[str, float]:
    """
    Detect language of a text string.
    Returns (language_code, confidence_0_to_1).
    Defaults to ('en', 0.5) if ambiguous.
    """
    if not text or len(text.strip()) == 0:
        return "en", 0.0

    sample = text[:2000]

    # 1. Check non-Latin scripts first
    script_counts: dict[str, int] = {}
    for code, pattern in SCRIPT_PATTERNS:
        matches = len(pattern.findall(sample))
        if matches > 0:
            script_counts[code] = matches

    if script_counts:
        top_script, count = max(script_counts.items(), key=lambda x: x[1])
        # If script chars form a significant part (>10% of alpha chars), choose it
        alpha_chars = sum(1 for c in sample if c.isalpha())
        if alpha_chars > 0 and (count / alpha_chars) > 0.08:
            confidence = min(0.99, max(0.60, count / alpha_chars * 1.5))
            return top_script, round(confidence, 2)

    # 2. Latin script word matching
    words = set(re.findall(r"\b[a-zA-Záéíóúüñßàâçêèëîïôûùöä]+\b", sample.lower()))
    if not words:
        return "en", 0.5

    best_lang = "en"
    best_score = 0

    for lang, stopwords in LATIN_STOPWORDS.items():
        overlap = len(words.intersection(stopwords))
        if overlap > best_score:
            best_score = overlap
            best_lang = lang

    if best_score > 0:
        # Confidence scales with number of matched stopwords
        confidence = min(0.95, 0.40 + (best_score * 0.08))
        return best_lang, round(confidence, 2)

    return "en", 0.50


class LanguageDetector:
    detect_language = staticmethod(detect_language)
