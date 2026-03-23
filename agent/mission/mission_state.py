"""Mission state machine — formal states, transitions, attempt tracking."""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from context.policy_telemetry import emit_policy_event


class MissionStatus(Enum):
    PENDING = "pending"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_REWORK = "waiting_rework"
    WAITING_TEST = "waiting_test"
    WAITING_REVIEW = "waiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


VALID_TRANSITIONS = {
    MissionStatus.PENDING: {MissionStatus.PLANNING},
    MissionStatus.PLANNING: {MissionStatus.READY, MissionStatus.FAILED},
    MissionStatus.READY: {MissionStatus.RUNNING},
    MissionStatus.RUNNING: {
        MissionStatus.WAITING_APPROVAL,
        MissionStatus.WAITING_REWORK,
        MissionStatus.WAITING_TEST,
        MissionStatus.WAITING_REVIEW,
        MissionStatus.COMPLETED,
        MissionStatus.FAILED
    },
    MissionStatus.WAITING_APPROVAL: {
        MissionStatus.RUNNING, MissionStatus.FAILED
    },
    MissionStatus.WAITING_REWORK: {MissionStatus.RUNNING},
    MissionStatus.WAITING_TEST: {MissionStatus.RUNNING},
    MissionStatus.WAITING_REVIEW: {MissionStatus.RUNNING},
    MissionStatus.FAILED: {
        MissionStatus.PLANNING, MissionStatus.READY
    },
    MissionStatus.COMPLETED: set()
}


@dataclass
class MissionState:
    mission_id: str
    status: MissionStatus = MissionStatus.PENDING
    current_stage_index: int = 0
    last_completed_stage_id: str = ""
    pending_stage_id: str = ""
    attempt_counters: dict = field(default_factory=dict)
    max_stage_attempts: int = 3
    transition_log: list = field(default_factory=list)

    def transition_to(self, new_status: MissionStatus,
                      reason: str = "") -> bool:
        """Attempt state transition. Returns True if valid."""
        if new_status not in VALID_TRANSITIONS.get(self.status, set()):
            emit_policy_event("invalid_state_transition", {
                "mission_id": self.mission_id,
                "from": self.status.value,
                "to": new_status.value,
                "reason": "transition not allowed"})
            return False

        old_status = self.status
        self.status = new_status

        self.transition_log.append({
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()})

        emit_policy_event("mission_state_transition", {
            "mission_id": self.mission_id,
            "from": old_status.value,
            "to": new_status.value,
            "reason": reason})

        return True

    def increment_stage_attempt(self, stage_id: str) -> int:
        self.attempt_counters[stage_id] = \
            self.attempt_counters.get(stage_id, 0) + 1
        return self.attempt_counters[stage_id]

    def can_retry_stage(self, stage_id: str) -> bool:
        return self.attempt_counters.get(stage_id, 0) < self.max_stage_attempts

    def to_dict(self) -> dict:
        return {
            "missionId": self.mission_id,
            "status": self.status.value,
            "currentStageIndex": self.current_stage_index,
            "lastCompletedStageId": self.last_completed_stage_id,
            "pendingStageId": self.pending_stage_id,
            "attemptCounters": self.attempt_counters,
            "transitionLog": self.transition_log}

    @classmethod
    def from_dict(cls, data: dict) -> "MissionState":
        state = cls(mission_id=data["missionId"])
        state.status = MissionStatus(data.get("status", "pending"))
        state.current_stage_index = data.get("currentStageIndex", 0)
        state.last_completed_stage_id = data.get("lastCompletedStageId", "")
        state.pending_stage_id = data.get("pendingStageId", "")
        state.attempt_counters = data.get("attemptCounters", {})
        state.transition_log = data.get("transitionLog", [])
        return state
