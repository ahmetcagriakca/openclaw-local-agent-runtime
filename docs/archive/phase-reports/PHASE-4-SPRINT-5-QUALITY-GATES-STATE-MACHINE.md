# Phase 4 — Sprint 5: Quality Gates + Feedback Loops + Durable Mission Execution

**Date:** 2026-03-23
**Status:** COMPLETE (standalone modules — Controller integration deferred to 5A-3/5B-2)
**Author:** Operator + Claude Opus 4.6
**Scope:** 3 quality gates, 2 feedback loops, 10-state mission state machine, strict ID-based approval store with idempotency

---

## Section 1: Executive Summary

**What changed:** Sprint 5 introduces the governance and durability layers that transform the mission system from a linear pipeline into a cycle-capable, failure-resilient execution engine.

**Before Sprint 5:**
- Stages ran sequentially — pass or fail, no middle ground
- Test failure = mission failure (no rework opportunity)
- Review rejection = mission failure (no feedback path)
- No formal state tracking — crash = lost mission
- Approvals accepted ambiguous "yes/no"

**After Sprint 5:**
- 3 quality gates validate artifacts between stage groups
- Dev-Tester loop allows up to 3 rework cycles before escalation
- Dev-Reviewer loop allows up to 2 rework cycles before escalation
- 10-state mission state machine with valid transition enforcement
- Crash-resumable state with serialization/deserialization
- Strict ID-based approval with paramsHash idempotency and timeout

**Test results:** 42/42 unit tests passed. Regression green (single-agent + mission mode).

**Integration note:** Standalone modules are built and tested. Controller stage loop integration (5A-3: gate injection + loop handling, 5B-2: recovery triage invocation) is deferred to a focused session — the Controller changes are architecturally significant and benefit from isolated implementation.

---

## Section 2: Quality Gates (5A-1)

### 2.1 Three Gates

| Gate | Name | Runs After | Runs Before | Checks |
|------|------|-----------|-------------|--------|
| Gate 1 | Requirements + Design | PO, Analyst, Architect, PM | Developer | requirements_brief schema, analysis recommendation, discovery_map completeness |
| Gate 2 | Code + Test | Developer, Tester | Reviewer | code_delivery files, test_report verdict, critical bugs |
| Gate 3 | Final Review | Reviewer | Manager/Delivery | review_decision, security concerns |

### 2.2 GateResult Structure

```python
@dataclass
class GateResult:
    passed: bool          # True if no blocking issues
    gate_name: str        # "gate_1_requirements_design" etc.
    findings: list        # [{check, status, detail}]
    blocking_issues: list # Critical issues that block progression
    recommendation: str   # "proceed" | "rework" | "abort"
```

### 2.3 Gate Logic Details

**Gate 1 — Requirements + Design:**
- `requirements_brief` must exist and pass schema validation (title, summary, requirements with acceptance_criteria)
- `analysis_report.recommendation` must not be `"reject"`
- `discovery_map` should have `working_set_recommendations.developer` (warn if missing, not blocking)
- Missing requirements_brief → blocking

**Gate 2 — Code + Test:**
- `code_delivery` must exist with `touched_files`
- `test_report` must exist with verdict
- Verdict `"fail"` → blocking
- Verdict `"pass"` or `"conditional_pass"` → pass
- Any critical-severity bugs → blocking

**Gate 3 — Final Review:**
- `review_decision` must exist
- Decision `"approve"` → pass
- Decision `"request_changes"` → fail with recommendation `"rework"`
- Decision `"reject"` → fail with recommendation `"abort"`
- Critical security concerns → blocking

### 2.4 Test Results

