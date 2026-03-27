"""Sprint 5C Integration Tests - Controller state machine, gates, recovery, approval store.

Converted from custom check() framework to pytest-native assertions.
Original: 56 tests with sys.exit(0/1).
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock

from mission.controller import MISSIONS_DIR, MissionController
from mission.feedback_loops import FeedbackLoop
from mission.mission_state import MissionState, MissionStatus
from mission.quality_gates import check_gate_1, check_gate_2, check_gate_3
from services.approval_store import ApprovalStore

# -- 5C-1: State Machine Unit Tests --


class TestStateMachine:
    def test_initial_state_is_pending(self):
        ms = MissionState("test-mission-001")
        assert ms.status == MissionStatus.PENDING

    def test_pending_to_planning(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        assert ms.status == MissionStatus.PLANNING

    def test_planning_to_ready(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        assert ms.status == MissionStatus.READY

    def test_ready_to_running(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        assert ms.status == MissionStatus.RUNNING

    def test_running_to_completed(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        assert ms.status == MissionStatus.COMPLETED

    def test_transition_log_has_4_entries(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        assert len(ms.transition_log) == 4

    def test_log_entry_has_required_keys(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        assert all(k in ms.transition_log[0] for k in ("from", "to", "reason"))

    def test_to_dict_has_mission_id(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        d = ms.to_dict()
        assert d["missionId"] == "test-mission-001"

    def test_to_dict_has_status(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        d = ms.to_dict()
        assert d["status"] == "completed"

    def test_to_dict_has_transition_log(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        d = ms.to_dict()
        assert len(d["transitionLog"]) == 4

    def test_from_dict_roundtrip(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        d = ms.to_dict()
        ms2 = MissionState.from_dict(d)
        assert ms2.status == MissionStatus.COMPLETED

    def test_from_dict_mission_id(self):
        ms = MissionState("test-mission-001")
        ms.transition_to(MissionStatus.PLANNING, "mission started")
        ms.transition_to(MissionStatus.READY, "planned 5 stages")
        ms.transition_to(MissionStatus.RUNNING, "executing stages")
        ms.transition_to(MissionStatus.COMPLETED, "all stages done")
        d = ms.to_dict()
        ms2 = MissionState.from_dict(d)
        assert ms2.mission_id == "test-mission-001"

    def test_invalid_transition_rejected(self):
        ms = MissionState("test-invalid")
        ms.transition_to(MissionStatus.COMPLETED, "skip all")
        assert ms.status == MissionStatus.PENDING

    def test_first_attempt_returns_1(self):
        ms = MissionState("test-retries")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        assert ms.increment_stage_attempt("stage-1") == 1

    def test_can_retry_after_1_attempt(self):
        ms = MissionState("test-retries")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        ms.increment_stage_attempt("stage-1")
        assert ms.can_retry_stage("stage-1") is True

    def test_cannot_retry_after_3_attempts(self):
        ms = MissionState("test-retries")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        ms.increment_stage_attempt("stage-1")
        ms.increment_stage_attempt("stage-1")
        ms.increment_stage_attempt("stage-1")
        assert ms.can_retry_stage("stage-1") is False

    def test_4th_attempt_returns_4(self):
        ms = MissionState("test-retries")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        ms.increment_stage_attempt("stage-1")
        ms.increment_stage_attempt("stage-1")
        ms.increment_stage_attempt("stage-1")
        assert ms.increment_stage_attempt("stage-1") == 4


class TestStatePersistence:
    def test_state_file_created(self):
        controller = MissionController()
        ms = MissionState("test-persist-001")
        ms.transition_to(MissionStatus.PLANNING, "test")
        controller._persist_mission_state(ms)
        state_path = os.path.join(MISSIONS_DIR, "test-persist-001-state.json")
        try:
            assert os.path.exists(state_path)
        finally:
            if os.path.exists(state_path):
                os.remove(state_path)

    def test_saved_state_has_mission_id(self):
        controller = MissionController()
        ms = MissionState("test-persist-002")
        ms.transition_to(MissionStatus.PLANNING, "test")
        controller._persist_mission_state(ms)
        state_path = os.path.join(MISSIONS_DIR, "test-persist-002-state.json")
        try:
            with open(state_path) as f:
                saved = json.load(f)
            assert saved["missionId"] == "test-persist-002"
        finally:
            if os.path.exists(state_path):
                os.remove(state_path)

    def test_saved_state_has_status(self):
        controller = MissionController()
        ms = MissionState("test-persist-003")
        ms.transition_to(MissionStatus.PLANNING, "test")
        controller._persist_mission_state(ms)
        state_path = os.path.join(MISSIONS_DIR, "test-persist-003-state.json")
        try:
            with open(state_path) as f:
                saved = json.load(f)
            assert saved["status"] == "planning"
        finally:
            if os.path.exists(state_path):
                os.remove(state_path)


# -- 5C-2: Quality Gates + Feedback Loops --


class TestQualityGates:
    def _make_mock_assembler(self):
        mock = MagicMock()
        mock.artifacts = {}
        return mock

    def test_gate_1_returns_gate_result(self):
        gate1 = check_gate_1({}, self._make_mock_assembler())
        assert hasattr(gate1, "passed")

    def test_gate_1_has_recommendation(self):
        gate1 = check_gate_1({}, self._make_mock_assembler())
        assert gate1.recommendation in ("proceed", "rework", "abort")

    def test_gate_2_returns_gate_result(self):
        gate2 = check_gate_2({}, self._make_mock_assembler())
        assert hasattr(gate2, "passed")

    def test_gate_3_returns_gate_result(self):
        gate3 = check_gate_3({}, self._make_mock_assembler())
        assert hasattr(gate3, "passed")


class TestFeedbackLoops:
    def test_initial_dev_test_count_is_0(self):
        fl = FeedbackLoop("test-fl-001")
        assert fl.dev_test_count == 0

    def test_pass_proceeds(self):
        fl = FeedbackLoop("test-fl-001")
        result = fl.evaluate_test_result({"verdict": "pass"})
        assert result["action"] == "proceed"

    def test_dev_test_count_unchanged_after_pass(self):
        fl = FeedbackLoop("test-fl-001")
        fl.evaluate_test_result({"verdict": "pass"})
        assert fl.dev_test_count == 0

    def test_fail_reworks(self):
        fl = FeedbackLoop("test-fl-001")
        result = fl.evaluate_test_result({"verdict": "fail", "bugs": ["bug1"]})
        assert result["action"] == "rework"

    def test_rework_has_cycle_count(self):
        fl = FeedbackLoop("test-fl-001")
        result = fl.evaluate_test_result({"verdict": "fail", "bugs": ["bug1"]})
        assert "cycle" in result

    def test_review_approve_proceeds(self):
        fl = FeedbackLoop("test-fl-001")
        result = fl.evaluate_review_result({"decision": "approve"})
        assert result["action"] == "proceed"

    def test_review_request_changes_reworks(self):
        fl = FeedbackLoop("test-fl-001")
        result = fl.evaluate_review_result({
            "decision": "request_changes",
            "findings": [{"severity": "critical", "description": "test"}]
        })
        assert result["action"] == "rework"

    def test_review_reject_escalates(self):
        fl = FeedbackLoop("test-fl-001")
        result = fl.evaluate_review_result({"decision": "reject"})
        assert result["action"] == "escalate"

    def test_escalation_after_max_cycles(self):
        fl = FeedbackLoop("test-fl-002")
        for _ in range(3):
            fl.evaluate_test_result({"verdict": "fail", "bugs": ["b"]})
        result = fl.evaluate_test_result({"verdict": "fail", "bugs": ["b"]})
        assert result["action"] == "escalate"

    def test_get_stats_has_dev_test_cycles(self):
        fl = FeedbackLoop("test-fl-002")
        fl.evaluate_test_result({"verdict": "fail", "bugs": ["b"]})
        stats = fl.get_stats()
        assert "dev_test_cycles" in stats

    def test_get_stats_has_total_reworks(self):
        fl = FeedbackLoop("test-fl-002")
        fl.evaluate_test_result({"verdict": "fail", "bugs": ["b"]})
        stats = fl.get_stats()
        assert "total_reworks" in stats


class TestGateCheckIntegration:
    def test_developer_role_proceeds(self):
        ctrl = MissionController()
        ctrl._gate_1_checked = False
        ctrl._gate_2_checked = False
        ctrl._gate_3_checked = False
        ctrl._feedback_loop = None

        mock_assembler = MagicMock()
        mock_assembler.artifacts = {}

        ms = MissionState("test-gate-001")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")

        action = ctrl._check_gates_and_loops(
            role="developer",
            completed_roles={"developer"},
            assembler=mock_assembler,
            stages=[{"id": "s1", "specialist": "developer"}],
            current_index=0,
            mission_state=ms,
            mission_id="test-gate-001"
        )
        assert action == "proceed"

    def test_rework_creates_2_stages(self):
        ctrl = MissionController()
        rework = ctrl._create_rework_stages(
            {"id": "stage-4", "specialist": "tester"},
            {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
            "developer", "tester"
        )
        assert len(rework) == 2

    def test_rework_first_is_developer(self):
        ctrl = MissionController()
        rework = ctrl._create_rework_stages(
            {"id": "stage-4", "specialist": "tester"},
            {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
            "developer", "tester"
        )
        assert rework[0]["specialist"] == "developer"

    def test_rework_second_is_tester(self):
        ctrl = MissionController()
        rework = ctrl._create_rework_stages(
            {"id": "stage-4", "specialist": "tester"},
            {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
            "developer", "tester"
        )
        assert rework[1]["specialist"] == "tester"

    def test_rework_has_is_rework_flag(self):
        ctrl = MissionController()
        rework = ctrl._create_rework_stages(
            {"id": "stage-4", "specialist": "tester"},
            {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
            "developer", "tester"
        )
        assert rework[0]["is_rework"] is True

    def test_rework_has_rework_cycle(self):
        ctrl = MissionController()
        rework = ctrl._create_rework_stages(
            {"id": "stage-4", "specialist": "tester"},
            {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
            "developer", "tester"
        )
        assert rework[0]["rework_cycle"] == 1

    def test_rework_has_working_set(self):
        ctrl = MissionController()
        rework = ctrl._create_rework_stages(
            {"id": "stage-4", "specialist": "tester"},
            {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
            "developer", "tester"
        )
        assert rework[0]["working_set"] is not None


# -- 5C-3: Recovery Triage --


class TestRecoveryTriage:
    def test_3_attempts_exhausted(self):
        ms = MissionState("test-recovery-001")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        for _ in range(3):
            ms.increment_stage_attempt("stage-fail")
        assert not ms.can_retry_stage("stage-fail")

    def test_exhausted_budget_aborts(self):
        ctrl = MissionController()
        ctrl._gate_1_checked = False
        ctrl._gate_2_checked = False
        ctrl._gate_3_checked = False
        ctrl._feedback_loop = None

        mock_assembler = MagicMock()
        mock_assembler.artifacts = {}

        ms = MissionState("test-recovery-002")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        for _ in range(3):
            ms.increment_stage_attempt("stage-fail")

        result = ctrl._handle_stage_failure(
            {"id": "stage-fail"}, "test error", ms, mock_assembler,
            "test-mission", "user1", [], None)
        assert result["action"] == "abort"

    def test_abort_reason_is_max_attempts(self):
        ctrl = MissionController()
        ctrl._gate_1_checked = False
        ctrl._gate_2_checked = False
        ctrl._gate_3_checked = False
        ctrl._feedback_loop = None

        mock_assembler = MagicMock()
        mock_assembler.artifacts = {}

        ms = MissionState("test-recovery-003")
        ms.transition_to(MissionStatus.PLANNING, "")
        ms.transition_to(MissionStatus.READY, "")
        ms.transition_to(MissionStatus.RUNNING, "")
        for _ in range(3):
            ms.increment_stage_attempt("stage-fail")

        result = ctrl._handle_stage_failure(
            {"id": "stage-fail"}, "test error", ms, mock_assembler,
            "test-mission", "user1", [], None)
        assert "max_attempts" in result["reason"]

    def test_find_stage_index(self):
        ctrl = MissionController()
        stages = [{"id": "stage-1"}, {"id": "stage-2"}, {"id": "stage-3"}]
        assert ctrl._find_stage_index(stages, "stage-2") == 1

    def test_find_nonexistent_stage_returns_none(self):
        ctrl = MissionController()
        stages = [{"id": "stage-1"}, {"id": "stage-2"}, {"id": "stage-3"}]
        assert ctrl._find_stage_index(stages, "stage-99") is None

    def test_latest_artifact_data(self):
        ctrl = MissionController()
        mock_assembler = MagicMock()
        mock_assembler.artifacts = {
            "art-1": {"type": "test_report", "data": {"verdict": "fail", "bugs": ["b1"]}},
            "art-2": {"type": "stage_output", "data": {"response": "ok"}},
            "art-3": {"type": "test_report", "data": {"verdict": "pass"}},
        }
        data = ctrl._get_latest_artifact_data("test_report", mock_assembler)
        assert data.get("verdict") == "pass"

    def test_nonexistent_type_returns_empty_dict(self):
        ctrl = MissionController()
        mock_assembler = MagicMock()
        mock_assembler.artifacts = {
            "art-1": {"type": "test_report", "data": {"verdict": "pass"}},
        }
        data = ctrl._get_latest_artifact_data("nonexistent", mock_assembler)
        assert data == {}

    def test_recovery_stage_is_manager(self):
        ctrl = MissionController()
        recovery = ctrl._create_recovery_stage(
            {"id": "stage-3", "specialist": "developer"}, "test failure")
        assert recovery["specialist"] == "manager"

    def test_recovery_has_is_recovery_flag(self):
        ctrl = MissionController()
        recovery = ctrl._create_recovery_stage(
            {"id": "stage-3", "specialist": "developer"}, "test failure")
        assert recovery["is_recovery"] is True

    def test_recovery_has_working_set(self):
        ctrl = MissionController()
        recovery = ctrl._create_recovery_stage(
            {"id": "stage-3", "specialist": "developer"}, "test failure")
        assert recovery["working_set"] is not None

    def test_recovery_id_contains_recovery(self):
        ctrl = MissionController()
        recovery = ctrl._create_recovery_stage(
            {"id": "stage-3", "specialist": "developer"}, "test failure")
        assert "recovery" in recovery["id"]


# -- 5C-4: Approval Store --


class TestApprovalStore:
    def test_record_created(self):
        store = ApprovalStore()
        record = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk: run_powershell", timeout_seconds=300)
        assert record is not None

    def test_record_has_approval_id(self):
        store = ApprovalStore()
        record = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk: run_powershell", timeout_seconds=300)
        assert record.approvalId.startswith("apr-")

    def test_record_status_is_pending(self):
        store = ApprovalStore()
        record = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk: run_powershell", timeout_seconds=300)
        assert record.status == "pending"

    def test_idempotency_no_approved_yet(self):
        store = ApprovalStore()
        store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk: run_powershell", timeout_seconds=300)
        params_hash = hashlib.sha256(
            json.dumps({"command": "Get-Process"}, sort_keys=True).encode()
        ).hexdigest()
        existing = store.check_idempotency(params_hash)
        assert existing is None

    def test_approve_succeeds(self):
        store = ApprovalStore()
        record = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk: run_powershell", timeout_seconds=300)
        approved = store.approve(record.approvalId, decided_by="operator")
        assert approved is True

    def test_idempotency_after_approval(self):
        store = ApprovalStore()
        record = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk: run_powershell", timeout_seconds=300)
        store.approve(record.approvalId, decided_by="operator")
        params_hash = hashlib.sha256(
            json.dumps({"command": "Get-Process"}, sort_keys=True).encode()
        ).hexdigest()
        existing = store.check_idempotency(params_hash)
        assert existing == record.approvalId

    def test_deny_succeeds(self):
        store = ApprovalStore()
        record = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-2",
            role="developer", tool_call_id="tc-002",
            tool="run_powershell", params={"command": "Stop-Process -Force"},
            risk="critical", reason="Critical risk", timeout_seconds=300)
        denied = store.deny(record.approvalId, decided_by="operator")
        assert denied is True

    def test_no_pending_after_decisions(self):
        store = ApprovalStore()
        r1 = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-1",
            role="developer", tool_call_id="tc-001",
            tool="run_powershell", params={"command": "Get-Process"},
            risk="high", reason="High risk", timeout_seconds=300)
        r2 = store.request_approval(
            mission_id="test-mission-001", stage_id="stage-2",
            role="developer", tool_call_id="tc-002",
            tool="run_powershell", params={"command": "Stop-Process"},
            risk="critical", reason="Critical", timeout_seconds=300)
        store.approve(r1.approvalId, decided_by="operator")
        store.deny(r2.approvalId, decided_by="operator")
        pending = store.get_pending()
        assert len(pending) == 0

    def test_get_pending_returns_list(self):
        store = ApprovalStore()
        assert isinstance(store.get_pending(), list)


# -- Summary Integration --


class TestSummaryIntegration:
    def _make_summary(self):
        ctrl = MissionController()
        ctrl._gate_1_checked = True
        ctrl._gate_2_checked = False
        ctrl._gate_3_checked = False
        ctrl._feedback_loop = FeedbackLoop("test-summary")
        ctrl._feedback_loop.evaluate_test_result({"verdict": "fail", "bugs": ["b1"]})

        ms = MissionState("test-summary-001")
        ms.transition_to(MissionStatus.PLANNING, "start")
        ms.transition_to(MissionStatus.READY, "planned")
        ms.transition_to(MissionStatus.RUNNING, "go")
        ms.transition_to(MissionStatus.COMPLETED, "done")

        mock_asm = MagicMock()
        mock_asm.artifacts = {}
        mock_asm.get_consumption_stats.return_value = {}
        mock_eb = MagicMock()
        mock_eb.get_stats.return_value = {}

        mission = {
            "missionId": "test-summary-001",
            "stages": [
                {"id": "s1", "specialist": "analyst", "status": "completed",
                 "tool_call_count": 3, "policy_deny_count": 0},
                {"id": "s1-rework-dev-c1", "specialist": "developer",
                 "status": "completed", "tool_call_count": 2,
                 "policy_deny_count": 0, "is_rework": True, "rework_cycle": 1},
            ],
            "error": None
        }

        ctrl._emit_mission_summary("test-summary-001", mission, mock_asm,
                                   mock_eb, "completed", mission_state=ms)
        return os.path.join(MISSIONS_DIR, "test-summary-001-summary.json")

    def test_summary_file_created(self):
        path = self._make_summary()
        try:
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_summary_has_state_transitions(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert "stateTransitions" in summary
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_summary_has_final_state(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert summary.get("finalState") == "completed"
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_summary_has_attempt_counters(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert "attemptCounters" in summary
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_summary_has_feedback_loop_stats(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert "feedbackLoopStats" in summary
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_summary_has_gates_checked(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert "gatesChecked" in summary
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_summary_gate_1_is_true(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert summary["gatesChecked"]["gate_1"] is True
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_rework_stage_marked_in_summary(self):
        path = self._make_summary()
        try:
            with open(path) as f:
                summary = json.load(f)
            assert any(s.get("isRework") for s in summary["stages"])
        finally:
            if os.path.exists(path):
                os.remove(path)
