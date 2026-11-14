# Zohra Content Opportunity Intelligence Engine (Part 3)

## Overview

The **Content Opportunity Intelligence Engine** transforms trending events and discovery signals from Part 2 into evidence-backed, intent-aligned, and business-viable **Content Opportunities** for publication.

While Part 2 answers *"What is happening in the world?"*, Part 3 answers:
> **"What should our website consider covering, from which search angle, for which audience, and why?"**

---

## Architectural Pipeline

```text
PART 2 QUALIFIED EVENT
          ↓
STAGE 1: SITE RELEVANCE PRE-FILTER (Cheap early exit)
          ↓
STAGE 2: KEYWORD DISCOVERY & CONTEXT-AWARE EXPANSION
          ↓
STAGE 3: QUERY NORMALIZATION & SEARCH INTENT CLASSIFICATION
          ↓
STAGE 4: KEYWORD CLUSTERING (Intent-Based & SERP Overlap)
          ↓
STAGE 5: SERP RETRIEVAL & FEATURE ANALYSIS (Cached in Redis)
          ↓
STAGE 6: COMPETITION & CONTENT GAP ANALYSIS (Zohra Competition Score)
          ↓
STAGE 7: EXISTING CONTENT CHECK & CANNIBALIZATION PREVENTER
          ↓
STAGE 8: ANGLE GENERATION & AUDIENCE FIT MAPPING
          ↓
STAGE 9: MULTI-PROFILE OPPORTUNITY SCORING & GATING
          ↓
STAGE 10: STANDARDIZED CONTENT OPPORTUNITY PACKAGE (Part 4 Handoff)
```

---

## Core Guiding Principles

1. **Trending Event $\neq$ Search Opportunity**: A viral celebrity rumor with a trend score of 98 will be immediately rejected on an AI automation site. Conversely, a technical model release with low search history creates valuable long-tail queries.
2. **Strict Provenance & Anti-Hallucination**: External SEO metrics (`search_volume`, `cpc`, `keyword_difficulty`) are strictly stored as `NULL` if not verified by an actual provider. The engine never fabricates numbers or converts missing data to 0.
3. **Information Gain over Word Count**: "We can write longer" is not an SEO strategy. The engine identifies specific structural dimensions missing in top SERPs (pricing transparency, beginner implementation workflows, unaddressed limitations, regional availability, comparison matrices).
4. **Intent-Driven Anti-Cannibalization**: If existing content on the site targets the identical search intent, the engine recommends `UPDATE` or `EXPAND`, reserving `CREATE` for genuinely distinct search intents.
