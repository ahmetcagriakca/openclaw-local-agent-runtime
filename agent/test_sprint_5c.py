"""Sprint 5C Integration Tests — Controller state machine, gates, recovery, approval store."""
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mission.mission_state import MissionState, MissionStatus
from mission.quality_gates import check_gate_1, check_gate_2, check_gate_3
from mission.feedback_loops import FeedbackLoop
from services.approval_store import ApprovalStore
from mission.controller import MissionController, MISSIONS_DIR

PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")


# ── 5C-1: State Machine Unit Tests ───────────────────────────────
print("\n=== 5C-1: State Machine ===")

ms = MissionState("test-mission-001")
check("Initial state is PENDING", ms.status == MissionStatus.PENDING)

ms.transition_to(MissionStatus.PLANNING, "mission started")
check("PENDING->PLANNING", ms.status == MissionStatus.PLANNING)

ms.transition_to(MissionStatus.READY, "planned 5 stages")
check("PLANNING->READY", ms.status == MissionStatus.READY)

ms.transition_to(MissionStatus.RUNNING, "executing stages")
check("READY->RUNNING", ms.status == MissionStatus.RUNNING)

ms.transition_to(MissionStatus.COMPLETED, "all stages done")
check("RUNNING->COMPLETED", ms.status == MissionStatus.COMPLETED)

check("Transition log has 4 entries", len(ms.transition_log) == 4)
check("Each log entry has from/to/reason",
      all(k in ms.transition_log[0] for k in ("from", "to", "reason")))

# Serialization
d = ms.to_dict()
check("to_dict has missionId", d["missionId"] == "test-mission-001")
check("to_dict has status", d["status"] == "completed")
check("to_dict has transitionLog", len(d["transitionLog"]) == 4)

ms2 = MissionState.from_dict(d)
check("from_dict roundtrip", ms2.status == MissionStatus.COMPLETED)
check("from_dict mission_id", ms2.mission_id == "test-mission-001")

# Invalid transition
ms3 = MissionState("test-invalid")
result = ms3.transition_to(MissionStatus.COMPLETED, "skip all")
check("Invalid PENDING->COMPLETED rejected", ms3.status == MissionStatus.PENDING)

# Attempt counters
ms4 = MissionState("test-retries")
ms4.transition_to(MissionStatus.PLANNING, "")
ms4.transition_to(MissionStatus.READY, "")
ms4.transition_to(MissionStatus.RUNNING, "")

check("First attempt returns 1", ms4.increment_stage_attempt("stage-1") == 1)
check("Can retry after 1 attempt", ms4.can_retry_stage("stage-1") is True)
ms4.increment_stage_attempt("stage-1")
ms4.increment_stage_attempt("stage-1")
check("Cannot retry after 3 attempts", ms4.can_retry_stage("stage-1") is False)
check("4th attempt returns 4", ms4.increment_stage_attempt("stage-1") == 4)

# State persistence
print("\n--- State Persistence ---")
controller = MissionController()
ms5 = MissionState("test-persist-001")
ms5.transition_to(MissionStatus.PLANNING, "test")
controller._persist_mission_state(ms5)
state_path = os.path.join(MISSIONS_DIR, "test-persist-001-state.json")
check("State file created", os.path.exists(state_path))
if os.path.exists(state_path):
    with open(state_path) as f:
        saved = json.load(f)
    check("Saved state has missionId", saved["missionId"] == "test-persist-001")
    check("Saved state has status", saved["status"] == "planning")
    os.remove(state_path)

# ── 5C-2: Quality Gates + Feedback Loops ─────────────────────────
print("\n=== 5C-2: Quality Gates + Feedback Loops ===")

# Gate results structure
from unittest.mock import MagicMock

mock_assembler = MagicMock()
mock_assembler.artifacts = {}

gate1 = check_gate_1({}, mock_assembler)
check("Gate 1 returns GateResult", hasattr(gate1, 'passed'))
check("Gate 1 has recommendation", gate1.recommendation in
      ("proceed", "rework", "abort"))

gate2 = check_gate_2({}, mock_assembler)
check("Gate 2 returns GateResult", hasattr(gate2, 'passed'))

gate3 = check_gate_3({}, mock_assembler)
check("Gate 3 returns GateResult", hasattr(gate3, 'passed'))

# Feedback loop - test evaluation
fl = FeedbackLoop("test-fl-001")
check("FeedbackLoop initial dev_test_count=0", fl.dev_test_count == 0)

