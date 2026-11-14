"""
Zohra — Keyword Clustering Engine (Intent-Based & SERP Overlap).

Groups search queries by search intent and entity overlap, reinforced by
SERP ranking URL intersection when SERP data is available.
Prevents creating fragmented or cannibalizing content.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants import SearchIntent
from app.opportunity.keywords.expander import KeywordCandidate


@dataclass
class ClusterMember:
    keyword: KeywordCandidate
    similarity_score: float
    is_primary: bool = False


@dataclass
class KeywordClusterResult:
    canonical_topic: str
    primary_keyword: str
    primary_intent: SearchIntent
    language: str
    country: str
    members: list[ClusterMember] = field(default_factory=list)
    aggregate_demand_score: float = 50.0
    commercial_value_score: float = 0.0
    freshness_score: float = 50.0
    cluster_confidence: float = 1.0


class KeywordClusteringEngine:
    """Clusters keyword candidates into cohesive intent groups."""

    def __init__(self, serp_overlap_threshold: float = 0.40) -> None:
        self.serp_overlap_threshold = serp_overlap_threshold

    def calculate_token_similarity(self, q1: str, q2: str) -> float:
        """Calculates token similarity combining Jaccard and containment on content tokens."""
        stopwords = {"how", "to", "use", "for", "and", "in", "is", "a", "the", "what", "does", "step", "by", "of"}
        t1 = {w for w in q1.lower().split() if w not in stopwords}
        t2 = {w for w in q2.lower().split() if w not in stopwords}
        if not t1 or not t2:
            t1 = set(q1.lower().split())
            t2 = set(q2.lower().split())
        if not t1 or not t2:
            return 0.0
        intersection = len(t1 & t2)
        jaccard = intersection / len(t1 | t2)
        containment = intersection / min(len(t1), len(t2))
        return max(jaccard, containment * 0.75)

    def calculate_serp_overlap(self, urls1: list[str], urls2: list[str]) -> float:
        """
        Calculates Jaccard overlap between ranking SERP URLs.
        If 4 or more out of 10 URLs overlap, queries belong to the same intent cluster.
        """
        if not urls1 or not urls2:
            return 0.0
        # Normalize URLs (strip query params and trailing slash)
        s1 = {u.split("?")[0].rstrip("/") for u in urls1[:10]}
        s2 = {u.split("?")[0].rstrip("/") for u in urls2[:10]}
        intersection = len(s1 & s2)
        union = len(s1 | s2)
        return intersection / union if union > 0 else 0.0

    def cluster(
        self,
        keywords: list[KeywordCandidate],
        serp_data: dict[str, list[str]] | None = None,  # query -> list of ranking URLs
        language: str = "en",
        country: str = "global",
    ) -> list[KeywordClusterResult]:
        """
        Groups keywords into clusters by intent, token overlap, and SERP overlap.
        Keywords with distinct intents (e.g. tutorial vs pricing) are strictly separated.
        """
        if not keywords:
            return []

        # Sort keywords by internal search demand descending so strongest query becomes primary
        sorted_kws = sorted(keywords, key=lambda k: k.search_demand_score, reverse=True)

        clusters: list[KeywordClusterResult] = []

        for kw in sorted_kws:
            assigned = False
            kw_serp_urls = serp_data.get(kw.normalized_keyword, []) if serp_data else []

            # Check fit against existing clusters
            for cluster in clusters:
                # Rule 1: PRIMARY INTENT MUST MATCH (or be highly compatible like informational + tutorial)
                intent_compatible = (
                    cluster.primary_intent == kw.intent
                    or (cluster.primary_intent == SearchIntent.INFORMATIONAL and kw.intent == SearchIntent.TUTORIAL)
                    or (cluster.primary_intent == SearchIntent.TUTORIAL and kw.intent == SearchIntent.INFORMATIONAL)
                )
                if not intent_compatible:
                    continue

                # Rule 2: SERP overlap if data exists
                if kw_serp_urls:
                    cluster_primary_urls = serp_data.get(cluster.primary_keyword, []) if serp_data else []
                    if cluster_primary_urls:
                        overlap = self.calculate_serp_overlap(kw_serp_urls, cluster_primary_urls)
                        if overlap >= self.serp_overlap_threshold:
                            cluster.members.append(ClusterMember(keyword=kw, similarity_score=round(overlap, 2), is_primary=False))
                            assigned = True
                            break

                # Rule 3: Semantic token similarity
                sim = self.calculate_token_similarity(cluster.primary_keyword, kw.normalized_keyword)
                # If they share core entity and significant tokens (>= 0.35 similarity)
                if sim >= 0.35:
                    cluster.members.append(ClusterMember(keyword=kw, similarity_score=round(sim, 2), is_primary=False))
                    assigned = True
                    break

            if not assigned:
                # Create new cluster with this keyword as primary
                new_cluster = KeywordClusterResult(
                    canonical_topic=kw.keyword,
                    primary_keyword=kw.normalized_keyword,
                    primary_intent=kw.intent,
                    language=language,
                    country=country,
                    members=[ClusterMember(keyword=kw, similarity_score=1.0, is_primary=True)],
                    aggregate_demand_score=kw.search_demand_score,
                    commercial_value_score=kw.commercial_value_score,
                    freshness_score=80.0 if kw.freshness_sensitivity == "fast_decay" else 50.0,
                    cluster_confidence=kw.intent_confidence,
                )
                clusters.append(new_cluster)

        # Recalculate cluster aggregate metrics
        for cluster in clusters:
            if cluster.members:
                avg_demand = sum(m.keyword.search_demand_score for m in cluster.members) / len(cluster.members)
                max_commercial = max(m.keyword.commercial_value_score for m in cluster.members)
                cluster.aggregate_demand_score = round(avg_demand, 1)
                cluster.commercial_value_score = round(max_commercial, 1)

        # Sort clusters by aggregate demand score descending
        clusters.sort(key=lambda c: c.aggregate_demand_score, reverse=True)
        return clusters
