# Development Guide

## Setup

```bash
# Clone and enter the project
cd zohra-publisher

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install with dev dependencies
pip install -e ".[dev]"

# Copy env file
cp .env.example .env
# Edit .env with your values
```

## Docker Development

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f api

# Run migrations
docker compose exec api alembic upgrade head

# Stop
docker compose down
```

## Common Commands

| Task | Command |
|------|---------|
| Start API | `uvicorn app.main:app --reload` |
| Start Worker | `celery -A app.workers.celery_app worker --loglevel=info` |
| Start Beat | `celery -A app.workers.celery_app beat --loglevel=info` |
| Run tests | `pytest -v` |
| Test with coverage | `pytest --cov=app` |
| Create migration | `alembic revision --autogenerate -m "description"` |
| Apply migrations | `alembic upgrade head` |
| Rollback | `alembic downgrade -1` |
| Lint | `ruff check app/` |
| Format | `ruff format app/` |
| Type check | `mypy app/` |

## Testing

Tests use in-memory SQLite — no external services required.

```bash
pytest                     # Run all tests
pytest tests/unit/         # Unit tests only
pytest tests/integration/  # Integration tests only
pytest -k "test_auth"      # Run specific tests
pytest -v --tb=long        # Verbose with full tracebacks
```

## Project Structure

```
app/
├── main.py            # FastAPI app factory
├── api/               # HTTP endpoints
├── core/              # Config, security, logging, exceptions
├── db/                # Models, sessions, migrations
├── schemas/           # Pydantic request/response models
├── services/          # Business logic
├── agents/            # AI agent base contract
├── llm/               # Provider abstraction
├── workers/           # Celery tasks and scheduling
├── integrations/      # External service clients (future)
├── workflows/         # Pipeline orchestration (future)
├── repositories/      # DB access patterns (future)
└── utils/             # Redis, retry, helpers
```

## Adding a New Feature

1. Create models in `app/db/models/`
2. Create Pydantic schemas in `app/schemas/`
3. Create service logic in `app/services/`
4. Create API endpoint in `app/api/v1/`
5. Register route in `app/api/router.py`
6. Write tests
7. Create migration: `alembic revision --autogenerate -m "add feature X"`
