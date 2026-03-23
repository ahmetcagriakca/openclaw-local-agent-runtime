# Phase 4 -- Sprint 5C: Controller Integration -- Gates, Loops, State Machine, Recovery

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator (AKCA) + Claude Opus 4.6
**Prerequisite:** Sprint 5 standalone modules (42/42 tests)
**Risk Level:** HIGHEST in Phase 4 -- Controller core loop rewritten from linear to state-driven

---

## Section 1: Executive Summary

**What changed:** Sprint 5C rewrites the Controller's core `execute_mission()` loop from a linear `for i, stage in enumerate(stages)` to a state-machine-driven `while current_stage_index < len(stages)` with dynamic stage insertion, quality gate checks, feedback loop evaluation, and recovery triage on failure.

**Before Sprint 5C:**
- Stage loop was a simple `for` iteration -- no dynamic stage insertion possible
- Stage failure = immediate `return mission` with status "failed"
- No quality gate checks between stage groups
- No feedback loop evaluation (rework stages never created at runtime)
- No state machine tracking (mission dict had raw string status)
- Approval store existed standalone but was not wired into the runner

**After Sprint 5C:**
- `while` loop with `current_stage_index` enables dynamic stage insertion (rework, recovery)
- 10-state `MissionState` tracks every transition: PENDING -> PLANNING -> READY -> RUNNING -> COMPLETED
- 3 quality gates fire automatically after their trigger roles complete
- Gate failure invokes FeedbackLoop, which inserts rework stages (dev+tester or dev+reviewer)
- Stage exception triggers `_handle_stage_failure()` (D-056: recovery_triage, not immediate abort)
- Retry budget enforced (max 3 attempts per stage, then abort)
- ApprovalStore records parallel audit trail with idempotency check
- Mission summary includes `stateTransitions`, `finalState`, `attemptCounters`, `feedbackLoopStats`, `gatesChecked`

**Test results:** 70/70 unit + integration tests passed. All Sprint 5 standalone tests (42/42) unaffected.

---

## Section 2: Task 5C-1 -- State Machine Integration

### 2.1 Core Loop Transformation

The fundamental change: `for` -> `while` with explicit index management.

**Before (Sprint 4):**
```python
for i, stage in enumerate(mission["stages"]):
    # ... execute stage ...
    # failure = immediate return
```

**After (Sprint 5C):**
```python
mission_state = MissionState(mission_id)
mission_state.transition_to(MissionStatus.PLANNING, "mission started")
# ... planning ...
mission_state.transition_to(MissionStatus.READY, f"planned {n} stages")
mission_state.transition_to(MissionStatus.RUNNING, "executing stages")

current_stage_index = 0
completed_roles = set()

while current_stage_index < len(mission["stages"]):
    stage = mission["stages"][current_stage_index]
    role = resolve_role(specialist)

    mission_state.current_stage_index = current_stage_index
    mission_state.pending_stage_id = stage_id

    try:
        result = self._execute_stage(...)
        completed_roles.add(role)
        mission_state.last_completed_stage_id = stage_id
    except Exception as e:
        recovery = self._handle_stage_failure(...)  # 5C-3
        if recovery["action"] == "retry_stage":
            continue  # re-run same index

    gate_action = self._check_gates_and_loops(...)  # 5C-2
    if gate_action == "abort":
        break

    current_stage_index += 1

if mission_state.status == MissionStatus.RUNNING:
    mission_state.transition_to(MissionStatus.COMPLETED, "all stages done")
```

### 2.2 State Lifecycle

Every mission now follows this state progression:

```
PENDING -> PLANNING -> READY -> RUNNING -> COMPLETED
                  \        \        |
                   \        \       +-> WAITING_REWORK -> RUNNING (gate 2/3 rework)
                    \        \      +-> WAITING_REVIEW -> RUNNING (gate 3 rework)
                     \        \     +-> FAILED -> READY -> RUNNING (recovery retry)
                      \        +-> FAILED (planning failed)
                       +-> FAILED (stage validation failed)
```

### 2.3 State Persistence

Every stage completion and every failure persists state to disk:

```
logs/missions/{mission_id}-state.json
```

