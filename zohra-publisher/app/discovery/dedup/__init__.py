"""Zohra — Discovery Deduplication package."""

from app.discovery.dedup.detector import (
    DedupCheckResult,
    compute_simhash,
    compute_token_jaccard_similarity,
    is_near_duplicate,
    simhash_hamming_distance,
    simhash_similarity,
)

__all__ = [
    "compute_simhash",
    "simhash_hamming_distance",
    "simhash_similarity",
    "compute_token_jaccard_similarity",
    "is_near_duplicate",
    "DedupCheckResult",
]
