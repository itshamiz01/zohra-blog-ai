# SERP Analysis & Feature Extraction

## Overview

The SERP subsystem executes queries via `SERPProvider` (with built-in `MockSERPProvider` and Redis caching) to inspect ranking landscapes.

---

## Strategic Features Detected

1. **Featured Snippets**: Indicates that search engines seek concise, direct answers (definitions, steps, comparison tables).
2. **Video Carousel**: Dominance of YouTube/video results indicates visual workflow preference.
3. **Forum Prevalence**: Multiple Reddit, Quora, or StackOverflow rankings in the top 5 indicates **unanswered practical questions** and weak formal editorial coverage, presenting a prime opportunity for a structured article.
4. **People Also Ask (PAA)**: Extracted and normalized into `discovered_questions` to guide research and FAQ schemas.
5. **Official Domain Dominance**: If an official portal dominates the top 3 positions for navigational queries, Zohra down-ranks the opportunity to avoid fighting unwinnable navigational traffic.

---

## Caching & Retention

- SERP results are cached in Redis using `sha256(query:country:language)` with configurable TTLs (e.g. 24 hours for breaking queries, 72 hours for evergreen queries).
- Historical snapshots are retained in PostgreSQL (`serp_snapshots` and `serp_results`) and cleaned up by Celery Beat tasks after retention expiry.
