"""
Tests for retry utility.
"""

import pytest

from app.utils.retry import calculate_backoff, retry_async, with_retry


class TestRetry:
    """Retry utility tests."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await retry_async(succeed, max_attempts=3)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("temporary failure")
            return "recovered"

        result = await retry_async(fail_twice, max_attempts=5, base_delay=0.01)
        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        async def always_fail():
            raise RuntimeError("permanent failure")

        with pytest.raises(RuntimeError, match="permanent failure"):
            await retry_async(always_fail, max_attempts=3, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_non_retryable_errors_raise_immediately(self):
        call_count = 0

        async def value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            await retry_async(value_error, max_attempts=5, base_delay=0.01)
        assert call_count == 1  # no retry for ValueError

    def test_backoff_calculation(self):
        delay = calculate_backoff(0, base=1.0, cap=60.0)
        assert 0 <= delay <= 1.0

        delay = calculate_backoff(3, base=1.0, cap=60.0)
        assert 0 <= delay <= 8.0

    def test_backoff_respects_cap(self):
        delay = calculate_backoff(100, base=1.0, cap=10.0)
        assert delay <= 10.0

    @pytest.mark.asyncio
    async def test_decorator_form(self):
        call_count = 0

        @with_retry(max_attempts=3, base_delay=0.01)
        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("flaky")
            return "stable"

        result = await flaky()
        assert result == "stable"
        assert call_count == 2
