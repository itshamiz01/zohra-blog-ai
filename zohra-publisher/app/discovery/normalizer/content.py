"""
Zohra — Content Normalizer & Hasher.

Computes deterministic SHA256 hashes of normalized titles and content,
counts words, and generates clean excerpts.
"""

from __future__ import annotations

import hashlib
import re

from app.discovery.security.sanitizer import sanitize_text


def normalize_title(title: str) -> str:
    """Normalize a title by stripping extra spaces, lowercase, removing special punctuation."""
    if not title:
        return ""
    clean = sanitize_text(title).lower()
    # Remove leading/trailing symbols, collapse non-alphanumeric separators
    clean = re.sub(r"[^\w\s]", "", clean)
    return re.sub(r"\s+", " ", clean).strip()


def compute_title_hash(title: str) -> str:
    """Compute deterministic SHA256 of normalized title."""
    norm = normalize_title(title)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def compute_content_hash(content: str) -> str:
    """Compute deterministic SHA256 of normalized content."""
    clean = sanitize_text(content).lower()
    # Collapse multiple whitespaces
    norm = re.sub(r"\s+", " ", clean).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def compute_word_count(text: str) -> int:
    """Calculate word count of normalized text."""
    if not text:
        return 0
    words = re.findall(r"\b\w+\b", text)
    return len(words)


def extract_clean_summary(text: str, max_chars: int = 300, max_sentences: int | None = None) -> str:
    """Extract a clean, readable summary/excerpt respecting sentence boundaries."""
    if not text:
        return ""
    clean = sanitize_text(text)
    if max_sentences is not None and max_sentences > 0:
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        selected = sentences[:max_sentences]
        return " ".join(selected).strip()

    if len(clean) <= max_chars:
        return clean

    truncated = clean[:max_chars]
    # Find last period, exclamation, or question mark
    last_punct = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "))
    if last_punct > max_chars // 2:
        return truncated[: last_punct + 1].strip()

    # Otherwise fallback to last whitespace
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space].strip() + "..."

    return truncated.strip() + "..."


class ContentNormalizer:
    hash_content = staticmethod(compute_content_hash)
    hash_title = staticmethod(compute_title_hash)
    count_words = staticmethod(compute_word_count)
    extract_summary = staticmethod(extract_clean_summary)