Contents:
```json
{
  "missionId": "mission-20260323...",
  "status": "completed",
  "currentStageIndex": 5,
  "lastCompletedStageId": "stage-5",
  "pendingStageId": "",
  "attemptCounters": {},
  "maxStageAttempts": 3,
  "transitionLog": [
    {"from": "pending", "to": "planning", "reason": "mission started", "timestamp": "..."},
    {"from": "planning", "to": "ready", "reason": "planned 5 stages", "timestamp": "..."},
    ...
  ]
}
```

### 2.4 Summary Enrichment

Mission summary JSON now includes:

| Field | Type | Source |
|-------|------|--------|
| `stateTransitions` | list | `mission_state.transition_log` |
| `finalState` | string | `mission_state.status.value` |
| `attemptCounters` | dict | `mission_state.attempt_counters` |
| `feedbackLoopStats` | dict | `feedback.get_stats()` |
| `gatesChecked` | dict | `{gate_1: bool, gate_2: bool, gate_3: bool}` |

---

## Section 3: Task 5C-2 -- Quality Gate + Feedback Loop Injection

### 3.1 Gate Trigger Points

| Gate | Trigger Role | Trigger Condition | Action on Fail |
|------|-------------|-------------------|----------------|
| Gate 1 | Any planning role | All of `{product-owner, analyst, architect, project-manager}` completed | `abort` or recovery stage |
| Gate 2 | `tester` | After every tester stage | FeedbackLoop -> rework (dev+tester) or escalate |
| Gate 3 | `reviewer` | After every reviewer stage | FeedbackLoop -> rework (dev+reviewer) or escalate |

### 3.2 `_check_gates_and_loops()` Method

New method on `MissionController` (controller.py line 575+):

```python
def _check_gates_and_loops(self, role, completed_roles, assembler,
                           stages, current_index, mission_state,
                           mission_id) -> str:
    """Returns: 'proceed' | 'abort' | 'stages_modified'"""
```

- Gate 1 fires only once (`_gate_1_checked` flag)
- Gate 2/3 fire on every tester/reviewer completion (supports rework cycles)
- On gate fail: calls `FeedbackLoop.evaluate_test_result()` or `evaluate_review_result()`
- Rework action: inserts `_create_rework_stages()` after current index
- Escalate action: inserts `_create_recovery_stage()` (manager)

### 3.3 Dynamic Stage Insertion

When a gate fails and feedback loop returns "rework":

```python
# Gate 2 fail example: tester at index 4
rework_stages = self._create_rework_stages(
    stages[4], loop_result, "developer", "tester")
# Inserts at index 5 and 6:
#   stage-4-rework-developer-c1
#   stage-4-rework-tester-c1
stages.insert(5, rework_stages[0])
stages.insert(6, rework_stages[1])
```

Rework stages have:
- `is_rework: True` flag
- `rework_cycle: N` counter
- Full `working_set` (built via `_build_default_working_set`)
- Instruction derived from feedback reason + bug list

### 3.4 State Transitions During Rework

```
RUNNING -> WAITING_REWORK -> RUNNING    (Gate 2 dev-test rework)
RUNNING -> WAITING_REVIEW -> RUNNING    (Gate 3 dev-review rework)
RUNNING -> FAILED -> RUNNING            (Gate escalation + recovery)
```

### 3.5 Telemetry Events

Each gate check emits:
```json
{
  "event": "quality_gate_checked",
  "mission_id": "...",
  "gate": "gate_1|gate_2|gate_3",
  "passed": true|false,
  "blocking": [...],
  "recommendation": "proceed|rework|abort"
}
```

---

## Section 4: Task 5C-3 -- Recovery Triage Integration

### 4.1 D-056: First Reflex is Recovery, NOT Restart

**Before:** Any exception in `_execute_stage()` immediately set `mission["status"] = "failed"` and returned.

**After:** Exception triggers `_handle_stage_failure()` which:

1. Checks retry budget (`mission_state.can_retry_stage()`)
2. If budget exhausted (3 attempts) -> immediate abort (no recovery call)
3. Otherwise transitions to FAILED, creates a manager recovery_triage stage
4. Executes the recovery stage to get a decision
5. Parses recovery_action from manager response: `retry_stage | abort | escalate_to_operator | retry_from`

### 4.2 Recovery Actions

| Action | Behavior | State Transition |
|--------|----------|-----------------|
| `retry_stage` | `continue` (same index, re-run) | FAILED -> READY -> RUNNING |
| `abort` | Break loop, mission fails | FAILED (terminal) |
| `escalate_to_operator` | Break loop, escalation recorded | FAILED (terminal) |
| `retry_from` | Rewind `current_stage_index` to target | FAILED -> READY -> RUNNING |

