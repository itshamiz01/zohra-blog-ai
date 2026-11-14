"""
Zohra — Document Deduplication Engine.

Provides multi-level deduplication without expensive LLM calls:
- Level 1: Exact canonical URL match
- Level 2: External feed GUID match
- Level 3: Content hash match (SHA256)
- Level 4: Near-duplicate match via 64-bit SimHash & Token Jaccard similarity
"""

from __future__ import annotations

import hashlib
import re
from typing import NamedTuple


class DedupCheckResult(NamedTuple):
    is_duplicate: bool
    dedup_level: str | None  # "url", "external_id", "content_hash", "near_duplicate", None
    matched_document_id: str | None
    similarity_score: float


def compute_simhash(text: str, n_gram: int = 1) -> str:
    """
    Computes a 64-bit SimHash hex string for near-duplicate text detection.
    Very efficient for large scale comparison without embeddings or LLMs.
    """
    if not text:
        return "0" * 16

    clean = re.sub(r"[^\w\s]", "", text.lower())
    words = clean.split()
    if not words:
        return "0" * 16

    # Extract word tokens (1-grams by default for Charikar SimHash)
    tokens: list[str] = []
    if n_gram > 1 and len(words) >= n_gram:
        for i in range(len(words) - n_gram + 1):
            tokens.append(" ".join(words[i : i + n_gram]))
    else:
        tokens = words

    # 64-bit vector
    v = [0] * 64

    for token in tokens:
        # MD5 digest truncated to 64 bits (8 bytes)
        digest = hashlib.md5(token.encode("utf-8")).digest()[:8]
        token_hash = int.from_bytes(digest, byteorder="big")

        for i in range(64):
            bit = (token_hash >> i) & 1
            if bit == 1:
                v[i] += 1
            else:
                v[i] -= 1

    # Form 64-bit integer from vector signs
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i

    # Format as 16-character hex string
    return f"{fingerprint:016x}"


def simhash_hamming_distance(hash1: str, hash2: str) -> int:
    """Computes the Hamming distance (number of differing bits) between two 64-bit hex SimHashes."""
    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
    except (ValueError, TypeError):
        return 64

    xor_val = val1 ^ val2
    # Count set bits
    return bin(xor_val).count("1")


def simhash_similarity(hash1: str, hash2: str) -> float:
    """Converts 64-bit SimHash Hamming distance to a normalized 0.0 - 1.0 similarity score."""
    dist = simhash_hamming_distance(hash1, hash2)
    return max(0.0, 1.0 - (dist / 64.0))


def compute_token_jaccard_similarity(text1: str, text2: str) -> float:
    """Computes token Jaccard similarity between two text strings."""
    if not text1 or not text2:
        return 0.0

    words1 = set(re.findall(r"\b\w+\b", text1.lower()))
    words2 = set(re.findall(r"\b\w+\b", text2.lower()))

    if not words1 or not words2:
        return 0.0

    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))

    return intersection / union if union > 0 else 0.0


def is_near_duplicate(
    hash1: str,
    hash2: str,
    text1: str | None = None,
    text2: str | None = None,
    simhash_threshold: float = 0.88,  # Hamming distance <= 7 out of 64
    jaccard_threshold: float = 0.75,
) -> tuple[bool, float]:
    """
    Evaluates whether two documents are near-duplicates using SimHash and optional Jaccard confirmation.
    Returns (is_near_duplicate, similarity_score).
    """
    sim = simhash_similarity(hash1, hash2)
    if sim >= simhash_threshold:
        return True, sim

    if text1 and text2:
        jaccard = compute_token_jaccard_similarity(text1, text2)
        if jaccard >= jaccard_threshold:
            return True, max(sim, jaccard)

    return False, sim


class DeduplicationDetector:
    compute_simhash = staticmethod(compute_simhash)
    hamming_distance = staticmethod(simhash_hamming_distance)
    similarity = staticmethod(simhash_similarity)
    jaccard_similarity = staticmethod(compute_token_jaccard_similarity)

    @staticmethod
    def is_near_duplicate(hash1: str, hash2: str, max_hamming_distance: int = 7) -> bool:
        dist = simhash_hamming_distance(hash1, hash2)
        return dist <= max_hamming_distance
