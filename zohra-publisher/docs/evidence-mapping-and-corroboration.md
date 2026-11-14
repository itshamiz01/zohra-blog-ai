# Evidence Mapping, Independence Groups & Corroboration

## Overview

Part 4 rejects simplistic source counting. Ten websites repeating the identical wire press release do NOT equal ten independent confirmations.

---

## 1. Independence Groups

The `SourceIndependenceEngine` clusters sources into `independence_group_id`s using:
1. **Explicit Attribution**: Regex detection of wire services (PR Newswire, BusinessWire) and secondary attribution phrases ("according to Reuters", "citing TechCrunch").
2. **4-Gram Shingle Similarity**: Pairwise Jaccard overlap on text fingerprints. Sources sharing $\ge 45\%$ shingle similarity are grouped into the same independence cluster.
3. **Circular Citation Detection**: Detects cycles ($A \rightarrow B \rightarrow C \rightarrow A$) where publications echo each other without original reporting.

**Rule**: When calculating corroboration, all sources sharing an `independence_group_id` count as **1** independent voice.

---

## 2. Verification Levels

Every atomic claim is assigned an explicit verification level from 0 to 5:

| Level | Definition | Minimum Criteria | Status |
|---|---|---|---|
| **0** | No Evidence | 0 matching sources | `unverified` / `unknown` |
| **1** | Single Weak/Moderate Source | 1 Tier 3 or 4 source (score $< 75$) | `weakly_supported` |
| **2** | Single Strong Source | 1 Tier 1/2 source or primary doc (score $\ge 75$) | `supported` |
| **3** | Multiple Independent Sources | $\ge 2$ independent source groups | `supported` |
| **4** | Primary Source + Independent Secondary | 1 primary source + $\ge 1$ independent secondary group | `strongly_supported` |
| **5** | Exceptionally Strong Multi-Source | 1 primary source + $\ge 2$ independent secondary groups | `strongly_supported` |

---

## 3. Support Direction

- `supports`: Document confirms the claim proposition with $\ge 65\%$ token overlap and no contradiction.
- `partially_supports`: Document supports a subset of qualifiers with $35\%–64\%$ overlap.
- `contradicts`: Document negates the claim or provides conflicting numeric/date values with high semantic overlap.
- `context_only`: Tangential or background mention without direct assertion.
