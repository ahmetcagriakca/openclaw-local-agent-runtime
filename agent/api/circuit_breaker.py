"""Per-source circuit breaker — D-072.

3 states: closed → open → half_open.
When one source fails, others continue serving.
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class _BreakerState:
    state: str = "closed"  # closed | open | half_open
    failure_count: int = 0
    last_failure_time: float = 0.0
    last_error: str = ""


class CircuitBreakerOpen(Exception):
    """Raised when circuit is open and call is rejected."""
    pass


class CircuitBreaker:
    """Per-source circuit breaker with 3 states."""

    def __init__(self, failure_threshold: int = 3,
                 recovery_timeout_s: float = 30.0):
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_s
        self._breakers: dict[str, _BreakerState] = {}

    def _get(self, source: str) -> _BreakerState:
        if source not in self._breakers:
            self._breakers[source] = _BreakerState()
        return self._breakers[source]

    def call(self, source_name: str, fn: Callable) -> Any:
        """Execute fn through the circuit breaker.

        Args:
            source_name: Identifier for this source.
            fn: Callable to execute.

        Returns:
            Result of fn().

        Raises:
            CircuitBreakerOpen: If circuit is open.
        """
        b = self._get(source_name)

        if b.state == "open":
            # Check if recovery timeout elapsed
            if time.time() - b.last_failure_time >= self._recovery_timeout:
                b.state = "half_open"
            else:
                raise CircuitBreakerOpen(
                    f"Circuit open for '{source_name}': {b.last_error}")

        try:
            result = fn()
            # Success → reset to closed
            if b.state == "half_open":
                b.state = "closed"
            b.failure_count = 0
            return result
        except Exception as e:
            b.failure_count += 1
            b.last_failure_time = time.time()
            b.last_error = str(e)[:200]

            if b.failure_count >= self._threshold:
                b.state = "open"
            raise

    def get_state(self, source_name: str) -> str:
        """Get current state: closed | open | half_open."""
        b = self._get(source_name)
        # Check for timeout transition
        if b.state == "open":
            if time.time() - b.last_failure_time >= self._recovery_timeout:
                b.state = "half_open"
        return b.state

    def reset(self, source_name: str) -> None:
        """Reset breaker to closed state."""
        if source_name in self._breakers:
            self._breakers[source_name] = _BreakerState()
