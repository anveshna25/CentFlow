import asyncio
from datetime import datetime, timezone
from enum import Enum
import logging
import time
from typing import Any, Callable, Coroutine, Optional, TypeVar

from app.core.errors import CircuitBreakerOpenError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Operational states of a Circuit Breaker."""

    CLOSED = "CLOSED"        # Normal operational state; calls pass through.
    OPEN = "OPEN"            # Provider degraded/failing; calls fail fast or route to fallback.
    HALF_OPEN = "HALF_OPEN"  # Recovery trial state; testing if upstream has recovered.


class CircuitBreaker:
    """Async-safe Circuit Breaker pattern implementation.

    Monitors calls to external dependencies (e.g., market data providers).
    When consecutive failures breach `failure_threshold`, transitions to OPEN
    to prevent cascading timeouts and resource exhaustion. After `recovery_timeout`,
    transitions to HALF_OPEN to attempt recovery probes.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 1,
    ) -> None:
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(0.05, recovery_timeout)
        self.half_open_success_threshold = max(1, half_open_success_threshold)

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_state_change = time.monotonic()
        self._last_failure_time: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._total_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        self._rejected_calls = 0

    @property
    def consecutive_failures(self) -> int:
        """Number of consecutive failures recorded while in CLOSED state."""
        return self._consecutive_failures

    @property
    def state(self) -> CircuitState:
        """Current operational state, automatically transitioning OPEN -> HALF_OPEN on timeout."""
        now = time.monotonic()
        if self._state == CircuitState.OPEN and (now - self._last_state_change >= self.recovery_timeout):
            self._state = CircuitState.HALF_OPEN
            self._last_state_change = now
            self._consecutive_successes = 0
            logger.info(
                "Circuit breaker '%s' transition: OPEN -> HALF_OPEN (recovery cooldown elapsed)",
                self.name,
            )
        return self._state

    def can_execute(self) -> bool:
        """Check whether a request is permitted to call the underlying dependency."""
        return self.state != CircuitState.OPEN

    def get_remaining_cooldown(self) -> float:
        """Return remaining seconds before OPEN circuit transitions to HALF_OPEN."""
        now = time.monotonic()
        if self._state == CircuitState.OPEN:
            elapsed = now - self._last_state_change
            if elapsed < self.recovery_timeout:
                return max(0.0, self.recovery_timeout - elapsed)
        return 0.0

    def record_success(self) -> None:
        """Record a successful execution against the underlying dependency."""
        self._total_successes += 1
        current = self.state

        if current == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.half_open_success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif current == CircuitState.CLOSED:
            self._consecutive_failures = 0

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record an execution failure against the underlying dependency."""
        self._total_failures += 1
        self._last_failure_time = datetime.now(timezone.utc)
        self._last_error = str(error) if error else "Unknown error"

        current = self.state
        if current == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif current == CircuitState.CLOSED:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition the circuit to a new state and reset tracking counters."""
        if self._state != new_state:
            logger.warning(
                "Circuit breaker '%s' transition: %s -> %s (consecutive failures: %d)",
                self.name,
                self._state.value,
                new_state.value,
                self._consecutive_failures,
            )
            self._state = new_state
            self._last_state_change = time.monotonic()
            if new_state == CircuitState.CLOSED:
                self._consecutive_failures = 0
                self._consecutive_successes = 0
            elif new_state == CircuitState.OPEN:
                self._consecutive_successes = 0

    def reset(self) -> None:
        """Manually force the circuit breaker back to CLOSED state."""
        self._transition_to(CircuitState.CLOSED)
        self._consecutive_failures = 0
        self._last_error = None

    def get_metrics(self) -> dict[str, Any]:
        """Diagnostic metrics and health telemetry for this circuit breaker."""
        state = self.state
        return {
            "name": self.name,
            "state": state.value,
            "can_execute": state != CircuitState.OPEN,
            "consecutive_failures": self._consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "cooldown_remaining_seconds": round(self.get_remaining_cooldown(), 2),
            "total_calls": self._total_calls,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "rejected_calls": self._rejected_calls,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "last_error": self._last_error,
        }

    async def execute(self, coro_fn: Callable[[], Coroutine[Any, Any, T]]) -> T:
        """Execute an asynchronous operation wrapped with circuit breaker protection.

        Raises:
            CircuitBreakerOpenError: If the circuit is currently OPEN.
        """
        self._total_calls += 1
        if not self.can_execute():
            self._rejected_calls += 1
            raise CircuitBreakerOpenError(
                provider_name=self.name,
                reset_timeout_seconds=self.get_remaining_cooldown(),
            )

        try:
            result = await coro_fn()
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure(exc)
            raise