# Test pass -> proceed
result = fl.evaluate_test_result({"verdict": "pass"})
check("Test pass -> proceed", result["action"] == "proceed")
check("dev_test_count unchanged after pass", fl.dev_test_count == 0)

# Test fail -> rework
result = fl.evaluate_test_result({"verdict": "fail", "bugs": ["bug1"]})
check("Test fail -> rework", result["action"] == "rework")
check("Rework has cycle count", "cycle" in result)

# Review approve -> proceed
result = fl.evaluate_review_result({"decision": "approve"})
check("Review approve -> proceed", result["action"] == "proceed")

# Review request_changes -> rework
result = fl.evaluate_review_result({
    "decision": "request_changes",
    "findings": [{"severity": "critical", "description": "test"}]
})
check("Review request_changes -> rework", result["action"] == "rework")

# Review reject -> escalate
result = fl.evaluate_review_result({"decision": "reject"})
check("Review reject -> escalate", result["action"] == "escalate")

# Escalation after max cycles
fl2 = FeedbackLoop("test-fl-002")
for _ in range(3):
    fl2.evaluate_test_result({"verdict": "fail", "bugs": ["b"]})
result = fl2.evaluate_test_result({"verdict": "fail", "bugs": ["b"]})
check("Escalate after max dev-test cycles", result["action"] == "escalate")

# Stats
stats = fl2.get_stats()
check("get_stats has dev_test_cycles", "dev_test_cycles" in stats)
check("get_stats has total_reworks", "total_reworks" in stats)

# Controller gate check method
print("\n--- Gate Check Integration ---")
ctrl = MissionController()
ctrl._gate_1_checked = False
ctrl._gate_2_checked = False
ctrl._gate_3_checked = False
ctrl._feedback_loop = None

ms_gate = MissionState("test-gate-001")
ms_gate.transition_to(MissionStatus.PLANNING, "")
ms_gate.transition_to(MissionStatus.READY, "")
ms_gate.transition_to(MissionStatus.RUNNING, "")

# Gate check with role that doesn't trigger any gate
action = ctrl._check_gates_and_loops(
    role="developer",
    completed_roles={"developer"},
    assembler=mock_assembler,
    stages=[{"id": "s1", "specialist": "developer"}],
    current_index=0,
    mission_state=ms_gate,
    mission_id="test-gate-001"
)
check("Developer role -> proceed (no gate)", action == "proceed")

# Rework stages creation
rework = ctrl._create_rework_stages(
    {"id": "stage-4", "specialist": "tester"},
    {"cycle": 1, "reason": "test bugs", "bugs": ["bug1"]},
    "developer", "tester"
)
check("Rework creates 2 stages", len(rework) == 2)
check("Rework[0] is developer", rework[0]["specialist"] == "developer")
check("Rework[1] is tester", rework[1]["specialist"] == "tester")
check("Rework has is_rework flag", rework[0]["is_rework"] is True)
check("Rework has rework_cycle", rework[0]["rework_cycle"] == 1)
check("Rework has working_set", rework[0]["working_set"] is not None)

# Recovery stage creation
recovery = ctrl._create_recovery_stage(
    {"id": "stage-3", "specialist": "developer"}, "test failure")
check("Recovery stage is manager", recovery["specialist"] == "manager")
check("Recovery has is_recovery flag", recovery["is_recovery"] is True)
check("Recovery has working_set", recovery["working_set"] is not None)
check("Recovery id contains 'recovery'", "recovery" in recovery["id"])

# ── 5C-3: Recovery Triage ────────────────────────────────────────
print("\n=== 5C-3: Recovery Triage ===")

# Max attempts -> abort
ms_rec = MissionState("test-recovery-001")
ms_rec.transition_to(MissionStatus.PLANNING, "")
ms_rec.transition_to(MissionStatus.READY, "")
ms_rec.transition_to(MissionStatus.RUNNING, "")

# Exhaust attempts
for _ in range(3):
    ms_rec.increment_stage_attempt("stage-fail")
check("3 attempts exhausted", not ms_rec.can_retry_stage("stage-fail"))

# _handle_stage_failure with exhausted budget -> abort
recovery_result = ctrl._handle_stage_failure(
    {"id": "stage-fail"}, "test error", ms_rec, mock_assembler,
    "test-mission", "user1", [], None)
check("Exhausted budget -> abort", recovery_result["action"] == "abort")
check("Reason is max_attempts", "max_attempts" in recovery_result["reason"])

