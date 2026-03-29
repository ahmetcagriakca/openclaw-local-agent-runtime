"""Mission resilience utilities — B-106.

Exponential backoff, circuit breaker, and poison pill detection
for stage retry logic.
"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger("mcc.mission.resilience")

# ── Exponential Backoff ──────────────────────────────────────────

BACKOFF_BASE_S = 0.5      # 500ms initial delay
BACKOFF_MAX_S = 30.0      # 30s max delay
BACKOFF_MULTIPLIER = 2.0  # Double each attempt


def backoff_delay(attempt: int) -> float:
    """Calculate backoff delay in seconds for given attempt number.

    Formula: min(max_delay, base * multiplier^(attempt-1))
    attempt=1 → 0.5s, attempt=2 → 1s, attempt=3 → 2s, ...
    """
    if attempt <= 0:
        return 0.0
    delay = BACKOFF_BASE_S * (BACKOFF_MULTIPLIER ** (attempt - 1))
    return min(delay, BACKOFF_MAX_S)


def sleep_with_backoff(attempt: int) -> float:
    """Sleep for backoff duration. Returns actual delay used."""
    delay = backoff_delay(attempt)
    if delay > 0:
        logger.info("Backoff: sleeping %.1fs before attempt %d", delay, attempt)
        time.sleep(delay)
    return delay


# ── Circuit Breaker ──────────────────────────────────────────────

class CircuitStatus(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitState:
    """Per-stage-type circuit breaker state."""
    failure_count: int = 0
    last_failure_at: str | None = None
    last_error_hash: str = ""
    status: CircuitStatus = CircuitStatus.CLOSED
    opened_at: str | None = None


class CircuitBreaker:
    """Circuit breaker for mission stage execution.

    Tracks consecutive failures per stage type (specialist role).
    Opens circuit after threshold failures, preventing further
    attempts until reset timeout expires. After timeout, enters
    HALF_OPEN state allowing exactly one probe attempt.

    State machine:
        CLOSED --(failure_threshold reached)--> OPEN
        OPEN --(reset_timeout elapsed)--> HALF_OPEN
        HALF_OPEN --(probe success)--> CLOSED
        HALF_OPEN --(probe failure)--> OPEN (timer reset)

    Parameters:
        failure_threshold: Consecutive failures before opening (default 3)
        reset_timeout_s: Seconds before half-open check (default 300 = 5min)
    """

    def __init__(self, failure_threshold: int = 3,
                 reset_timeout_s: float = 300.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout_s = reset_timeout_s
        self._circuits: dict[str, CircuitState] = {}

    def _get_circuit(self, key: str) -> CircuitState:
        if key not in self._circuits:
            self._circuits[key] = CircuitState()
        return self._circuits[key]

    def is_open(self, stage_type: str) -> bool:
        """Check if circuit is open (should fail-fast).

        Returns True if circuit is OPEN and reset timeout hasn't elapsed.
        If timeout has elapsed, transitions to HALF_OPEN and returns False
        to allow exactly one probe attempt.
        """
        circuit = self._get_circuit(stage_type)

        if circuit.status == CircuitStatus.CLOSED:
            return False

        if circuit.status == CircuitStatus.HALF_OPEN:
            # Already in half-open, allow the probe
            return False

        # Status is OPEN — check if reset timeout has elapsed
        if circuit.opened_at:
            opened = datetime.fromisoformat(circuit.opened_at)
            elapsed = (datetime.now(timezone.utc) - opened).total_seconds()
            if elapsed >= self.reset_timeout_s:
                # Transition to HALF_OPEN — allow one probe
                circuit.status = CircuitStatus.HALF_OPEN
                logger.info("Circuit HALF_OPEN for %s (%.0fs elapsed)",
                            stage_type, elapsed)
                return False

        return True

    def record_failure(self, stage_type: str, error: str = "") -> bool:
        """Record a stage failure. Returns True if circuit just opened.

        In HALF_OPEN state, a failure immediately re-opens the circuit
        with a fresh timer.
        """
        circuit = self._get_circuit(stage_type)
        now = datetime.now(timezone.utc).isoformat()

        circuit.failure_count += 1
        circuit.last_failure_at = now
        circuit.last_error_hash = _error_hash(error)

        if circuit.status == CircuitStatus.HALF_OPEN:
            # Probe failed — re-open with fresh timer
            circuit.status = CircuitStatus.OPEN
            circuit.opened_at = now
            logger.warning(
                "Circuit re-OPEN for %s (half-open probe failed)",
                stage_type)
            return True

        if (circuit.failure_count >= self.failure_threshold
                and circuit.status == CircuitStatus.CLOSED):
            circuit.status = CircuitStatus.OPEN
            circuit.opened_at = now
            logger.warning(
                "Circuit OPEN for %s after %d failures",
                stage_type, circuit.failure_count)
            return True

        return False

    def record_success(self, stage_type: str) -> None:
        """Record a stage success — reset circuit to CLOSED."""
        circuit = self._get_circuit(stage_type)
        if circuit.failure_count > 0 or circuit.status != CircuitStatus.CLOSED:
            logger.info("Circuit CLOSED for %s (was: %d failures, status=%s)",
                        stage_type, circuit.failure_count, circuit.status.value)
        circuit.failure_count = 0
        circuit.last_failure_at = None
        circuit.last_error_hash = ""
        circuit.status = CircuitStatus.CLOSED
        circuit.opened_at = None

    def get_state(self, stage_type: str) -> dict:
        """Get circuit state for inspection."""
        circuit = self._get_circuit(stage_type)
        return {
            "stage_type": stage_type,
            "failure_count": circuit.failure_count,
            "last_failure_at": circuit.last_failure_at,
            "status": circuit.status.value,
            "opened_at": circuit.opened_at,
        }

    def all_states(self) -> list[dict]:
        """Get all circuit states."""
        return [self.get_state(k) for k in self._circuits]

    def reset(self, stage_type: str) -> None:
        """Manually reset a circuit."""
        if stage_type in self._circuits:
            self._circuits[stage_type] = CircuitState()
            logger.info("Circuit manually reset for %s", stage_type)

    def reset_all(self) -> None:
        """Reset all circuits."""
        self._circuits.clear()


# ── Poison Pill Detection ────────────────────────────────────────

def is_poison_pill(stage_type: str, error: str,
                   breaker: CircuitBreaker) -> bool:
    """Check if a stage error matches previous failures (same error hash).

    If same stage type fails with identical error repeatedly,
    it's a poison pill — further retries are pointless.
    """
    circuit = breaker._get_circuit(stage_type)
    current_hash = _error_hash(error)
    if (circuit.last_error_hash == current_hash
            and circuit.failure_count >= 2):
        logger.warning("Poison pill detected: %s (hash=%s, failures=%d)",
                        stage_type, current_hash[:16], circuit.failure_count)
        return True
    return False


def _error_hash(error: str) -> str:
    """Simple hash of error message for comparison."""
    import hashlib
    # Normalize: strip timestamps, IDs, whitespace
    normalized = error.strip().lower()
    return hashlib.md5(normalized.encode()).hexdigest()[:16]
