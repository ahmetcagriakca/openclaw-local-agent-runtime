"""StageRecoveryEngine — extracted from MissionController (D-139, B-139).

Handles stage failure recovery triage: circuit breaker, poison pill detection,
exponential backoff, manager invocation, and DLQ enqueue.
"""
import json
import logging
import re
from typing import Any, Callable

from context.policy_telemetry import emit_policy_event
from mission.mission_state import MissionState, MissionStatus
from mission.resilience import (
    CircuitBreaker,
    is_poison_pill,
    sleep_with_backoff,
)
from persistence.dlq_store import DLQStore

logger = logging.getLogger("mcc.mission.recovery_engine")


class StageRecoveryEngine:
    """D-056 / B-106: Stage failure recovery with circuit breaker + DLQ."""

    def __init__(self, circuit_breaker: CircuitBreaker, dlq_store: DLQStore):
        self._circuit_breaker = circuit_breaker
        self._dlq_store = dlq_store

    def handle_stage_failure(
        self,
        failed_stage: dict,
        error_context: str,
        mission_state: MissionState,
        assembler: Any,
        mission_id: str,
        user_id: str,
        all_artifacts: list,
        expansion_broker: Any,
        execute_stage_fn: Callable,
        create_recovery_stage_fn: Callable,
    ) -> dict:
        """D-056: First reflex is recovery_triage, NOT restart.

        B-106: Enhanced with exponential backoff, circuit breaker,
        and poison pill detection.

        Returns: {"action": "retry_stage"|"abort"|"escalate"|"retry_from",
                  "reason": ..., ...}
        """
        stage_id = failed_stage.get("id",
                                    failed_stage.get("stage_id", "unknown"))
        specialist = failed_stage.get("specialist", "unknown")

        # B-106: Circuit breaker check — fail-fast if circuit is open
        if self._circuit_breaker.is_open(specialist):
            emit_policy_event("recovery_triage_decision", {
                "mission_id": mission_state.mission_id,
                "stage_id": stage_id,
                "action": "abort",
                "reason": f"Circuit open for {specialist}"
            })
            return {"action": "abort",
                    "reason": f"circuit_open:{specialist}"}

        # B-106: Poison pill detection — same error repeating
        if is_poison_pill(specialist, error_context, self._circuit_breaker):
            self._circuit_breaker.record_failure(specialist, error_context)
            emit_policy_event("recovery_triage_decision", {
                "mission_id": mission_state.mission_id,
                "stage_id": stage_id,
                "action": "abort",
                "reason": "Poison pill — identical error repeating"
            })
            return {"action": "abort",
                    "reason": "poison_pill_detected"}

        # Record failure in circuit breaker
        self._circuit_breaker.record_failure(specialist, error_context)

        # Check retry budget
        attempt = mission_state.increment_stage_attempt(stage_id)
        if not mission_state.can_retry_stage(stage_id):
            emit_policy_event("recovery_triage_decision", {
                "mission_id": mission_state.mission_id,
                "stage_id": stage_id,
                "action": "abort",
                "reason": f"Max attempts ({attempt}) exceeded"
            })
            return {"action": "abort",
                    "reason": "max_attempts_exceeded"}

        # B-106: Exponential backoff before retry
        sleep_with_backoff(attempt)

        # Transition to FAILED for recovery
        if mission_state.status != MissionStatus.FAILED:
            mission_state.transition_to(
                MissionStatus.FAILED,
                f"Stage {stage_id} failed, attempt {attempt}")

        # Try to invoke Manager recovery_triage
        try:
            recovery_stage = create_recovery_stage_fn(
                failed_stage, error_context)

            recovery_result = execute_stage_fn(
                recovery_stage, all_artifacts, mission_id, user_id,
                expansion_broker=expansion_broker)

            # Parse recovery decision from result
            recovery_data = {}
            if recovery_result and isinstance(recovery_result, dict):
                response_text = recovery_result.get("response", "")
                try:
                    json_match = re.search(
                        r'\{[^}]*"recovery_action"[^}]*\}',
                        response_text)
                    if json_match:
                        recovery_data = json.loads(json_match.group())
                except (json.JSONDecodeError, AttributeError):
                    pass

            action = recovery_data.get("recovery_action", "abort")

            emit_policy_event("recovery_triage_decision", {
                "mission_id": mission_state.mission_id,
                "stage_id": stage_id,
                "action": action,
                "diagnosis": str(
                    recovery_data.get("diagnosis", ""))[:200]
            })

            if action == "retry_stage":
                mission_state.transition_to(
                    MissionStatus.READY,
                    f"Recovery: retry {stage_id}")
                mission_state.transition_to(
                    MissionStatus.RUNNING,
                    "resuming after recovery")
                return {"action": "retry_stage", "stage_id": stage_id}

            elif action == "escalate_to_operator":
                return {"action": "escalate",
                        "reason": recovery_data.get("diagnosis", "")}

            elif action == "retry_from":
                return {"action": "retry_from",
                        "target_stage": recovery_data.get(
                            "target_stage", "stage-1"),
                        "reason": recovery_data.get("diagnosis", "")}

            else:
                return {"action": "abort",
                        "reason": recovery_data.get(
                            "diagnosis", "Recovery chose abort")}

        except Exception as recovery_error:
            emit_policy_event("recovery_triage_decision", {
                "mission_id": mission_state.mission_id,
                "stage_id": stage_id,
                "action": "abort",
                "reason": f"Recovery failed: {str(recovery_error)[:200]}"
            })
            return {"action": "abort",
                    "reason": f"Recovery triage itself failed: "
                              f"{recovery_error}"}

    def enqueue_to_dlq(self, mission: dict,
                       suppress: bool = False) -> str | None:
        """B-106: Enqueue failed mission to DLQ for later retry.

        suppress: True during DLQ retry to prevent orphan entries.
        """
        if suppress:
            return None
        try:
            failed_stage_id = ""
            for s in mission.get("stages", []):
                if s.get("status") == "failed":
                    failed_stage_id = s.get("id", "")
                    break
            return self._dlq_store.enqueue(
                mission,
                failed_stage_id=failed_stage_id,
                error=mission.get("error", ""),
            )
        except Exception as e:
            logger.error("DLQ enqueue failed: %s", e)
            return None