# _find_stage_index
stages = [{"id": "stage-1"}, {"id": "stage-2"}, {"id": "stage-3"}]
check("Find stage-2 -> index 1", ctrl._find_stage_index(stages, "stage-2") == 1)
check("Find nonexistent -> None", ctrl._find_stage_index(stages, "stage-99") is None)

# _get_latest_artifact_data
mock_assembler2 = MagicMock()
mock_assembler2.artifacts = {
    "art-1": {"type": "test_report", "data": {"verdict": "fail", "bugs": ["b1"]}},
    "art-2": {"type": "stage_output", "data": {"response": "ok"}},
    "art-3": {"type": "test_report", "data": {"verdict": "pass"}},
}
data = ctrl._get_latest_artifact_data("test_report", mock_assembler2)
check("Latest test_report is art-3", data.get("verdict") == "pass")

data2 = ctrl._get_latest_artifact_data("nonexistent", mock_assembler2)
check("Nonexistent type -> empty dict", data2 == {})

# ── 5C-4: Approval Store ─────────────────────────────────────────
print("\n=== 5C-4: Approval Store ===")

store = ApprovalStore()

# Request approval
record = store.request_approval(
    mission_id="test-mission-001",
    stage_id="stage-1",
    role="developer",
    tool_call_id="tc-001",
    tool="run_powershell",
    params={"command": "Get-Process"},
    risk="high",
    reason="High risk: run_powershell",
    timeout_seconds=300
)
check("Record created", record is not None)
check("Record has approvalId", record.approvalId.startswith("apr-"))
check("Record status is pending", record.status == "pending")

# Idempotency — same params should return existing
import hashlib
params_hash = hashlib.sha256(
    json.dumps({"command": "Get-Process"}, sort_keys=True).encode()
).hexdigest()
existing = store.check_idempotency(params_hash)
check("Idempotency: no approved yet -> None", existing is None)

# Approve
approved = store.approve(record.approvalId, decided_by="operator")
check("Approve succeeded", approved is True)

# Check idempotency after approval
existing = store.check_idempotency(params_hash)
check("Idempotency: approved -> returns ID", existing == record.approvalId)

# Deny flow
record2 = store.request_approval(
    mission_id="test-mission-001",
    stage_id="stage-2",
    role="developer",
    tool_call_id="tc-002",
    tool="run_powershell",
    params={"command": "Stop-Process -Force"},
    risk="critical",
    reason="Critical risk",
    timeout_seconds=300
)
denied = store.deny(record2.approvalId, decided_by="operator")
check("Deny succeeded", denied is True)

# Pending list
pending = store.get_pending()
check("No pending after decisions", len(pending) == 0)

# Stats
stats_store = store.get_pending()
check("get_pending returns list", isinstance(stats_store, list))

# ── 5C Controller Integration: _emit_mission_summary ──────────────
print("\n=== Summary Integration ===")

ctrl2 = MissionController()
ctrl2._gate_1_checked = True
ctrl2._gate_2_checked = False
ctrl2._gate_3_checked = False
ctrl2._feedback_loop = FeedbackLoop("test-summary")
ctrl2._feedback_loop.evaluate_test_result({"verdict": "fail", "bugs": ["b1"]})

ms_sum = MissionState("test-summary-001")
ms_sum.transition_to(MissionStatus.PLANNING, "start")
ms_sum.transition_to(MissionStatus.READY, "planned")
ms_sum.transition_to(MissionStatus.RUNNING, "go")
ms_sum.transition_to(MissionStatus.COMPLETED, "done")

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

ctrl2._emit_mission_summary("test-summary-001", mission, mock_asm,
                            mock_eb, "completed", mission_state=ms_sum)

summary_path = os.path.join(MISSIONS_DIR, "test-summary-001-summary.json")
check("Summary file created", os.path.exists(summary_path))
if os.path.exists(summary_path):
    with open(summary_path) as f:
        summary = json.load(f)
    check("Summary has stateTransitions", "stateTransitions" in summary)
    check("Summary has finalState", summary.get("finalState") == "completed")
    check("Summary has attemptCounters", "attemptCounters" in summary)
    check("Summary has feedbackLoopStats", "feedbackLoopStats" in summary)
    check("Summary has gatesChecked", "gatesChecked" in summary)
    check("Summary gatesChecked.gate_1 is True",
          summary["gatesChecked"]["gate_1"] is True)
    check("Rework stage marked in summary",
          any(s.get("isRework") for s in summary["stages"]))
    # Cleanup
    os.remove(summary_path)


# ── Final Report ──────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Sprint 5C Tests: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
print(f"{'='*60}")
if FAIL > 0:
    print("SOME TESTS FAILED — review above output")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
