# Zohra Autonomous Publishing Engine — Part 2: Global Discovery Engine

## 1. Overview & Architecture

The Global Discovery & Trend Intelligence Engine operates autonomously to answer:
> **What is happening right now, what appears to be gaining attention, how reliable is the underlying information, and which events deserve deeper SEO/opportunity analysis?**

It deliberately stops short of editorial and content generation responsibilities (reserved for Part 3).

```text
       ┌──────────────────────────────┐
       │   INTERNET / DATA SOURCES    │
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │       SOURCE REGISTRY        │ (Tiers 1-5, Circuit Breakers, Adaptor Polling)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │   SSRF-PROTECTED FETCHING    │ (Hop-by-hop IP & Private Subnet Validation)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │  CONTENT SANITIZATION & FIREWALL (Defuses prompt injections & dangerous HTML)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │ MULTI-LEVEL DEDUPLICATION    │ (Canonical URL, External ID, Content Hash, SimHash)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │  ENTITY & TOPIC EXTRACTION   │ (Aliases, Taxonomy, Risk & Verification Detection)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │   HYBRID EVENT CLUSTERING    │ (Time Window → Category → Entities → Cosine Similarity)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │  VELOCITY & TREND SCORING    │ (Windowed Acceleration, Momentum, Source Diversity)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │       EVENT LIFECYCLE        │ (Emerging → Active → Accelerating → Peaking → etc.)
       └──────────────┬───────────────┘
                      │
                      ▼
       ┌──────────────────────────────┐
       │   PART 3 HANDOFF CONTRACT    │ (Clean JSON Qualified Event Payload)
       └──────────────────────────────┘
```

## 2. Pipeline Execution Flow

1. **Source Registry & Adaptive Polling**: Sources are selected according to their polling interval, priority, and circuit breaker status (`CLOSED`, `OPEN`, `HALF_OPEN`).
2. **SSRF-Safe Ingestion**: `SSRFValidator` resolves target DNS hostnames and verifies every intermediate redirect against private subnets (RFC 1918, RFC 3927, loopback, cloud metadata `169.254.169.254`).
3. **Sanitization**: Raw HTML is stripped of scripts, iframes, styles, malformed Unicode, and control characters.
4. **Prompt-Injection Firewall**: Text is analyzed for jailbreak heuristics and wrapped in boundary delimiters (`wrap_untrusted_for_prompt`) before passing to any downstream LLM component.
5. **Deduplication**:
   - **Level 1**: Canonical URL normalization (stripping tracking query parameters).
   - **Level 2**: External item ID matching.
   - **Level 3**: Content hash (SHA-256 of normalized body and title).
   - **Level 4**: Near-duplicate detection via 64-bit SimHash (Hamming distance $\le 3$).
6. **Entity & Topic Extraction**: Named entities (Organizations, People, Products, Locations, etc.) are extracted and normalized to canonical aliases. Topics are classified against a 10-domain taxonomy.
7. **Risk & Claim Profiling**: Evaluates 11 sensitive risk flags (crime, health, legal, allegations) and tags person-related claims with `HIGH_VERIFICATION_REQUIRED`.
8. **Event Clustering**: Clusters new reports into existing events within a configurable candidate window (default 48 hours) using category match, entity Jaccard overlap, title word similarity, and semantic cosine similarity.
9. **Trend Scoring**: Computes velocity across 15m, 1h, 6h, 24h windows, momentum trajectory, source diversity, freshness decay, and factual confidence.
10. **Handoff Generation**: Emits structured `QualifiedEventHandoff` payload for Part 3 Content Opportunity Analysis when `trend_score >= 60`, `confidence_score >= 60`, and spam probability is low.
