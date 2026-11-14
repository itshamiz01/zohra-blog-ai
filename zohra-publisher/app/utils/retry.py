"""
Zohra — Retry utility with exponential backoff and jitter.

Provides a reusable async retry decorator and function.
Different failure types can have different retry policies.
"""

from __future__ import annotations

import asyncio
import functools
import random
from collections.abc import Callable
from typing import Any, TypeVar

from app.core.constants import MAX_RETRY_ATTEMPTS, RETRY_BASE_DELAY_SECONDS, RETRY_MAX_DELAY_SECONDS
from app.core.logging import get_logger

logger = get_logger(__name__, component="retry")

T = TypeVar("T")

# Errors that should generally NOT be retried
NON_RETRYABLE_ERRORS = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    PermissionError,
)


def calculate_backoff(
    attempt: int, base: float = RETRY_BASE_DELAY_SECONDS, cap: float = RETRY_MAX_DELAY_SECONDS
) -> float:
    """Exponential backoff with full jitter."""
    delay = min(base * (2**attempt), cap)
    return random.uniform(0, delay)


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY_SECONDS,
    max_delay: float = RETRY_MAX_DELAY_SECONDS,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
    on_retry: Callable[[int, Exception], Any] | None = None,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff + jitter.

    Args:
        func: Async callable to retry.
        max_attempts: Maximum number of attempts (including the first).
        base_delay: Base delay in seconds for backoff calculation.
        max_delay: Maximum delay cap in seconds.
        retryable_exceptions: Tuple of exception types that should trigger retry.
                              If None, retries on all exceptions except NON_RETRYABLE_ERRORS.
        on_retry: Optional callback(attempt, exception) called before each retry.
    """
    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except NON_RETRYABLE_ERRORS:
            raise  # never retry logic errors
        except Exception as exc:
            if retryable_exceptions and not isinstance(exc, retryable_exceptions):
                raise

            last_exception = exc

            if attempt + 1 >= max_attempts:
                logger.error(
                    "All %d retry attempts exhausted for %s: %s",
                    max_attempts,
                    func.__name__,
                    exc,
                )
                raise

            delay = calculate_backoff(attempt, base_delay, max_delay)

            logger.warning(
                "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                attempt + 1,
                max_attempts,
                func.__name__,
                exc,
                delay,
            )

            if on_retry:
                if asyncio.iscoroutinefunction(on_retry):
                    await on_retry(attempt + 1, exc)
                else:
                    on_retry(attempt + 1, exc)

            await asyncio.sleep(delay)

    # Should not reach here, but be explicit
    if last_exception:
        raise last_exception


def with_retry(
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY_SECONDS,
    max_delay: float = RETRY_MAX_DELAY_SECONDS,
    retryable_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable:
    """
    Decorator form of retry_async.

    Usage:
        @with_retry(max_attempts=3)
        async def call_external_api():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_async(
                func,
                *args,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions,
                **kwargs,
            )

        return wrapper

    return decorator
