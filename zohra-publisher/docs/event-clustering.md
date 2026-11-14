# Zohra Hybrid Event Clustering Engine

## 1. The Scaling Problem

Comparing every newly discovered document against every historical document is an $O(N^2)$ operation that fails catastrophically at scale.

Zohra avoids this by implementing **staged candidate narrowing**:

```text
Incoming Document
       │
       ▼
[Stage 1: Temporal Window]  ─── Discard events older than 48 hours
       │
       ▼
[Stage 2: Category Filter]  ─── Discard events in completely disjoint categories
       │
       ▼
[Stage 3: Entity Overlap]   ─── Score shared canonical named entities (Jaccard)
       │
       ▼
[Stage 4: Title Similarity] ─── Word overlap / Levenshtein word ratio
       │
       ▼
[Stage 5: Cosine Similarity]─── 64-dimensional L2-normalized embedding similarity
       │
       ▼
Weighted Hybrid Score >= 0.72  ─── Attach to Event Cluster
Weighted Hybrid Score < 0.72   ─── Create New Event Cluster
```

## 2. Similarity Formula & Weights

```python
composite_similarity = (
    0.35 * semantic_cosine_similarity
    + 0.30 * headline_token_similarity
    + 0.25 * entity_jaccard_overlap
    + 0.10 * temporal_proximity_factor
)
```

- **Candidate Threshold**: If `composite_similarity >= 0.72`, the document is attached to the existing event.
- **Ambiguity Range**: If `0.60 <= composite_similarity < 0.72`, the document is evaluated for secondary signals or flagged for adjudication.
- **Disjoint Events with Shared Entity**: If two articles discuss the same company doing completely different things (e.g. "Apple launches M4" vs "Apple sued in antitrust lawsuit"), entity overlap is high (~0.5) but title and semantic similarities are low (~0.2), producing a composite score around 0.35 — correctly creating separate event clusters.

## 3. Administrative Cluster Overrides

- **Merge Events (`POST /api/v1/events/merge`)**: Combines two clusters that later proved to be the same event. All documents are reassigned to the target event, metrics are recomputed, the source event is marked `MERGED`, and an audit log records the action.
- **Split Event (`POST /api/v1/events/{id}/split`)**: Moves a set of selected documents into a new standalone event cluster when articles were mistakenly lumped together. Full document provenance is preserved.
