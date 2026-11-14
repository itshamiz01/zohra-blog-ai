"""
Zohra — Source Circuit Breaker.

Prevents hammering dead, rate-limited, or failing external websites:
  CLOSED (normal) → failures >= threshold → OPEN (blocking) → cooldown passes → HALF-OPEN (testing)
  HALF-OPEN: success → CLOSED; failure → OPEN
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.core.constants import CircuitBreakerState


@dataclass
class CircuitBreakerStatus:
    state: CircuitBreakerState
    consecutive_failures: int
    can_attempt: bool
    cooldown_remaining_seconds: float


class SourceCircuitBreaker:
    """
    In-memory / Redis-compatible circuit breaker for a source.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 300.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.state = CircuitBreakerState.CLOSED
        self.tripped_at: float | None = None

    def can_execute(self) -> bool:
        status = self.check_state(
            current_state=self.state.value,
            consecutive_failures=self.consecutive_failures,
            tripped_at_epoch=self.tripped_at,
        )
        return status.can_attempt

    def check_state(
        self,
        current_state: str,
        consecutive_failures: int,
        tripped_at_epoch: float | None,
        now_epoch: float | None = None,
    ) -> CircuitBreakerStatus:
        """Evaluate circuit breaker state and determine if an attempt is permitted."""
        now = now_epoch if now_epoch is not None else time.time()
        cb_state = CircuitBreakerState(current_state)

        if cb_state == CircuitBreakerState.CLOSED:
            if consecutive_failures >= self.failure_threshold:
                return CircuitBreakerStatus(
                    state=CircuitBreakerState.OPEN,
                    consecutive_failures=consecutive_failures,
                    can_attempt=False,
                    cooldown_remaining_seconds=self.cooldown_seconds,
                )
            return CircuitBreakerStatus(
                state=CircuitBreakerState.CLOSED,
                consecutive_failures=consecutive_failures,
                can_attempt=True,
                cooldown_remaining_seconds=0.0,
            )

        if cb_state == CircuitBreakerState.OPEN:
            time_since_trip = (
                (now - tripped_at_epoch) if tripped_at_epoch else self.cooldown_seconds + 1
            )
            if time_since_trip >= self.cooldown_seconds:
                # Cooldown elapsed -> transition to HALF_OPEN to test
                return CircuitBreakerStatus(
                    state=CircuitBreakerState.HALF_OPEN,
                    consecutive_failures=consecutive_failures,
                    can_attempt=True,
                    cooldown_remaining_seconds=0.0,
                )
            return CircuitBreakerStatus(
                state=CircuitBreakerState.OPEN,
                consecutive_failures=consecutive_failures,
                can_attempt=False,
                cooldown_remaining_seconds=max(0.0, self.cooldown_seconds - time_since_trip),
            )

        # HALF_OPEN
        return CircuitBreakerStatus(
            state=CircuitBreakerState.HALF_OPEN,
            consecutive_failures=consecutive_failures,
            can_attempt=True,
            cooldown_remaining_seconds=0.0,
        )

    def record_success(self) -> tuple[CircuitBreakerState, int]:
        """On success, reset consecutive failures and close circuit."""
        self.consecutive_failures = 0
        self.state = CircuitBreakerState.CLOSED
        self.tripped_at = None
        return CircuitBreakerState.CLOSED, 0

    def record_failure(
        self,
        current_failures: int | None = None,
        current_state: str | None = None,
    ) -> tuple[CircuitBreakerState, int, bool]:
        """
        Record a failure.
        Returns (new_state, new_consecutive_failures, did_trip).
        """
        c_fails = self.consecutive_failures if current_failures is None else current_failures
        c_state = self.state.value if current_state is None else current_state

        new_failures = c_fails + 1

        if c_state == CircuitBreakerState.HALF_OPEN.value:
            # Immediate re-trip back to OPEN
            res = CircuitBreakerState.OPEN, new_failures, True
        elif new_failures >= self.failure_threshold and c_state != CircuitBreakerState.OPEN.value:
            res = CircuitBreakerState.OPEN, new_failures, True
        else:
            res = CircuitBreakerState(c_state), new_failures, False

        self.consecutive_failures = res[1]
        self.state = res[0]
        if res[2]:
            self.tripped_at = time.time()
        return res


CircuitBreaker = SourceCircuitBreaker