### 4.3 Attempt Counter

```python
attempt = mission_state.increment_stage_attempt(stage_id)
if not mission_state.can_retry_stage(stage_id):  # max 3
    return {"action": "abort", "reason": "max_attempts_exceeded"}
```

Each stage has an independent counter. The 4th failure on the same stage always aborts without invoking recovery.

### 4.4 Recovery Self-Failure

If `_handle_stage_failure()` itself throws an exception (e.g., LLM unreachable during recovery), the outer catch returns `{"action": "abort", "reason": "Recovery triage itself failed: ..."}`. No crash, no infinite recursion.

### 4.5 Telemetry Events

```json
{"event": "stage_failed", "mission_id": "...", "stage_id": "...", "role": "...", "error": "..."}
{"event": "recovery_triage_decision", "mission_id": "...", "stage_id": "...", "action": "retry_stage|abort|escalate", "diagnosis": "..."}
```

---

## Section 5: Task 5C-4 -- Approval Store Integration (Lightweight)

### 5.1 Parallel Audit Layer

`ApprovalStore` is wired into `oc_agent_runner_lib.py` as a parallel recording layer. The existing `ApprovalService` (Telegram-based) flow is **unchanged**.

**New flow (oc_agent_runner_lib.py):**

```python
from services.approval_store import ApprovalStore

approval_store = ApprovalStore()  # initialized alongside existing services

# When risk engine returns "require_approval":
params_hash = sha256(json.dumps(params, sort_keys=True)).hexdigest()

# 1. Idempotency check
existing = approval_store.check_idempotency(params_hash)
if existing:
    # Same params already approved -- skip approval flow entirely
    execute_tool()
else:
    # 2. Record in store (parallel)
    store_record = approval_store.request_approval(...)

    # 3. Existing Telegram flow (unchanged)
    approval = approval_service.request_approval(...)

    # 4. Record decision in store
    if approval["approved"]:
        approval_store.approve(store_record.approvalId, ...)
    else:
        approval_store.deny(store_record.approvalId, ...)
```

### 5.2 Idempotency Benefit

When the same tool call with identical parameters is requested multiple times (e.g., retry after recovery), the second call skips the Telegram approval round-trip entirely. The operator is not bothered twice for the same action.

### 5.3 What Is NOT Changed

- Telegram approval flow: untouched
- `ApprovalService` class: untouched
- Risk engine classification: untouched
- Tool execution logic: untouched (only approval path has new branch)

---

## Section 6: Files Changed

| File | Lines Changed | What |
|------|--------------|------|
| `agent/mission/controller.py` | ~350 net new | State machine, while loop, gates, recovery, helpers |
| `agent/oc_agent_runner_lib.py` | ~40 net new | ApprovalStore parallel recording + idempotency |
| `agent/test_sprint_5c.py` | 280 (new file) | 70 integration tests |

### 6.1 New Methods on MissionController

| Method | Task | Purpose |
|--------|------|---------|
| `_persist_mission_state(mission_state)` | 5C-1 | Write state JSON to disk |
| `_check_gates_and_loops(role, ...)` | 5C-2 | Gate check + feedback loop after each stage |
| `_create_rework_stages(failed_stage, loop_result, *roles)` | 5C-2 | Build dev+tester or dev+reviewer rework stages |
| `_create_recovery_stage(failed_stage, failure_reason)` | 5C-2/3 | Build manager recovery_triage stage |
| `_get_latest_artifact_data(artifact_type, assembler)` | 5C-2 | Find most recent artifact of type |
| `_handle_stage_failure(failed_stage, error, ...)` | 5C-3 | D-056 recovery triage handler |
| `_find_stage_index(stages, target_stage_id)` | 5C-3 | Lookup stage by ID for retry_from |

### 6.2 Modified Methods

| Method | Change |
|--------|--------|
| `execute_mission()` | Rewritten: for->while, state machine, gate calls, recovery calls |
| `_emit_mission_summary()` | New `mission_state` param, adds stateTransitions/finalState/feedbackLoopStats/gatesChecked |

---

## Section 7: Test Results

