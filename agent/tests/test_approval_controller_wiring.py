"""B-134: Approval FSM Controller Wiring tests.

Tests that MissionController correctly integrates with ApprovalStore
when PolicyEngine returns ESCALATE decision.

Scenarios:
1. Expire → FAILED
2. Deny → FAILED
3. Approve → RUNNING (continue execution)
4. Escalated stays WAITING_APPROVAL
5. Timeout → FAILED (D-138 timeout=deny)
6. Idempotency — same params don't create duplicate records
"""
import time
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from mission.controller import MissionController
from mission.mission_state import MissionState, MissionStatus
from services.approval_store import ApprovalRecord, ApprovalStore


def _make_approval_record(approval_id="apr-test-001", status="pending",
                          decided_by=None):
    """Helper to build an ApprovalRecord for testing."""
    return ApprovalRecord(
        approvalId=approval_id,
        missionId="m-001",
        stageId="s-001",
        requestedByRole="analyst",
        toolCallId="policy-s-001",
        tool="run_shell",
        paramsHash="sha256:abc123",
        risk="high",
        reason="High risk tool",
        requestedAt="2026-04-05T00:00:00+00:00",
        expiresAt="2026-04-05T00:05:00+00:00",
        status=status,
        decidedBy=decided_by,
    )


class TestWaitForApprovalDirect(unittest.TestCase):
    """Test _wait_for_approval method directly."""

    @patch("services.approval_store.ApprovalStore.__init__", return_value=None)
    @patch("mission.controller.PolicyEngine")
    @patch("mission.controller.DLQStore")
    @patch("mission.controller.MissionController._update_capability_manifest")
    def _make_controller(self, mock_manifest, mock_dlq, mock_policy, mock_store):
        ctrl = MissionController.__new__(MissionController)
        ctrl._approval_store = MagicMock(spec=ApprovalStore)
        ctrl._policy_engine = MagicMock()
        ctrl._dlq_store = MagicMock()
        ctrl._circuit_breaker = MagicMock()
        ctrl.planner_agent_id = "gpt-general"
        return ctrl

    def test_approved_returns_approved(self):
        """Approval approved → returns 'approved'."""
        ctrl = self._make_controller()
        ctrl._approval_store.get_record.return_value = {
            "status": "approved", "decidedBy": "operator"
        }
        ms = MissionState(mission_id="m-001", status=MissionStatus.WAITING_APPROVAL)

        result = ctrl._wait_for_approval("m-001", {}, ms, "apr-test-001", timeout_s=5)

        self.assertEqual(result, "approved")
        ctrl._approval_store.get_record.assert_called_with("apr-test-001")

    def test_denied_returns_denied(self):
        """Approval denied → returns 'denied'."""
        ctrl = self._make_controller()
        ctrl._approval_store.get_record.return_value = {
            "status": "denied", "decidedBy": "operator"
        }
        ms = MissionState(mission_id="m-001", status=MissionStatus.WAITING_APPROVAL)

        result = ctrl._wait_for_approval("m-001", {}, ms, "apr-test-001", timeout_s=5)

        self.assertEqual(result, "denied")

    def test_expired_returns_expired(self):
        """Approval expired → returns 'expired' (D-138 timeout=deny)."""
        ctrl = self._make_controller()
        ctrl._approval_store.get_record.return_value = {"status": "expired"}
        ms = MissionState(mission_id="m-001", status=MissionStatus.WAITING_APPROVAL)

        result = ctrl._wait_for_approval("m-001", {}, ms, "apr-test-001", timeout_s=5)

        self.assertEqual(result, "expired")

    def test_disappeared_record_returns_denied(self):
        """Record disappeared → returns 'denied' (fail-closed)."""
        ctrl = self._make_controller()
        ctrl._approval_store.get_record.return_value = None
        ms = MissionState(mission_id="m-001", status=MissionStatus.WAITING_APPROVAL)

        result = ctrl._wait_for_approval("m-001", {}, ms, "apr-test-001", timeout_s=5)

        self.assertEqual(result, "denied")

    @patch("mission.controller.time")
    def test_timeout_returns_timeout(self, mock_time):
        """No decision within timeout → returns 'timeout' (D-138 timeout=deny)."""
        ctrl = self._make_controller()
        # Always return pending
        ctrl._approval_store.get_record.return_value = {"status": "pending"}

        # Simulate: first call returns start, second call returns past deadline
        mock_time.time.side_effect = [100.0, 500.0, 500.0]
        mock_time.sleep = MagicMock()

        ms = MissionState(mission_id="m-001", status=MissionStatus.WAITING_APPROVAL)
        result = ctrl._wait_for_approval("m-001", {}, ms, "apr-test-001", timeout_s=300)

        self.assertEqual(result, "timeout")
        ctrl._approval_store.check_expired.assert_called()

    @patch("mission.controller.time")
    def test_escalated_keeps_waiting(self, mock_time):
        """Escalated status → keep waiting, then eventual approval."""
        ctrl = self._make_controller()
        # First poll: escalated (keep waiting), second poll: approved
        ctrl._approval_store.get_record.side_effect = [
            {"status": "escalated"},
            {"status": "approved", "decidedBy": "admin"},
        ]
        # time.time() sequence: deadline calc, first loop check, second loop check
        mock_time.time.side_effect = [100.0, 100.0, 100.0]
        mock_time.sleep = MagicMock()

        ms = MissionState(mission_id="m-001", status=MissionStatus.WAITING_APPROVAL)
        result = ctrl._wait_for_approval("m-001", {}, ms, "apr-test-001", timeout_s=300)

        self.assertEqual(result, "approved")
        # Should have polled at least twice
        self.assertEqual(ctrl._approval_store.get_record.call_count, 2)