| Test | Expected | Result |
|------|----------|--------|
| Gate 1: valid requirements + non-reject analysis | PASS | PASS |
| Gate 1: missing requirements_brief | FAIL + blocking | PASS |
| Gate 1: analysis recommendation "reject" | FAIL | PASS |
| Gate 2: test verdict "pass" | PASS | PASS |
| Gate 2: test verdict "fail" | FAIL + blocking | PASS |
| Gate 2: critical bugs present | FAIL + blocking | PASS |
| Gate 3: decision "approve" | PASS | PASS |
| Gate 3: decision "request_changes" | FAIL + rework | PASS |
| Gate 3: decision "reject" | FAIL + abort | PASS |
| Gate 2: fail has blocking issues | >= 1 blocking | PASS |

**File:** `agent/mission/quality_gates.py`

---

## Section 3: Feedback Loops (5A-2)

### 3.1 Two Loops

| Loop | Max Cycles | Trigger | Rework Path | Escalation |
|------|:----------:|---------|-------------|------------|
| Dev-Tester | 3 | test_report verdict != pass | Developer → Tester | Manager (recovery_triage) |
| Dev-Reviewer | 2 | review_decision != approve | Developer → Reviewer | Manager (recovery_triage) |

### 3.2 Decision Logic

**Dev-Tester Loop:**
- Verdict `pass`/`conditional_pass` → `"proceed"` (move to reviewer)
- Verdict `fail`, cycle <= 3 → `"rework"` (back to developer with bug list)
- Verdict `fail`, cycle > 3 → `"escalate"` (invoke manager)

**Dev-Reviewer Loop:**
- Decision `approve` → `"proceed"` (move to manager/delivery)
- Decision `request_changes`, cycle <= 2 → `"rework"` (back to developer with must-fix findings)
- Decision `request_changes`, cycle > 2 → `"escalate"` (invoke manager)
- Decision `reject` → `"escalate"` (immediate, no rework attempt)

### 3.3 Telemetry Events

| Event | When |
|-------|------|
| `feedback_loop_rework` | Rework cycle triggered (includes loop, cycle, bug/finding count) |
| `feedback_loop_escalated` | Max cycles exceeded or reject (includes reason) |

### 3.4 Test Results

| Test | Expected | Result |
|------|----------|--------|
| Test pass → proceed | proceed | PASS |
| Test fail cycle 1 → rework | rework + bugs | PASS |
| Test fail cycle 1 has bugs | bugs in result | PASS |
| Test fail cycle 4 → escalate | escalate (max 3) | PASS |
| Review approve → proceed | proceed | PASS |
| Review changes cycle 1 → rework | rework + findings | PASS |
| Review changes cycle 3 → escalate | escalate (max 2) | PASS |
| Review reject → escalate | immediate escalate | PASS |
| Stats: dev_test_cycles == 4 | 4 | PASS |

**File:** `agent/mission/feedback_loops.py`

---

## Section 4: Mission State Machine (5B-1)

### 4.1 Ten States

```
PENDING → PLANNING → READY → RUNNING → COMPLETED
                                 ↓
                    WAITING_APPROVAL / WAITING_REWORK /
                    WAITING_TEST / WAITING_REVIEW
                                 ↓
                              FAILED → PLANNING (recovery retry)
                                     → READY (retry stage)
```

| State | Description |
|-------|-------------|
| PENDING | Mission created, not yet started |
| PLANNING | Complexity classification + stage planning |
| READY | Plan validated, stages enriched with working sets |
| RUNNING | Stages executing |
| WAITING_APPROVAL | Stage blocked on approval (high/critical risk tool) |
| WAITING_REWORK | Feedback loop triggered, waiting for rework stage |
| WAITING_TEST | Rework done, waiting for re-test |
| WAITING_REVIEW | Rework done, waiting for re-review |
| COMPLETED | All stages done, all gates passed |
| FAILED | Stage or gate failed (may transition to PLANNING/READY for recovery) |

### 4.2 Valid Transitions

- **PENDING** → PLANNING
- **PLANNING** → READY, FAILED
- **READY** → RUNNING
- **RUNNING** → WAITING_*, COMPLETED, FAILED
- **WAITING_*** → RUNNING (resumed)
- **WAITING_APPROVAL** → FAILED (denied/expired)
- **FAILED** → PLANNING (recovery retry), READY (retry stage)
- **COMPLETED** → (terminal, no transitions)

