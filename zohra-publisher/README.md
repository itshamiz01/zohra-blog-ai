# ZOHRA AUTONOMOUS PUBLISHING OS

**Production-grade autonomous intelligence, research, editorial verification, multi-site publishing, SEO analytics, learning & command center operating system.**

---

## 1. System Architecture (All 10 Stages Completed)

Zohra operates a continuous, observable, policy-controlled autonomous publishing lifecycle:

```text
WORLD / INTERNET (SERP, News, RSS, Academic Sources)
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
[PART 10: PRODUCTION COMMAND CENTER & FULL SYSTEM INTEGRATION]
   ├── Command Center UI: Next.js + Tailwind CSS & Embedded Console (/console)
   ├── Global & Site Autonomy: Emergency Kill-Switch (/autonomy/pause, /autonomy/resume)
   ├── Multi-Tenant RBAC: SUPER_ADMIN, ADMIN, EDITOR, ANALYST, VIEWER & Site Roles
   ├── Encrypted Credentials: Authenticated AES-128 / Fernet with Zero-Leak Masking
   ├── Cost Governor: Real-time spend limits, degradation modes (NORMAL, ECONOMY, ESSENTIAL_ONLY)
   ├── AlertManager: Deduplication keys, cooldown windows, Telegram & Webhook routing
   ├── Disaster Recovery: Checksummed, encrypted backups with sandbox restore validation
   └── Transactional Outbox: Guaranteed domain event publishing across all subsystems
```

---

## 2. Command Center Interfaces

Zohra provides two complementary Command Center interfaces:
1. **Next.js Production Web App** (`/frontend`): Full-featured TypeScript/React desktop and mobile-optimized dashboard.
2. **Embedded Web Console** (`/console` & `/`): Zero-build single-page application served directly by FastAPI for immediate operational control, metric monitoring, and kill-switch triggering out of the box.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)

### Setup

```bash
# Clone
git clone <repository>
cd zohra-publisher

# Create environment file
cp .env.example .env
# Edit .env — set SECRET_KEY and ADMIN_PASSWORD_HASH

# Generate a password hash:
python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your-password'))"

# Generate a secret key:
python -c "import secrets; print(secrets.token_urlsafe(64))"

# Start all services
docker compose up -d

# Run migrations
docker compose exec api alembic upgrade head

# Verify
curl http://localhost:8000/health
```

### Local Development (without Docker)

```bash
# Install dependencies
pip install -e ".[dev]"

# Start PostgreSQL and Redis (ensure they're running)
# Update .env with local connection strings

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Start Celery Beat
celery -A app.workers.celery_app beat --loglevel=info
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string |
| `SECRET_KEY` | ✅ | JWT signing key |
| `ADMIN_PASSWORD_HASH` | ✅ | bcrypt hash of admin password |
| `HEAVENLY_SITE_URL` | For Heavenly | Publisher base URL |
| `HEAVENLY_API_TOKEN` | For Heavenly | Bearer token for the publisher API |
| `HEAVENLY_UPLOAD_IMAGES` | No | Upload covers to the publisher (default `true`) |
| `ARTICLE_IMAGE_GUARANTEE_IMAGE` | No | Never publish without a cover (default `true`) |
| `REDIS_URL` | No | Redis connection (default: localhost:6379) |
| `APP_ENV` | No | `development` / `testing` / `production` |
| `LLM_DAILY_BUDGET` | No | Daily AI spend limit in USD |
| `AUTONOMY_ENABLED` | No | Master autonomy kill switch |

See `.env.example` for the complete list.

---

## Article Cover Images (Heavenly Insights)

**Invariant: every published article carries a cover image.**

The Heavenly Insights post schema exposes exactly `cover_image_url` and
`cover_image_alt`. Its image pipeline is:

```text
ImageProvider.generate_article_featured_image()   -> WebP bytes (+ local /storage path)
        ↓
POST {HEAVENLY_SITE_URL}/api/images               multipart/form-data, field name "file"
        ↓  201 {"id", "url": "https://…/api/images/<id>", "mime", "size"}
POST {HEAVENLY_SITE_URL}/api/posts                cover_image_url=<that absolute url>
                                                  cover_image_alt=<alt text>
        ↓
article page renders  <img src="<cover_image_url>">  verbatim
```

Rules enforced by the code:

1. **Only public absolute URLs are published.** A relative app path such as
   `/storage/media/articles/x.webp` resolves against the *blog's* domain, where
   no such file exists, and renders as a broken image. `ensure_public_cover_url()`
   uploads the bytes instead of ever publishing such a path.
2. **The legacy `image_url` / `featured_image` payload keys are not sent.**
   The API silently discards them, which is why covers used to disappear.
3. **Uploaded images only become anonymously fetchable once the post that
   references them is published.** Draft and orphan images return 404.
   `verify_cover_image_public()` checks this *after* publishing.
4. **Generation never returns nothing.** With `ARTICLE_IMAGE_GUARANTEE_IMAGE=true`
   a failed generative attempt degrades to a procedural cover, and then to a
   deterministic PIL placeholder, so bytes always exist.
5. **Publication is blocked rather than imageless.** If no publishable cover can
   be produced, the cycle fails and retries instead of posting without an image.

### Repairing articles that are already missing covers

```bash
# Show what would be fixed (no writes)
python scripts/backfill_covers.py

# Also re-check that existing covers still resolve
python scripts/backfill_covers.py --verify-existing

# Repair every article missing a cover
python scripts/backfill_covers.py --apply
python scripts/backfill_covers.py --apply --limit 5
python scripts/backfill_covers.py --apply --slug some-article-slug
```

The backfill re-sends each article's stored body verbatim (the API's formatter is
byte-idempotent on existing bodies) and preserves title, slug, category, excerpt
and status, so article text is never altered.


## API Endpoints

### Health (no auth)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Full health status |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |

### Admin Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/admin/login` | Basic Auth → JWT token |
| GET | `/api/v1/admin/me` | Verify token |

### System (admin required)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/system/status` | Full system status |
| POST | `/api/v1/system/jobs` | Create job |
| GET | `/api/v1/system/jobs/{id}` | Get job |
| PUT | `/api/v1/system/jobs/{id}/status` | Transition job status |
| GET | `/api/v1/system/costs` | AI cost summary |
| POST | `/api/v1/system/worker/test` | Test Celery worker |

## Database Tables

| Table | Purpose |
|-------|---------|
| `system_settings` | Runtime key-value configuration |
| `agent_runs` | AI agent execution records |
| `model_usage` | Per-call LLM token/cost tracking |
| `system_errors` | Persistent error log |
| `audit_logs` | Who-changed-what audit trail |
| `jobs` | Background job queue |

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

Tests use in-memory SQLite — no PostgreSQL or Redis required.

## Development Commands

```bash
# Start API with reload
uvicorn app.main:app --reload

# Start worker
celery -A app.workers.celery_app worker --loglevel=info

# Start scheduler
celery -A app.workers.celery_app beat --loglevel=info

# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Run tests
pytest -v

# Run tests with coverage
pytest --cov=app

# Type check
mypy app/

# Lint
ruff check app/

# Format
ruff format app/
```

## Security Notes

- Secrets loaded exclusively from environment variables
- Passwords hashed with bcrypt
- JWT tokens for API authentication
- Admin endpoints protected — reject anonymous access
- CORS origins configurable (not wildcarded in production)
- Sensitive data redacted from logs
- Stack traces never exposed in API responses
- Untrusted external content is architecturally separated from system instructions

## License

Proprietary — Zohra Project
