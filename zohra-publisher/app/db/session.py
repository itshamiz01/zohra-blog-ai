"""
Zohra — Async database session management.

Provides:
  - async SQLAlchemy engine
  - async session factory
  - FastAPI dependency for request-scoped sessions
  - health check utility
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

# ── Engine & Session Factory ─────────────────────────────────────

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the async engine, creating it on first call."""
    global _engine
    if _engine is None:
        settings = get_settings()
        engine_kwargs: dict[str, Any] = {
            "echo": settings.DEBUG and settings.is_development,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
        if "sqlite" not in settings.DATABASE_URL:
            engine_kwargs["pool_size"] = 10
            engine_kwargs["max_overflow"] = 20
        _engine = create_async_engine(
            settings.DATABASE_URL,
            **engine_kwargs,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


def async_session_factory() -> AsyncSession:
    """Convenience callable returning a new AsyncSession from the factory."""
    return get_session_factory()()


# ── FastAPI Dependency ───────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a request-scoped async session.
    Commits on success, rolls back on exception.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Health Check ─────────────────────────────────────────────────


async def check_database_health() -> bool:
    """Return True if the database is reachable."""
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ── Lifecycle ────────────────────────────────────────────────────


async def close_engine() -> None:
    """Dispose of the engine — called during shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