Invalid transitions are **denied and logged** via telemetry (`invalid_state_transition` event).

### 4.3 Attempt Counters

- Each stage has an attempt counter: `increment_stage_attempt(stage_id)`
- `can_retry_stage(stage_id)` returns False after 3 attempts (configurable via `max_stage_attempts`)
- Prevents infinite retry loops

### 4.4 Serialization

`to_dict()` / `from_dict()` enable crash recovery:
```python
# Save before each stage
state_dict = mission_state.to_dict()
save_to_disk(state_dict)

# Resume after crash
state_dict = load_from_disk(mission_id)
mission_state = MissionState.from_dict(state_dict)
# Resume from mission_state.current_stage_index
```

### 4.5 Test Results

| Test | Expected | Result |
|------|----------|--------|
| PENDING → PLANNING → READY → RUNNING → COMPLETED | Valid path | PASS |
| COMPLETED → RUNNING | Blocked (invalid) | PASS |
| RUNNING → FAILED → PLANNING | Valid (recovery) | PASS |
| RUNNING → WAITING_REWORK → RUNNING | Valid (rework cycle) | PASS |
| FAILED → COMPLETED | Blocked (invalid) | PASS |
| can_retry_stage (initial) | True | PASS |
| can_retry_stage (after 3 attempts) | False | PASS |
| to_dict/from_dict roundtrip: mission_id | Preserved | PASS |
| to_dict/from_dict roundtrip: status | Preserved | PASS |
| to_dict/from_dict roundtrip: attempts | Preserved | PASS |

**File:** `agent/mission/mission_state.py`

---

## Section 5: Approval Store (5C-1)

### 5.1 Strict ID-Based Lifecycle

```
request_approval() → ApprovalRecord with approvalId
  → approve(approvalId) → status: approved
  → deny(approvalId) → status: denied
  → timeout → status: expired (auto)
```

**No ambiguous yes/no accepted.** Only `approve("apr-xxx")` or `deny("apr-xxx")` by exact ID.

### 5.2 Idempotency

`paramsHash` = SHA-256 of tool params (sorted JSON). If the same params are submitted while a pending approval exists, the existing record is returned — no duplicate created.

`check_idempotency(params_hash)` scans history for previously approved identical calls — enables safe re-execution.

### 5.3 ApprovalRecord Fields

| Field | Description |
|-------|-------------|
| approvalId | Unique ID: `apr-{timestamp}-{toolCallId[:8]}` |
| missionId | Parent mission |
| stageId | Which stage requested |
| requestedByRole | Which role triggered the approval |
| toolCallId | Original tool call ID |
| tool | Tool name (e.g., "close_application") |
| paramsHash | SHA-256 of params for idempotency |
| risk | Risk level (low/medium/high/critical) |
| reason | Why approval is needed |
| requestedAt / expiresAt | Request + expiry timestamps |
| status | pending → approved/denied/expired |
| decision / decidedAt / decidedBy | Resolution details |

### 5.4 Telemetry Events

| Event | When |
|-------|------|
| `approval_requested` | New approval created |
| `approval_decided` | Approved, denied, or expired |

### 5.5 Test Results

| Test | Expected | Result |
|------|----------|--------|
| request_approval returns approvalId | apr-* | PASS |
| Status pending after request | pending | PASS |
| approve by exact ID | True, status approved | PASS |
| Status approved after approve | approved | PASS |
| approve nonexistent ID | False | PASS |
| deny by exact ID | True | PASS |
| Idempotency: same params → same record | Same approvalId | PASS |
| Expired approval → cannot approve | False | PASS |
| get_pending → only pending | Filtered | PASS |
| check_idempotency → finds approved | approvalId | PASS |

**File:** `agent/services/approval_store.py`

---

## Section 6: File Map

### New Files