```
=== 5C-1: State Machine ===
  [PASS] Initial state is PENDING
  [PASS] PENDING->PLANNING
  [PASS] PLANNING->READY
  [PASS] READY->RUNNING
  [PASS] RUNNING->COMPLETED
  [PASS] Transition log has 4 entries
  [PASS] Each log entry has from/to/reason
  [PASS] to_dict has missionId
  [PASS] to_dict has status
  [PASS] to_dict has transitionLog
  [PASS] from_dict roundtrip
  [PASS] from_dict mission_id
  [PASS] Invalid PENDING->COMPLETED rejected
  [PASS] First attempt returns 1
  [PASS] Can retry after 1 attempt
  [PASS] Cannot retry after 3 attempts
  [PASS] 4th attempt returns 4
  [PASS] State file created
  [PASS] Saved state has missionId
  [PASS] Saved state has status

=== 5C-2: Quality Gates + Feedback Loops ===
  [PASS] Gate 1 returns GateResult
  [PASS] Gate 1 has recommendation
  [PASS] Gate 2 returns GateResult
  [PASS] Gate 3 returns GateResult
  [PASS] FeedbackLoop initial dev_test_count=0
  [PASS] Test pass -> proceed
  [PASS] dev_test_count unchanged after pass
  [PASS] Test fail -> rework
  [PASS] Rework has cycle count
  [PASS] Review approve -> proceed
  [PASS] Review request_changes -> rework
  [PASS] Review reject -> escalate
  [PASS] Escalate after max dev-test cycles
  [PASS] get_stats has dev_test_cycles
  [PASS] get_stats has total_reworks
  [PASS] Developer role -> proceed (no gate)
  [PASS] Rework creates 2 stages
  [PASS] Rework[0] is developer
  [PASS] Rework[1] is tester
  [PASS] Rework has is_rework flag
  [PASS] Rework has rework_cycle
  [PASS] Rework has working_set
  [PASS] Recovery stage is manager
  [PASS] Recovery has is_recovery flag
  [PASS] Recovery has working_set
  [PASS] Recovery id contains 'recovery'

=== 5C-3: Recovery Triage ===
  [PASS] 3 attempts exhausted
  [PASS] Exhausted budget -> abort
  [PASS] Reason is max_attempts
  [PASS] Find stage-2 -> index 1
  [PASS] Find nonexistent -> None
  [PASS] Latest test_report is art-3
  [PASS] Nonexistent type -> empty dict

=== 5C-4: Approval Store ===
  [PASS] Record created
  [PASS] Record has approvalId
  [PASS] Record status is pending
  [PASS] Idempotency: no approved yet -> None
  [PASS] Approve succeeded
  [PASS] Idempotency: approved -> returns ID
  [PASS] Deny succeeded
  [PASS] No pending after decisions
  [PASS] get_pending returns list

=== Summary Integration ===
  [PASS] Summary file created
  [PASS] Summary has stateTransitions
  [PASS] Summary has finalState
  [PASS] Summary has attemptCounters
  [PASS] Summary has feedbackLoopStats
  [PASS] Summary has gatesChecked
  [PASS] Summary gatesChecked.gate_1 is True
  [PASS] Rework stage marked in summary

============================================================
Sprint 5C Tests: 70 passed, 0 failed, 70 total
============================================================
ALL TESTS PASSED
```

---

## Section 8: Exit Criteria Verification

| # | Criterion | Task | Status | Evidence |
|---|-----------|------|--------|----------|
| 1 | for->while loop transformation | 5C-1 | DONE | controller.py line 97: `while current_stage_index < len(...)` |
| 2 | State transitions logged | 5C-1 | DONE | PENDING->PLANNING->READY->RUNNING->COMPLETED in transition_log |
| 3 | State persisted to disk | 5C-1 | DONE | `{id}-state.json` written after every stage + on failure |
| 4 | Gate 1 checked after planning roles | 5C-2 | DONE | `GATE_1_AFTER` subset check in `_check_gates_and_loops()` |
| 5 | Gate 2 checked after tester | 5C-2 | DONE | `if role == "tester"` trigger |
| 6 | Gate 3 checked after reviewer | 5C-2 | DONE | `if role == "reviewer"` trigger |
| 7 | Gate fail -> rework stages inserted | 5C-2 | DONE | `_create_rework_stages()` + `stages.insert()` |
| 8 | Escalation -> recovery stage inserted | 5C-2 | DONE | `_create_recovery_stage()` for manager |
| 9 | Stage fail -> recovery_triage (D-056) | 5C-3 | DONE | `_handle_stage_failure()` not immediate abort |
| 10 | Retry respects max attempts (3) | 5C-3 | DONE | `can_retry_stage()` returns False after 3 |
| 11 | Recovery failure -> safe abort | 5C-3 | DONE | Outer try/except in `_handle_stage_failure()` |
| 12 | Approval store parallel recording | 5C-4 | DONE | `ApprovalStore` in oc_agent_runner_lib.py |
| 13 | feedbackLoopStats in summary | 5C-2 | DONE | `summary["feedbackLoopStats"]` populated |
| 14 | Regression: trivial mission | All | DONE | No gate triggers for trivial (analyst-only) |
| 15 | Regression: single-agent | All | DONE | `run_agent_with_config()` path unchanged |

