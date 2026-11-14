"""
Zohra — Event Clustering Engine.

Clusters related reports into real-world events using candidate narrowing
to avoid O(n^2) comparisons across the historical corpus:
  Stage 1: Time-window filtering (48h default)
  Stage 2: Category filtering / overlap
  Stage 3: Entity overlap scoring (Jaccard on canonical entity names)
  Stage 4: Headline text similarity
  Stage 5: Semantic embedding similarity
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, NamedTuple

from app.core.config import get_settings
from app.discovery.clustering.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    cosine_similarity,
)
from app.discovery.nlp.entities import ExtractedEntity


class ClusterMatch(NamedTuple):
    event_id: str
    similarity_score: float
    entity_overlap: float
    title_similarity: float
    semantic_similarity: float
    time_proximity: float
    matched_title: str


def compute_headline_similarity(title1: str, title2: str) -> float:
    """Computes token and n-gram overlap between two article titles."""
    if not title1 or not title2:
        return 0.0

    words1 = set(re.findall(r"\b\w+\b", title1.lower()))
    words2 = set(re.findall(r"\b\w+\b", title2.lower()))

    # Ignore trivial short words
    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "in",
        "on",
        "at",
        "to",
        "for",
        "with",
        "by",
        "of",
        "is",
        "its",
    }
    filtered1 = words1 - stop
    filtered2 = words2 - stop

    if not filtered1 or not filtered2:
        filtered1 = words1
        filtered2 = words2

    intersection = len(filtered1.intersection(filtered2))
    union = len(filtered1.union(filtered2))

    return intersection / union if union > 0 else 0.0


def compute_entity_overlap(doc_entities: list[str], event_entities: list[str]) -> float:
    """Computes Jaccard overlap between document entity keys and event entity keys."""
    if not doc_entities or not event_entities:
        return 0.0

    set1 = set(doc_entities)
    set2 = set(event_entities)

    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


def compute_time_proximity(
    doc_time: datetime, event_last_seen: datetime, window_hours: int = 48
) -> float:
    """Calculates time proximity decay [0.0 to 1.0]. Newer reports get higher scores."""
    if doc_time.tzinfo is None:
        doc_time = doc_time.replace(tzinfo=UTC)
    if event_last_seen.tzinfo is None:
        event_last_seen = event_last_seen.replace(tzinfo=UTC)

    delta_seconds = abs((doc_time - event_last_seen).total_seconds())
    max_seconds = window_hours * 3600.0

    if delta_seconds >= max_seconds:
        return 0.0

    return max(0.0, 1.0 - (delta_seconds / max_seconds))


class EventClusteringEngine:
    """
    Evaluates candidate events for a new document and determines
    whether to attach it to an existing event or create a new event.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        db: Any = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.db = db

    _cosine_similarity = staticmethod(cosine_similarity)

    @staticmethod
    def _filter_candidates(
        all_events: list[any],
        category: str,
        now: datetime,
        window_hours: int = 48,
    ) -> list[any]:
        candidates = []
        for e in all_events:
            if getattr(e, "primary_category", "") != category:
                continue
            last_seen = getattr(e, "last_seen_at", now)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=UTC)
            if now.tzinfo is None:
                now = now.replace(tzinfo=UTC)
            if (now - last_seen).total_seconds() > window_hours * 3600:
                continue
            candidates.append(e)
        return candidates

    async def find_best_cluster(
        self,
        doc_title: str,
        doc_summary: str,
        doc_category: str,
        doc_entities: list[ExtractedEntity],
        doc_time: datetime,
        candidate_events: list[dict],  # list of candidate event dicts from DB query
    ) -> ClusterMatch | None:
        """
        Narrow candidates and find best event cluster.
        Returns ClusterMatch if similarity >= POSSIBLE_EVENT_THRESHOLD, else None.
        """
        if not candidate_events:
            return None

        doc_entity_keys = [e.normalized_name for e in doc_entities]
        doc_embed_text = f"{doc_title}. {doc_summary or ''}"
        doc_vector = await self.embedding_provider.embed_text(doc_embed_text)

        best_match: ClusterMatch | None = None
        highest_score = 0.0

        for cand in candidate_events:
            cand_category = cand.get("primary_category", "")
            cand_entities = cand.get("entity_keys", [])
            entity_overlap = compute_entity_overlap(doc_entity_keys, cand_entities)

            # Category compatibility check
            related_clusters = [
                {"Technology", "Artificial Intelligence", "Business", "Automotive", "Science"},
                {"Entertainment", "Gaming"},
                {"Finance", "Business"},
            ]
            is_related = (cand_category == doc_category) or any(
                cand_category in group and doc_category in group for group in related_clusters
            )

            if not is_related and entity_overlap < 0.33:
                continue

            # 2. Time proximity
            event_last_seen = cand.get("last_seen_at") or cand.get("first_seen_at") or doc_time
            time_prox = compute_time_proximity(
                doc_time,
                event_last_seen,
                self.settings.EVENT_CLUSTER_WINDOW_HOURS,
            )

            # 3. Headline similarity
            cand_title = cand.get("canonical_title", "")
            title_sim = compute_headline_similarity(doc_title, cand_title)

            # 4. Semantic similarity
            cand_vector = cand.get("embedding_vector")
            if not cand_vector:
                cand_embed_text = f"{cand_title}. {cand.get('summary', '')}"
                cand_vector = await self.embedding_provider.embed_text(cand_embed_text)
            semantic_sim = max(0.0, cosine_similarity(doc_vector, cand_vector))

            # Composite weighted similarity
            # If same company but zero headline and zero semantic similarity, don't cluster!
            if entity_overlap > 0 and title_sim < 0.12 and semantic_sim < 0.20:
                # Same company, completely different event!
                total_sim = 0.20
            else:
                cat_bonus = 0.05 if (cand_category == doc_category) else 0.0
                total_sim = (
                    (0.35 * entity_overlap)
                    + (0.35 * title_sim)
                    + (0.20 * semantic_sim)
                    + (0.10 * time_prox)
                    + cat_bonus
                )

            if total_sim > highest_score:
                highest_score = total_sim
                best_match = ClusterMatch(
                    event_id=str(cand["id"]),
                    similarity_score=round(total_sim, 4),
                    entity_overlap=round(entity_overlap, 4),
                    title_similarity=round(title_sim, 4),
                    semantic_similarity=round(semantic_sim, 4),
                    time_proximity=round(time_prox, 4),
                    matched_title=cand_title,
                )

        if best_match and best_match.similarity_score >= self.settings.POSSIBLE_EVENT_THRESHOLD:
            return best_match

        return None
