# ZOHRA AUTONOMOUS PUBLISHING OS — FINAL PRODUCTION ARCHITECTURE

## 1. System Overview

Zohra is an autonomous, observable, controllable, policy-governed publishing intelligence engine. It continuously discovers trends, researches claims with verifiable citations, drafts grounded articles, verifies factual statements, optimizes SEO metadata, publishes to WordPress, ingests Google Search Console performance metrics, runs controlled content refresh experiments, and records bounded strategy memory.

Surrounding the complete loop is the **Command Center**, providing emergency pause, multi-site isolation, role-based access control, encrypted credential storage, spending governance, and disaster recovery.

---

## 2. Complete End-to-End Workflow

```text
WORLD / INTERNET (Feeds, News, SERP, Research Sources)
        ↓
[PART 2: DISCOVERY ENGINE] (Events, Snapshots, Clustering)
        ↓
[PART 3: TREND INTELLIGENCE] (Velocity, Acceleration, Novelty, Diversity)
        ↓
[PART 4: OPPORTUNITY & KEYWORDS] (Search Intent, Demand, Cannibalization Risk)
        ↓
[PART 5: RESEARCH & CLAIMS ENGINE] (Evidence Graph, Questions, Authority Tiers)
        ↓
[PART 6: EDITORIAL & VERIFICATION] (Grounding, Claims Audit, Editorial Scoring)
        ↓
[PART 7: WORDPRESS PUBLISHING] (Idempotent WP REST, Schemas, Internal Links)
        ↓
[PART 8: SEARCH CONSOLE ANALYTICS] (Clicks, Impressions, CTR, Position, Decays)
        ↓
[PART 9: LEARNING & OPTIMIZATION] (Refresh Candidates, Experiments, Strategy Memory)
        ↓
[PART 10: PRODUCTION COMMAND CENTER & INTEGRATION]
   ├── Global & Per-Site Autonomy Control (Emergency Pause Kill-Switch)
   ├── Role-Based Access Control (SUPER_ADMIN, ADMIN, EDITOR, ANALYST, VIEWER)
   ├── SecretProvider (Authenticated AES-128 / Fernet, Zero-Leak Masking)
   ├── AlertManager & Notifications (Deduplication, Telegram, Email, Webhook)
   ├── CostGovernor (NORMAL, ECONOMY, ESSENTIAL_ONLY, PAUSED)
   ├── Transactional Outbox (Guaranteed event dispatching)
   ├── BackupManager (Encrypted backups, SHA-256 checksums, sandbox restore)
   └── Full Article Lineage & Dead-Letter Job Recovery
```

---

## 3. High-Level Component Topology

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      ZOHRA COMMAND CENTER (UI)                         │
│   Next.js / TypeScript / React / Tailwind CSS / Embedded Web Console   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS (Strict Security Headers)
┌───────────────────────────────────▼────────────────────────────────────┐
│                    EDGE REVERSE PROXY (Caddy / Nginx)                  │
│             Rate Limiting, TLS Termination, CSP, Anti-Bruteforce       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                      ZOHRA CORE API (FastAPI)                          │
│            RBAC, Lifespan Hooks, Pre-Publish Gates, Lineage            │
└──────────┬────────────────────────┬──────────────────────┬─────────────┘
           │                        │                      │
┌──────────▼──────────┐  ┌──────────▼──────────┐ ┌─────────▼─────────────┐
│    PostgreSQL 16    │  │       Redis 7       │ │     Object Storage    │
│  Durable DB Store   │  │ Message Broker, AOF │ │ Local & S3 Compatible │
│  Transactional      │  │ Locks, Rate Limits  │ │ Media, Backups,       │
│  Outbox, Audit      │  │ Distributed Cache   │ │ Large Reports         │
└─────────────────────┘  └──────────┬──────────┘ └───────────────────────┘
                                    │
    ┌───────────────────────────────┴───────────────────────────────┐
    │                                                               │
┌───▼──────────────────────────┐                        ┌───────────▼───────────┐
│     CELERY WORKER POOLS      │                        │      CELERY BEAT      │
│ - worker-general (discovery) │                        │ Scheduled Task        │
│ - worker-publishing (WP sync)│                        │ Registry, Recurring   │
│ - worker-analytics (GSC sync)│                        │ Ingestion Cron        │
│ - worker-optimization (ML)   │                        └───────────────────────┘
└──────────────────────────────┘
```

---

## 4. Multi-Tenant Site Isolation & Security Boundaries

1. **Deterministic Site Scoping**: Every database query scoped to articles, keywords, opportunities, or credentials requires a validated `site_id`.
2. **Role Hierarchy**:
   - `SUPER_ADMIN`: Universal system, billing, and infrastructure management.
   - `ADMIN`: Assigned site administration, budget reviews, and workflow approvals.
   - `EDITOR`: Content creation, draft reviews, manual verification overrides.
   - `ANALYST`: Read-only access to search analytics, experiments, and performance reports.
   - `VIEWER`: Strictly read-only viewer.
3. **Secret Security**: No plain secrets in database records. All credentials stored via `SecretProvider` using authenticated encryption with unique per-secret derivation salts. Plaintext secrets are never returned over HTTP.
4. **Emergency Stop (Kill Switch)**: Pauses all autonomous actions immediately across the entire cluster without interrupting running DB transactions or corrupting WordPress posts.
