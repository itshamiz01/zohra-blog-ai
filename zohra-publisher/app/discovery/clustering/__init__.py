"""Zohra — Event Clustering package."""

from app.discovery.clustering.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    cosine_similarity,
)
from app.discovery.clustering.engine import (
    ClusterMatch,
    EventClusteringEngine,
    compute_entity_overlap,
    compute_headline_similarity,
    compute_time_proximity,
)
from app.discovery.clustering.operations import merge_events, split_event

__all__ = [
    "EmbeddingProvider",
    "DeterministicEmbeddingProvider",
    "cosine_similarity",
    "ClusterMatch",
    "EventClusteringEngine",
    "compute_headline_similarity",
    "compute_entity_overlap",
    "compute_time_proximity",
    "merge_events",
    "split_event",
]
