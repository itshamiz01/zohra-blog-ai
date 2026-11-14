# Keyword Intelligence & Normalization

## Overview

The Keyword Intelligence module discovers search queries from event entities, expands context-aware query families, normalizes tokens while preserving distinct intents, and scores internal demand without fabricating external search volume metrics.

---

## Provenance Tracking & Missing Data Principle

In accordance with strict anti-hallucination rules:
- `search_volume`: `int | None` (defaults to `NULL`)
- `cpc`: `float | None` (defaults to `NULL`)
- `competition_metric`: `float | None` (defaults to `NULL`)

If an external provider (DataForSEO, Semrush, Ahrefs, Google Keyword Planner) was not queried, these values remain `None` (`NULL` in PostgreSQL).
**No data $\neq$ Zero.** A newly launched AI model launched 10 minutes ago has 0 historical volume in keyword databases, but rapid emerging demand. Converting missing volume to 0 would wrongfully reject emerging opportunities.

---

## Query Normalization Rules

`KeywordExpander.normalize(query)`:
1. Normalizes Unicode characters via NFKC.
2. Strips redundant whitespace and lowercases.
3. Preserves punctuation that defines meaning:
   - Version numbers: `Python 3.12`, `GPT-4`
   - Language tokens: `C++`, `.NET`
   - Comparative markers: `vs`
4. Cleans generic plural noise for specific dictionary terms while strictly keeping intent distinction:
   - `ChatGPT pricing` and `ChatGPT API pricing` remain **strictly distinct queries**.
