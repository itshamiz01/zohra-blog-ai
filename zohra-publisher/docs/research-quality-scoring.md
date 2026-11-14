# Research Quality & Confidence Scoring Formula

## Overview

The `ResearchQualityScorer` evaluates the rigor, completeness, and evidence density of completed research projects.

---

## Implemented Formula & Weights

$$\text{Positive Quality Score} = \sum_{i} W_i \times S_i$$

| Metric | Implemented Weight | Rationale |
|---|---|---|
| **Coverage Score** | 20% | Priority-weighted answer rate across all research questions |
| **Critical Claim Coverage** | 20% | Answer rate for critical questions (pricing, core workflow, specs) |
| **Source Quality Score** | 15% | Average authority, reliability, and tier distribution |
| **Primary Source Coverage** | 15% | Percentage of key claims anchored in primary documentation |
| **Corroboration Score** | 10% | Percentage of claims supported by $\ge 2$ independent groups |
| **Freshness Score** | 10% | Temporal currency and decay-adjusted evidence age |
| **Contradiction Resolution** | 5% | Resolution status of detected factual conflicts |
| **Evidence Specificity** | 5% | Directness of quotes and data table references |
| **Total Positive Score** | **100%** | |

---

## Penalties

- **Unresolved Critical Contradictions**: Deducts up to 25 points ($15$ points per unresolved critical conflict).
- **Missing Critical Sources**: Deducts 15 points if critical questions lack primary/secondary evidence.
- **Stale Critical Evidence**: Deducts 10 points if time-sensitive claims rely on evidence $> 12$ months old.

$$\text{Final Research Quality Score} = \max(0, \min(100, \text{Positive Score} - \text{Total Penalties}))$$

---

## Quality Gates

- `0–49`: **FAIL** — Research abandoned or rejected.
- `50–64`: **INSUFFICIENT** — Major holes in critical facts.
- `65–74`: **MORE_RESEARCH** — Triggers gap-driven query expansion.
- `75–84`: **PASS** — Standard publication threshold.
- `85–94`: **STRONG** — High conviction across primary and secondary sources.
- `95–100`: **EXCEPTIONAL** — Flawless multi-source primary verification.

### High-Risk / YMYL Policy
For medical, legal, or financial topics, passing threshold increases to **90.0**. Any unresolved critical contradictions automatically require human review before proceeding to Part 5.
