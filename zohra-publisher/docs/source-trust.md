# Zohra Source Trust & Intelligence System

## 1. Core Principle: Popularity ≠ Credibility

A Reddit thread or viral tweet may be an outstanding **trend detector** (high freshness, high signal value) while being a weak factual authority. Conversely, an official government regulatory filing or scientific journal is a primary factual authority (high authority, high reliability) but may publish hours or days after initial buzz.

Zohra models these dimensions independently:

```text
AUTHORITY:     Institutional weight, editorial standards, official status (0–100)
RELIABILITY:   Historical accuracy rate, absence of retractions/fabrications (0–100)
FRESHNESS:     Speed of initial reporting relative to real-world occurrence (0–100)
SIGNAL VALUE:  Early-warning sensitivity for emerging public curiosity (0–100)
```

## 2. Source Tiers

| Tier | Category | Examples | Role in System |
|---|---|---|---|
| **Tier 1** | Primary / Official | Government agencies, regulatory filings, company press rooms, academic preprints | Ultimate factual verification benchmark |
| **Tier 2** | Major Professional | Reuters, BBC, AP, Bloomberg, MIT Tech Review | High-credibility multi-source reporting |
| **Tier 3** | Industry Specialist | Ars Technica, The Verge, TechCrunch, Tom's Hardware | Deep niche coverage and timely technical context |
| **Tier 4** | Community / Discussion | Hacker News, Reddit, GitHub Discussions | Early trend and sentiment detection |
| **Tier 5** | Unverified / Aggregators | Content farms, unknown blogs, scraping syndicates | Quarantined; high scrutiny required |

## 3. Autonomous Escalation Protection

**Rule**: An AI or automated system CANNOT autonomously promote an unknown or Tier 4/5 source into a Tier 1 or Tier 2 source purely based on high publishing frequency or viral popularity.

Source tier adjustments are administrative operations tracked with complete provenance in the immutable audit log (`audit_logs`).

## 4. Source Circuit Breaker

To prevent cascading resource consumption when external feeds fail or throttle requests:

```text
       ┌──────────┐
       │  CLOSED  │ (Normal operations)
       └────┬─────┘
            │  5 consecutive failures
            ▼
       ┌──────────┐
       │   OPEN   │ (Fast-fails; requests suspended for 15 minutes)
       └────┬─────┘
            │  Cooldown elapsed
            ▼
       ┌──────────┐
       │ HALF-OPEN│ (Allows single probe request)
       └────┬─────┘
            ├─ Success → CLOSED (reset failure counter)
            └─ Failure → OPEN (reset cooldown timer)
```