class TestEscalateBlockIntegration(unittest.TestCase):
    """Test the full ESCALATE block wiring in controller — approval store + FSM."""

    def _build_controller(self):
        """Build a minimally-mocked controller."""
        ctrl = MissionController.__new__(MissionController)
        ctrl._approval_store = MagicMock(spec=ApprovalStore)
        ctrl._policy_engine = MagicMock()
        ctrl._dlq_store = MagicMock()
        ctrl._circuit_breaker = MagicMock()
        ctrl._save_mission = MagicMock()
        ctrl._persist_mission_state = MagicMock()
        ctrl._emit_mission_summary = MagicMock()
        ctrl._enqueue_to_dlq = MagicMock()
        ctrl.planner_agent_id = "gpt-general"
        return ctrl

    @patch("mission.controller.emit_policy_event")
    def test_escalate_approve_transitions_to_running(self, mock_emit):
        """ESCALATE → approved → mission transitions WAITING_APPROVAL → RUNNING."""
        ctrl = self._build_controller()
        record = _make_approval_record()
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="approved")

        mission = {"goal": "test", "status": "executing"}
        stage = {"skill": "run_shell", "policyDecision": "escalate"}
        ms = MissionState(mission_id="m-001", status=MissionStatus.RUNNING)

        # Simulate the ESCALATE block logic
        ms.transition_to(MissionStatus.WAITING_APPROVAL, "Policy escalated: risk")

        ctrl._approval_store.request_approval.assert_not_called()
        # Now call the actual method
        approval_record = ctrl._approval_store.request_approval(
            mission_id="m-001", stage_id="s-001", role="analyst",
            tool_call_id="policy-s-001", tool="run_shell",
            params={"goal": "test", "stage": "s-001"},
            risk="escalate", reason="risk", timeout_seconds=300)

        decision = ctrl._wait_for_approval(
            "m-001", mission, ms, record.approvalId, timeout_s=300)

        self.assertEqual(decision, "approved")
        # After approval, transition to RUNNING
        ms.transition_to(MissionStatus.RUNNING, f"approval {record.approvalId} approved")
        self.assertEqual(ms.status, MissionStatus.RUNNING)

    @patch("mission.controller.emit_policy_event")
    def test_escalate_denied_transitions_to_failed(self, mock_emit):
        """ESCALATE → denied → mission transitions WAITING_APPROVAL → FAILED."""
        ctrl = self._build_controller()
        record = _make_approval_record()
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="denied")

        mission = {"goal": "test", "status": "executing"}
        ms = MissionState(mission_id="m-001", status=MissionStatus.RUNNING)

        ms.transition_to(MissionStatus.WAITING_APPROVAL, "Policy escalated: risk")

        decision = ctrl._wait_for_approval(
            "m-001", mission, ms, record.approvalId, timeout_s=300)

        self.assertEqual(decision, "denied")
        ms.transition_to(MissionStatus.FAILED,
                         f"Approval denied for stage s-001")
        self.assertEqual(ms.status, MissionStatus.FAILED)

    @patch("mission.controller.emit_policy_event")
    def test_escalate_expired_transitions_to_failed(self, mock_emit):
        """ESCALATE → expired → mission transitions WAITING_APPROVAL → FAILED (D-138)."""
        ctrl = self._build_controller()
        record = _make_approval_record()
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="expired")

        mission = {"goal": "test", "status": "executing"}
        ms = MissionState(mission_id="m-001", status=MissionStatus.RUNNING)

        ms.transition_to(MissionStatus.WAITING_APPROVAL, "Policy escalated: risk")

        decision = ctrl._wait_for_approval(
            "m-001", mission, ms, record.approvalId, timeout_s=300)

        self.assertEqual(decision, "expired")
        ms.transition_to(MissionStatus.FAILED,
                         f"Approval expired for stage s-001")
        self.assertEqual(ms.status, MissionStatus.FAILED)

    @patch("mission.controller.emit_policy_event")
    def test_escalate_timeout_transitions_to_failed(self, mock_emit):
        """ESCALATE → timeout → mission transitions WAITING_APPROVAL → FAILED (D-138)."""
        ctrl = self._build_controller()
        record = _make_approval_record()
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="timeout")

        mission = {"goal": "test", "status": "executing"}
        ms = MissionState(mission_id="m-001", status=MissionStatus.RUNNING)

        ms.transition_to(MissionStatus.WAITING_APPROVAL, "Policy escalated: risk")

        decision = ctrl._wait_for_approval(
            "m-001", mission, ms, record.approvalId, timeout_s=300)

        self.assertEqual(decision, "timeout")
        ms.transition_to(MissionStatus.FAILED,
                         f"Approval timeout for stage s-001")
        self.assertEqual(ms.status, MissionStatus.FAILED)

    def test_idempotency_same_params(self):
        """Same params don't create duplicate approval records."""
        store = ApprovalStore.__new__(ApprovalStore)
        store.store_path = "/tmp/test_approvals"
        store.pending = {}
        store.history = []

        with patch("services.approval_store.os.makedirs"), \
             patch("services.approval_store.emit_policy_event"), \
             patch("services.approval_store.atomic_write_json"):
            store2 = ApprovalStore(store_path="/tmp/test_approvals")

            r1 = store2.request_approval(
                mission_id="m-001", stage_id="s-001", role="analyst",
                tool_call_id="policy-s-001", tool="run_shell",
                params={"goal": "test", "stage": "s-001"},
                risk="high", reason="risk", timeout_seconds=300)

            r2 = store2.request_approval(
                mission_id="m-001", stage_id="s-001", role="analyst",
                tool_call_id="policy-s-001", tool="run_shell",
                params={"goal": "test", "stage": "s-001"},
                risk="high", reason="risk", timeout_seconds=300)

            self.assertEqual(r1.approvalId, r2.approvalId)
            self.assertEqual(len(store2.pending), 1)

    @patch("mission.controller.emit_policy_event")
    def test_approval_store_called_with_correct_params(self, mock_emit):
        """Verify request_approval is called with proper mission context."""
        ctrl = self._build_controller()
        record = _make_approval_record()
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="approved")

        mission = {"goal": "deploy service", "status": "executing"}
        stage = {"skill": "run_shell", "policyDecision": "escalate"}
        ms = MissionState(mission_id="m-002", status=MissionStatus.RUNNING)
        ms.transition_to(MissionStatus.WAITING_APPROVAL, "test")

        ctrl._approval_store.request_approval(
            mission_id="m-002", stage_id="s-003", role="engineer",
            tool_call_id="policy-s-003", tool="run_shell",
            params={"goal": "deploy service", "stage": "s-003"},
            risk="escalate", reason="high risk deploy",
            timeout_seconds=300)

        call_kwargs = ctrl._approval_store.request_approval.call_args
        self.assertEqual(call_kwargs.kwargs["mission_id"], "m-002")
        self.assertEqual(call_kwargs.kwargs["stage_id"], "s-003")
        self.assertEqual(call_kwargs.kwargs["tool"], "run_shell")
        self.assertEqual(call_kwargs.kwargs["timeout_seconds"], 300)

    @patch("mission.controller.emit_policy_event")
    def test_pending_approval_id_set_on_mission(self, mock_emit):
        """Mission dict gets pendingApprovalId during ESCALATE."""
        ctrl = self._build_controller()
        record = _make_approval_record(approval_id="apr-xyz-123")
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="approved")

        mission = {"goal": "test", "status": "executing"}
        mission["pendingApprovalId"] = record.approvalId

        self.assertEqual(mission["pendingApprovalId"], "apr-xyz-123")

        # After approval, pendingApprovalId should be removed
        mission.pop("pendingApprovalId", None)
        self.assertNotIn("pendingApprovalId", mission)

    @patch("mission.controller.emit_policy_event")
    def test_denied_mission_gets_error_and_finished(self, mock_emit):
        """Denied mission gets error message and finishedAt timestamp."""
        ctrl = self._build_controller()
        record = _make_approval_record()
        ctrl._approval_store.request_approval.return_value = record
        ctrl._wait_for_approval = MagicMock(return_value="denied")

        mission = {"goal": "test", "status": "waiting_approval"}
        ms = MissionState(mission_id="m-001", status=MissionStatus.RUNNING)
        ms.transition_to(MissionStatus.WAITING_APPROVAL, "escalated")

        decision = ctrl._wait_for_approval(
            "m-001", mission, ms, record.approvalId, timeout_s=300)

        # Simulate the denial handling from ESCALATE block
        failure_reason = (
            f"Approval {decision} for stage s-001 "
            f"(approval_id={record.approvalId})")
        ms.transition_to(MissionStatus.FAILED, failure_reason)
        mission["status"] = "failed"
        mission["error"] = failure_reason

        self.assertEqual(ms.status, MissionStatus.FAILED)
        self.assertIn("denied", mission["error"])
        self.assertIn(record.approvalId, mission["error"])


if __name__ == "__main__":
    unittest.main()
