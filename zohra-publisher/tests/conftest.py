"""
Zohra — Pytest fixtures for unit and integration tests.

Provides:
  - in-memory SQLite async session (no real PostgreSQL needed)
  - FastAPI test client
  - settings overrides for test isolation
  - admin auth header fixture
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import ZohraBase

# ── Override env BEFORE importing app code ───────────────────────

os.environ.update(
    {
        "APP_ENV": "testing",
        "DATABASE_URL": "sqlite+aiosqlite:///",
        "REDIS_URL": "redis://localhost:6379/15",
        "CELERY_BROKER_URL": "redis://localhost:6379/14",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/14",
        "SECRET_KEY": "test-secret-key-do-not-use-in-production",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD_HASH": "$2b$12$2DO0H/A.VEABxFhOYo.xiu7VUmus3GDmxrUDYGAob6eTDTZjE4N7m",  # hash of "testpass123"
        "LLM_DAILY_BUDGET": "100.0",
        "LLM_MONTHLY_BUDGET": "1000.0",
        "AUTONOMY_ENABLED": "false",
        "MAINTENANCE_MODE": "false",
        "LLM_PRIMARY_PROVIDER": "openai",
        "GEMINI_ENABLED": "false",
        "OPENAI_API_KEY": "",
        "GEMINI_API_KEY": "",
    }
)


from app.core.config import get_settings
from app.db.session import get_db
from app.llm.registry import reset_providers

# ── Clear cached settings for test isolation ─────────────────────


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the lru_cache on get_settings so each test gets fresh settings."""
    reset_providers()
    get_settings.cache_clear()
    yield
    reset_providers()
    get_settings.cache_clear()


# ── In-Memory SQLite Database ────────────────────────────────────


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated in-memory SQLite async session."""
    engine = create_async_engine("sqlite+aiosqlite:///", echo=False)

    async with engine.begin() as conn:
        import app.db.models  # noqa: F401
        await conn.run_sync(ZohraBase.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(ZohraBase.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db(db_session: AsyncSession) -> AsyncSession:
    """Alias for db_session fixture."""
    return db_session


# ── FastAPI Test Client ──────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async test client with the DB session override.
    No real PostgreSQL or Redis needed.
    """
    from app.main import app

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Admin Auth Header ────────────────────────────────────────────


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Return auth headers with a valid admin JWT token."""
    from app.core.security import create_access_token

    token = create_access_token(subject="admin", extra={"role": "admin"})
    return {"Authorization": f"Bearer {token}"}