| File | Sub-Sprint | Purpose |
|------|-----------|---------|
| `agent/mission/quality_gates.py` | 5A-1 | 3 quality gate definitions (GateResult) |
| `agent/mission/feedback_loops.py` | 5A-2 | Dev-Tester + Dev-Reviewer rework loop tracker |
| `agent/mission/mission_state.py` | 5B-1 | 10-state machine with transitions + attempt counters |
| `agent/services/approval_store.py` | 5C-1 | Strict ID-based approval + idempotency + timeout |

### No Modified Files

Sprint 5 standalone modules do not modify existing files. Controller integration (5A-3, 5B-2) is deferred.

---

## Section 7: Integration Status

### Completed (Standalone, Tested)

| Component | Tests | Status |
|-----------|:-----:|--------|
| Gate 1: Requirements + Design | 3/3 | Ready for Controller |
| Gate 2: Code + Test | 3/3 | Ready for Controller |
| Gate 3: Final Review | 4/4 | Ready for Controller |
| Dev-Tester feedback loop | 4/4 | Ready for Controller |
| Dev-Reviewer feedback loop | 5/5 | Ready for Controller |
| Mission state machine | 10/10 | Ready for Controller |
| Approval store | 10/10 | Ready for Controller |

### Deferred to Next Session (Controller Integration)

| Task | Description | Dependency |
|------|-------------|------------|
| 5A-3 | Gate injection into Controller stage loop — insert gate checks after role groups, insert rework stages dynamically | 5A-1, 5A-2 |
| 5B-2 | Recovery triage integration — stage fail triggers manager recovery_triage instead of immediate abort | 5B-1 |

**Why deferred:** Controller integration rewrites the core stage execution loop — from linear `for i, stage in enumerate(stages)` to a state-machine-driven `while current_stage_index < len(stages)` with dynamic stage insertion. This is the highest-risk change in the entire Phase 4 and benefits from a focused session with full regression testing.

---

## Section 8: Telemetry Coverage After Sprint 5

| # | Event | Source | Sprint |
|---|-------|--------|--------|
| 1-6 | Enforcer events (6 types) | Working Set Enforcer | 1H/2C |
| 7-8 | context_read, context_reread | Context Assembler | 2C |
| 9-10 | expansion_requested, expansion_decided | Expansion Broker | 2C |
| 11-12 | mission_completed, mission_failed | Mission Controller | 2C |
| 13 | complexity_classified | Complexity Router | 4 |
| 14-15 | feedback_loop_rework, feedback_loop_escalated | Feedback Loops | **5** |
| 16-17 | mission_state_transition, invalid_state_transition | Mission State | **5** |
| 18-19 | approval_requested, approval_decided | Approval Store | **5** |

**Total: 19 telemetry event types** across all layers, all writing to `logs/policy-telemetry.jsonl`.

---

## Section 9: Sprint 6 Readiness

Sprint 5 delivers all governance and durability components that Sprint 6 (Full Integration Test) requires:

| Component | Status | Controller Integration |
|-----------|--------|----------------------|
| Quality gates (3) | Built + tested | 5A-3 (deferred) |
| Feedback loops (2) | Built + tested | 5A-3 (deferred) |
| Mission state machine | Built + tested | 5B-2 (deferred) |
| Approval store | Built + tested | Available for injection |
| Complexity router | Integrated in Controller | Done (Sprint 4) |
| Discovery → working set | Integrated in Controller | Done (Sprint 4) |
| 9 roles + 10 skills | Integrated in Controller | Done (Sprint 3) |
| Enforcer + Assembler | Integrated in Controller | Done (Sprint 2C) |

**Recommended next steps:**
1. **5A-3 + 5B-2 session** — Controller integration (gate injection + recovery)
2. **Sprint 6** — Full SDLC integration test (trivial/simple/medium/complex + rework + recovery)

---

## Section 10: Commit History

```
27b8dc4 Sprint 5: quality gates + feedback loops + state machine + approval store
```

---

*Phase 4 Sprint 5 Report*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Date: 2026-03-23*