---

## Section 9: Architecture Diagram -- New Execution Flow

```
execute_mission(goal)
  |
  v
MissionState(PENDING) -> PLANNING
  |
  v
_plan_mission(goal) -> stages[], complexity
  |
  v
MissionState -> READY -> RUNNING
  |
  v
+--[ while current_stage_index < len(stages) ]--+
|                                                |
|  stage = stages[current_stage_index]           |
|  role = resolve_role(specialist)               |
|                                                |
|  try:                                          |
|    _execute_stage(stage, ...)                   |
|    completed_roles.add(role)                   |
|  except:                                       |
|    _handle_stage_failure() ----+               |
|      |                        |               |
|      retry_stage -> continue  |               |
|      abort/escalate -> break  |               |
|      retry_from -> rewind     |               |
|                               |               |
|  _check_gates_and_loops() ----+               |
|    |                                          |
|    Gate 1 (after planning roles)              |
|    Gate 2 (after tester) -> FeedbackLoop      |
|    Gate 3 (after reviewer) -> FeedbackLoop    |
|    |                                          |
|    proceed -> increment                       |
|    stages_modified -> increment (new stages)  |
|    abort -> break                             |
|                                               |
|  current_stage_index += 1                     |
|  _persist_mission_state()                     |
+-----------------------------------------------+
  |
  v
MissionState -> COMPLETED
_emit_mission_summary() [enriched with state + feedback + gates]
```

---

## Section 10: Risk Assessment and Known Limitations

### 10.1 Addressed Risks

| Risk | Mitigation |
|------|-----------|
| Infinite retry loop | max 3 attempts per stage, hard abort |
| Recovery crashes the mission | `_handle_stage_failure()` has outer try/except |
| Rework stages lack working_set | `_create_rework_stages()` calls `_build_default_working_set()` |
| Gate fires on wrong role | Role-specific `if` checks, Gate 1 has subset guard |
| State inconsistency on crash | State persisted after every stage completion |

### 10.2 Known Limitations

1. **No crash-resume yet:** State is persisted but there is no `resume_mission(mission_id)` method. A crashed mission can be inspected but not restarted from its last state. This is a Sprint 6+ feature.

2. **Recovery stage uses LLM:** `_handle_stage_failure()` calls `_execute_stage()` for the manager recovery_triage. If the LLM provider is down, recovery also fails (caught by outer except, safe abort).

3. **Gate 1 fires only once:** If planning roles are re-executed (e.g., via retry_from), Gate 1 will not re-fire. This is by design for this sprint; re-gate logic can be added later.

4. **Approval store is read-only audit:** The store records decisions in parallel but does not replace the Telegram flow. Full migration is deferred to post-Sprint 6.

---

## Section 11: Sprint 6 Readiness

Sprint 5C unblocks the following Sprint 6 test scenarios:

| Sprint 6 Test | Depends On | Status |
|---------------|-----------|--------|
| T-4: Medium mission (3 gates) | 5C-2 gate injection | UNBLOCKED |
| T-6: Test rework cycle | 5C-2 Gate 2 + FeedbackLoop | UNBLOCKED |
| T-7: Review rework cycle | 5C-2 Gate 3 + FeedbackLoop | UNBLOCKED |
| T-8: Recovery triage | 5C-3 `_handle_stage_failure()` | UNBLOCKED |
| T-9: Approval idempotency | 5C-4 ApprovalStore | UNBLOCKED |

**Sprint 5C is complete. Sprint 6 integration testing may proceed.**
