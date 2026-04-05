"""B-141: Mission Startup Recovery tests — Sprint 65 Task 65.1.

Tests for _recover_orphaned_missions() fail-closed model:
- RUNNING/PLANNING → FAILED
- WAITING_APPROVAL (PENDING/ESCALATED) → expire approval → FAILED
- PAUSED → preserve (no mutation)
- Terminal states → no mutation
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mission.mission_state import MissionState, MissionStatus


def _write_mission(missions_dir, mission_id, status, **extra):
    """Helper: write a mission JSON file."""
    mission = {
        "missionId": mission_id,
        "status": status,
        "goal": "test",
        "userId": "test",
        "sessionId": "test",
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "stages": [],
        "error": None,
        "finishedAt": None,
    }
    mission.update(extra)
    path = os.path.join(missions_dir, f"{mission_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mission, f)
    return path


def _write_state(missions_dir, mission_id, status_value):
    """Helper: write a mission state JSON file."""
    state = MissionState(mission_id)
    state.status = MissionStatus(status_value)
    path = os.path.join(missions_dir, f"{mission_id}-state.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f)
    return path


def _read_mission(missions_dir, mission_id):
    path = os.path.join(missions_dir, f"{mission_id}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _read_state(missions_dir, mission_id):
    path = os.path.join(missions_dir, f"{mission_id}-state.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class TestStartupRecovery(unittest.TestCase):
    """Tests for MissionController._recover_orphaned_missions()."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.missions_dir = self.temp_dir

    def _make_controller(self):
        """Create a MissionController with patched MISSIONS_DIR."""
        from mission.controller import MissionController
        from mission.persistence_adapter import MissionPersistenceAdapter

        ctrl = MissionController.__new__(MissionController)
        ctrl.planner_agent_id = "gpt-general"
        ctrl._dlq_store = MagicMock()
        ctrl._approval_store = MagicMock()
        ctrl._approval_store.pending = {}
        ctrl._policy_engine = MagicMock()
        ctrl._circuit_breaker = MagicMock()
        ctrl._recovery_engine = MagicMock()
        ctrl._persistence = MissionPersistenceAdapter(self.missions_dir)
        # Patch the module-level MISSIONS_DIR so _recover_orphaned_missions
        # scans the temp dir instead of the real logs/missions/
        self._patcher = patch("mission.controller.MISSIONS_DIR", self.missions_dir)
        self._patcher.start()
        return ctrl

    def tearDown(self):
        import shutil
        if hasattr(self, "_patcher"):
            self._patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── RUNNING → FAILED ──

    def test_running_mission_recovered_to_failed(self):
        _write_mission(self.missions_dir, "mission-run-01", "running")
        _write_state(self.missions_dir, "mission-run-01", "running")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)
        m = _read_mission(self.missions_dir, "mission-run-01")
        self.assertEqual(m["status"], "failed")
        self.assertIn("orphaned_by_restart", m["error"])
        self.assertIsNotNone(m["finishedAt"])

    def test_running_state_machine_transitions_to_failed(self):
        _write_mission(self.missions_dir, "mission-run-02", "running")
        _write_state(self.missions_dir, "mission-run-02", "running")
        ctrl = self._make_controller()
        ctrl._recover_orphaned_missions()
        s = _read_state(self.missions_dir, "mission-run-02")
        self.assertEqual(s["status"], "failed")

    # ── PLANNING → FAILED ──

    def test_planning_mission_recovered_to_failed(self):
        _write_mission(self.missions_dir, "mission-plan-01", "planning")
        _write_state(self.missions_dir, "mission-plan-01", "planning")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)
        m = _read_mission(self.missions_dir, "mission-plan-01")
        self.assertEqual(m["status"], "failed")
        self.assertIn("orphaned_by_restart", m["error"])

    # ── EXECUTING → FAILED ──

    def test_executing_mission_recovered_to_failed(self):
        _write_mission(self.missions_dir, "mission-exec-01", "executing")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)
        m = _read_mission(self.missions_dir, "mission-exec-01")
        self.assertEqual(m["status"], "failed")

    # ── WAITING_APPROVAL (PENDING) → FAILED ──

    def test_waiting_approval_pending_recovered_to_failed(self):
        _write_mission(self.missions_dir, "mission-apr-01", "waiting_approval",
                       pendingApprovalId="apr-001")
        _write_state(self.missions_dir, "mission-apr-01", "waiting_approval")

        # Mock pending approval record
        mock_record = MagicMock()
        mock_record.status = "pending"
        mock_record.approvalId = "apr-001"

        ctrl = self._make_controller()
        ctrl._approval_store.pending = {"apr-001": mock_record}

        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)

        m = _read_mission(self.missions_dir, "mission-apr-01")
        self.assertEqual(m["status"], "failed")
        self.assertIn("restart_expired_approval", m["error"])

        # Approval should be expired
        self.assertEqual(mock_record.status, "expired")
        self.assertEqual(mock_record.decision, "expired")
        self.assertEqual(mock_record.decidedBy, "system:startup_recovery")

    # ── WAITING_APPROVAL (ESCALATED) → FAILED ──

    def test_waiting_approval_escalated_recovered_to_failed(self):
        _write_mission(self.missions_dir, "mission-apr-02", "waiting_approval",
                       pendingApprovalId="apr-002")
        _write_state(self.missions_dir, "mission-apr-02", "waiting_approval")

        mock_record = MagicMock()
        mock_record.status = "escalated"
        mock_record.approvalId = "apr-002"

        ctrl = self._make_controller()
        ctrl._approval_store.pending = {"apr-002": mock_record}

        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)

        m = _read_mission(self.missions_dir, "mission-apr-02")
        self.assertIn("restart_expired_escalated_approval", m["error"])

    # ── PAUSED → preserve ──

    def test_paused_mission_not_recovered(self):
        _write_mission(self.missions_dir, "mission-pause-01", "paused")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)
        m = _read_mission(self.missions_dir, "mission-pause-01")
        self.assertEqual(m["status"], "paused")

    # ── Terminal states → no mutation ──

    def test_completed_mission_not_mutated(self):
        _write_mission(self.missions_dir, "mission-done-01", "completed")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)
        m = _read_mission(self.missions_dir, "mission-done-01")
        self.assertEqual(m["status"], "completed")

    def test_failed_mission_not_mutated(self):
        _write_mission(self.missions_dir, "mission-fail-01", "failed")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)

    def test_timed_out_mission_not_mutated(self):
        _write_mission(self.missions_dir, "mission-to-01", "timed_out")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)

    # ── Multiple missions ──

    def test_multiple_missions_mixed_states(self):
        _write_mission(self.missions_dir, "mission-m1", "running")
        _write_mission(self.missions_dir, "mission-m2", "completed")
        _write_mission(self.missions_dir, "mission-m3", "planning")
        _write_mission(self.missions_dir, "mission-m4", "paused")
        _write_mission(self.missions_dir, "mission-m5", "failed")

        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        # Only running + planning should be recovered
        self.assertEqual(count, 2)

    # ── Edge cases ──

    def test_no_missions_returns_zero(self):
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)

    def test_corrupt_json_skipped(self):
        path = os.path.join(self.missions_dir, "mission-corrupt-01.json")
        with open(path, "w") as f:
            f.write("NOT VALID JSON {{{")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)

    def test_state_file_excluded_from_scan(self):
        """State files (-state.json) should not be scanned as missions."""
        _write_mission(self.missions_dir, "mission-x1", "completed")
        _write_state(self.missions_dir, "mission-x1", "completed")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 0)

    def test_mission_without_state_file(self):
        """Recovery should work even without a state machine file."""
        _write_mission(self.missions_dir, "mission-nostate-01", "running")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)
        m = _read_mission(self.missions_dir, "mission-nostate-01")
        self.assertEqual(m["status"], "failed")

    def test_policy_event_emitted_on_recovery(self):
        _write_mission(self.missions_dir, "mission-evt-01", "running")
        ctrl = self._make_controller()
        with patch("mission.controller.emit_policy_event") as mock_emit:
            ctrl._recover_orphaned_missions()
            mock_emit.assert_called()
            call_args = mock_emit.call_args_list
            recovery_calls = [c for c in call_args
                              if c[0][0] == "mission_startup_recovery"]
            self.assertEqual(len(recovery_calls), 1)

    def test_waiting_approval_no_approval_id_still_fails(self):
        """WAITING_APPROVAL without pendingApprovalId → still FAILED."""
        _write_mission(self.missions_dir, "mission-apr-03", "waiting_approval")
        ctrl = self._make_controller()
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)
        m = _read_mission(self.missions_dir, "mission-apr-03")
        self.assertEqual(m["status"], "failed")

    def test_waiting_approval_already_expired_approval(self):
        """If approval already in terminal state, mission still fails."""
        _write_mission(self.missions_dir, "mission-apr-04", "waiting_approval",
                       pendingApprovalId="apr-expired")
        ctrl = self._make_controller()
        ctrl._approval_store.pending = {}  # Not in pending (already expired)
        count = ctrl._recover_orphaned_missions()
        self.assertEqual(count, 1)
        m = _read_mission(self.missions_dir, "mission-apr-04")
        self.assertEqual(m["status"], "failed")


    # ── P2: Recovery invariants (GPT review requirement) ──

    def test_idempotent_repeated_recovery(self):
        """Running recovery twice produces same result — no double mutation."""
        _write_mission(self.missions_dir, "mission-idem-01", "running")
        _write_state(self.missions_dir, "mission-idem-01", "running")
        ctrl = self._make_controller()

        count1 = ctrl._recover_orphaned_missions()
        self.assertEqual(count1, 1)
        m1 = _read_mission(self.missions_dir, "mission-idem-01")
        self.assertEqual(m1["status"], "failed")

        # Second run: already failed → should not re-recover
        count2 = ctrl._recover_orphaned_missions()
        self.assertEqual(count2, 0)
        m2 = _read_mission(self.missions_dir, "mission-idem-01")
        self.assertEqual(m2["status"], "failed")
        # finishedAt should not change
        self.assertEqual(m1["finishedAt"], m2["finishedAt"])

    def test_terminal_completed_unchanged_after_recovery(self):
        """COMPLETED missions remain exactly unchanged after recovery."""
        _write_mission(self.missions_dir, "mission-term-01", "completed",
                       finishedAt="2026-01-01T00:00:00+00:00",
                       error=None)
        ctrl = self._make_controller()
        ctrl._recover_orphaned_missions()
        m = _read_mission(self.missions_dir, "mission-term-01")
        self.assertEqual(m["status"], "completed")
        self.assertEqual(m["finishedAt"], "2026-01-01T00:00:00+00:00")
        self.assertIsNone(m["error"])

    def test_terminal_failed_unchanged_after_recovery(self):
        """FAILED missions remain exactly unchanged after recovery."""
        _write_mission(self.missions_dir, "mission-term-02", "failed",
                       finishedAt="2026-01-01T00:00:00+00:00",
                       error="original error")
        ctrl = self._make_controller()
        ctrl._recover_orphaned_missions()
        m = _read_mission(self.missions_dir, "mission-term-02")
        self.assertEqual(m["status"], "failed")
        self.assertEqual(m["error"], "original error")

    def test_paused_unchanged_after_recovery(self):
        """PAUSED missions remain exactly unchanged — status + error + finishedAt."""
        _write_mission(self.missions_dir, "mission-pause-inv", "paused",
                       finishedAt=None, error=None)
        ctrl = self._make_controller()
        ctrl._recover_orphaned_missions()
        m = _read_mission(self.missions_dir, "mission-pause-inv")
        self.assertEqual(m["status"], "paused")
        self.assertIsNone(m["error"])
        self.assertIsNone(m["finishedAt"])

    def test_waiting_approval_expired_exactly_once(self):
        """WAITING_APPROVAL approval expires exactly once, not repeatedly."""
        _write_mission(self.missions_dir, "mission-apr-once", "waiting_approval",
                       pendingApprovalId="apr-once")
        _write_state(self.missions_dir, "mission-apr-once", "waiting_approval")

        mock_record = MagicMock()
        mock_record.status = "pending"
        mock_record.approvalId = "apr-once"

        ctrl = self._make_controller()
        ctrl._approval_store.pending = {"apr-once": mock_record}

        count1 = ctrl._recover_orphaned_missions()
        self.assertEqual(count1, 1)
        self.assertEqual(mock_record.status, "expired")

        # Second run: mission is now failed → no re-recovery
        count2 = ctrl._recover_orphaned_missions()
        self.assertEqual(count2, 0)

    def test_transition_log_emitted_on_recovery(self):
        """State machine transition log should record recovery transition."""
        _write_mission(self.missions_dir, "mission-log-01", "running")
        _write_state(self.missions_dir, "mission-log-01", "running")
        ctrl = self._make_controller()
        ctrl._recover_orphaned_missions()

        s = _read_state(self.missions_dir, "mission-log-01")
        log = s.get("transitionLog", [])
        self.assertGreater(len(log), 0)
        last_entry = log[-1]
        self.assertEqual(last_entry["from"], "running")
        self.assertEqual(last_entry["to"], "failed")
        self.assertIn("orphaned_by_restart", last_entry["reason"])

    def test_audit_event_contains_required_fields(self):
        """Policy event must contain mission_id, old_status, new_status, reason."""
        _write_mission(self.missions_dir, "mission-audit-01", "planning")
        ctrl = self._make_controller()
        with patch("mission.controller.emit_policy_event") as mock_emit:
            ctrl._recover_orphaned_missions()
            recovery_calls = [c for c in mock_emit.call_args_list
                              if c[0][0] == "mission_startup_recovery"]
            self.assertEqual(len(recovery_calls), 1)
            payload = recovery_calls[0][0][1]
            self.assertIn("mission_id", payload)
            self.assertIn("old_status", payload)
            self.assertIn("new_status", payload)
            self.assertIn("reason", payload)
            self.assertEqual(payload["old_status"], "planning")
            self.assertEqual(payload["new_status"], "failed")


if __name__ == "__main__":
    unittest.main()
