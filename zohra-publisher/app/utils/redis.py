"""
Zohra — Redis client and utilities.

Provides:
  - async Redis connection management
  - distributed locking (with auto-expiry to prevent deadlocks)
  - idempotency key management
  - health check
  - namespaced key helpers
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.constants import (
    DEFAULT_IDEMPOTENCY_TTL_SECONDS,
    DEFAULT_LOCK_TTL_SECONDS,
    REDIS_CACHE_PREFIX,
    REDIS_IDEMPOTENCY_PREFIX,
    REDIS_LOCK_PREFIX,
)
from app.core.exceptions import DuplicateOperationError
from app.core.logging import get_logger

logger = get_logger(__name__, component="redis")

# ── Connection ───────────────────────────────────────────────────

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Return the shared async Redis client, creating it on first call."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
    return _redis_client


async def close_redis() -> None:
    """Shutdown the Redis connection — called during app teardown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def check_redis_health() -> bool:
    """Return True if Redis responds to PING."""
    try:
        client = await get_redis()
        return await client.ping()
    except Exception:
        return False


# ── Distributed Locking ──────────────────────────────────────────


@asynccontextmanager
async def distributed_lock(
    resource: str,
    ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    owner: str | None = None,
) -> AsyncGenerator[bool, None]:
    """
    Acquire a Redis-based distributed lock.
    Auto-releases on exit. TTL prevents permanent deadlocks.

    Usage:
        async with distributed_lock("topic:123") as acquired:
            if acquired:
                # safe to process
    """
    acquired = False
    client = None
    lock_key = f"{REDIS_LOCK_PREFIX}:{resource}"
    lock_owner = owner or str(uuid.uuid4())

    try:
        client = await get_redis()
        acquired = bool(await client.set(lock_key, lock_owner, nx=True, ex=ttl_seconds))
    except Exception as exc:
        logger.warning("redis_unavailable_for_lock: resource=%s, error=%s", resource, str(exc))
        yield True
        return

    try:
        yield acquired
    finally:
        if acquired and client:
            try:
                current = await client.get(lock_key)
                if current == lock_owner:
                    await client.delete(lock_key)
            except Exception as exc:
                logger.warning("Failed to release distributed lock %s: %s", lock_key, exc)


async def is_locked(resource: str) -> bool:
    """Check whether a resource is currently locked."""
    client = await get_redis()
    lock_key = f"{REDIS_LOCK_PREFIX}:{resource}"
    return await client.exists(lock_key) > 0


# ── Idempotency ──────────────────────────────────────────────────


async def check_idempotency(
    key: str,
    ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS,
) -> None:
    """
    Check if an operation with this key has already been performed.
    Raises DuplicateOperationError if the key exists.
    Otherwise sets the key with TTL to mark the operation as started.
    """
    client = await get_redis()
    full_key = f"{REDIS_IDEMPOTENCY_PREFIX}:{key}"

    was_set = await client.set(full_key, "processing", nx=True, ex=ttl_seconds)
    if not was_set:
        existing = await client.get(full_key)
        raise DuplicateOperationError(f"Operation '{key}' already exists with status: {existing}")


async def mark_idempotency_complete(
    key: str,
    result_ref: str = "completed",
    ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS,
) -> None:
    """Mark an idempotent operation as completed with a result reference."""
    client = await get_redis()
    full_key = f"{REDIS_IDEMPOTENCY_PREFIX}:{key}"
    await client.set(full_key, result_ref, ex=ttl_seconds)


async def clear_idempotency(key: str) -> None:
    """Remove an idempotency key (e.g., after failed operation that should be retryable)."""
    client = await get_redis()
    full_key = f"{REDIS_IDEMPOTENCY_PREFIX}:{key}"
    await client.delete(full_key)


# ── Cache Helpers ────────────────────────────────────────────────


async def cache_get(key: str) -> str | None:
    """Retrieve a cached value."""
    client = await get_redis()
    return await client.get(f"{REDIS_CACHE_PREFIX}:{key}")


async def cache_set(key: str, value: str, ttl_seconds: int = 3600) -> None:
    """Store a value with TTL. Never creates permanent entries."""
    client = await get_redis()
    await client.set(f"{REDIS_CACHE_PREFIX}:{key}", value, ex=ttl_seconds)


async def cache_delete(key: str) -> None:
    """Remove a cached entry."""
    client = await get_redis()
    await client.delete(f"{REDIS_CACHE_PREFIX}:{key}")
