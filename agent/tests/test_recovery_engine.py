"""Tests for StageRecoveryEngine — B-139 extraction from controller."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mission.mission_state import MissionState, MissionStatus
from mission.recovery_engine import StageRecoveryEngine
from mission.resilience import CircuitBreaker, CircuitStatus
from persistence.dlq_store import DLQStore


@pytest.fixture
def circuit_breaker():
    return CircuitBreaker(failure_threshold=3, reset_timeout_s=300.0)


@pytest.fixture
def dlq_store(tmp_path):
    return DLQStore(store_path=str(tmp_path / "dlq" / "dlq.json"))


@pytest.fixture
def engine(circuit_breaker, dlq_store):
    return StageRecoveryEngine(circuit_breaker, dlq_store)


def _make_stage(stage_id="stage-1", specialist="developer"):
    return {"id": stage_id, "specialist": specialist, "status": "failed"}


def _make_state(mission_id="m-test"):
    return MissionState(mission_id)


class TestHandleStageFailure:
    @patch("mission.recovery_engine.emit_policy_event")
    def test_circuit_open_aborts(self, mock_emit, engine, circuit_breaker):
        cs = circuit_breaker._get_circuit("developer")
        cs.status = CircuitStatus.OPEN
        cs.failure_count = 99

        state = _make_state()
        state.transition_to(MissionStatus.RUNNING, "test")

        result = engine.handle_stage_failure(
            failed_stage=_make_stage(),
            error_context="some error",
            mission_state=state,
            assembler=None,
            mission_id="m-test",
            user_id="u1",
            all_artifacts=[],
            expansion_broker=None,
            execute_stage_fn=MagicMock(),
            create_recovery_stage_fn=MagicMock(),
        )
        assert result["action"] == "abort"
        assert "circuit_open" in result["reason"]

    @patch("mission.recovery_engine.emit_policy_event")
    @patch("mission.recovery_engine.sleep_with_backoff")
    def test_max_attempts_aborts(self, mock_sleep, mock_emit, engine):
        state = _make_state()
        state.transition_to(MissionStatus.RUNNING, "test")
        # Exhaust retry budget
        for _ in range(5):
            state.increment_stage_attempt("stage-1")

        result = engine.handle_stage_failure(
            failed_stage=_make_stage(),
            error_context="error",
            mission_state=state,
            assembler=None,
            mission_id="m-test",
            user_id="u1",
            all_artifacts=[],
            expansion_broker=None,
            execute_stage_fn=MagicMock(),
            create_recovery_stage_fn=MagicMock(),
        )
        assert result["action"] == "abort"
        assert "max_attempts" in result["reason"]

    @patch("mission.recovery_engine.emit_policy_event")
    @patch("mission.recovery_engine.sleep_with_backoff")
    def test_recovery_abort_default(self, mock_sleep, mock_emit, engine):
        state = _make_state()
        state.transition_to(MissionStatus.RUNNING, "test")

        mock_execute = MagicMock(return_value={"response": "no json here"})
        mock_create = MagicMock(return_value={"specialist": "manager"})

        result = engine.handle_stage_failure(
            failed_stage=_make_stage(),
            error_context="error",
            mission_state=state,
            assembler=None,
            mission_id="m-test",
            user_id="u1",
            all_artifacts=[],
            expansion_broker=None,
            execute_stage_fn=mock_execute,
            create_recovery_stage_fn=mock_create,
        )
        assert result["action"] == "abort"

    @patch("mission.recovery_engine.emit_policy_event")
    @patch("mission.recovery_engine.sleep_with_backoff")
    def test_recovery_retry_stage(self, mock_sleep, mock_emit, engine):
        state = _make_state()
        state.transition_to(MissionStatus.RUNNING, "test")

        response = '{"recovery_action": "retry_stage", "diagnosis": "transient"}'
        mock_execute = MagicMock(return_value={"response": response})
        mock_create = MagicMock(return_value={"specialist": "manager"})

        result = engine.handle_stage_failure(
            failed_stage=_make_stage(),
            error_context="timeout",
            mission_state=state,
            assembler=None,
            mission_id="m-test",
            user_id="u1",
            all_artifacts=[],
            expansion_broker=None,
            execute_stage_fn=mock_execute,
            create_recovery_stage_fn=mock_create,
        )
        assert result["action"] == "retry_stage"

    @patch("mission.recovery_engine.emit_policy_event")
    @patch("mission.recovery_engine.sleep_with_backoff")
    def test_recovery_exception_aborts(self, mock_sleep, mock_emit, engine):
        state = _make_state()
        state.transition_to(MissionStatus.RUNNING, "test")

        mock_create = MagicMock(side_effect=RuntimeError("boom"))

        result = engine.handle_stage_failure(
            failed_stage=_make_stage(),
            error_context="error",
            mission_state=state,
            assembler=None,
            mission_id="m-test",
            user_id="u1",
            all_artifacts=[],
            expansion_broker=None,
            execute_stage_fn=MagicMock(),
            create_recovery_stage_fn=mock_create,
        )
        assert result["action"] == "abort"
        assert "Recovery triage itself failed" in result["reason"]


class TestEnqueueToDlq:
    def test_enqueue_basic(self, engine):
        mission = {
            "missionId": "m-dlq-1",
            "status": "failed",
            "error": "test error",
            "stages": [{"id": "s-1", "status": "failed"}],
        }
        dlq_id = engine.enqueue_to_dlq(mission)
        assert dlq_id is not None

    def test_enqueue_suppressed(self, engine):
        mission = {"missionId": "m-dlq-2", "status": "failed", "stages": []}
        result = engine.enqueue_to_dlq(mission, suppress=True)
        assert result is None

    def test_enqueue_no_failed_stage(self, engine):
        mission = {
            "missionId": "m-dlq-3",
            "status": "failed",
            "error": "planning failed",
            "stages": [],
        }
        dlq_id = engine.enqueue_to_dlq(mission)
        assert dlq_id is not None
