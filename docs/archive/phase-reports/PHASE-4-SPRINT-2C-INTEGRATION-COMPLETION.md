# Phase 4 — Sprint 2C: Integration Completion

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Close 6 integration gaps identified in Sprint 2 report — wire Assembler into Controller, complete telemetry, link Broker to Enforcer

---

## Section 1: Executive Summary

**Problem:** Sprint 2 delivered standalone modules (Assembler, Expansion Broker, Artifact Identity) that passed unit tests but were not connected to the mission pipeline. The Sprint 2 report itself stated: *"Context Assembler is built and tested but not yet wired into the Mission Controller's stage loop."* This single sentence expanded to 6 concrete gaps.

**What was fixed:** All 6 gaps closed in a single session. The Assembler now lives inside the mission stage loop, every enforcer/assembler/broker decision emits structured telemetry, scope-deny messages offer expansion paths, and the naming layer uses D-048 canonical roles.

**Validation:** All unit tests passed, both regression paths green (single-agent + mission mode), structured mission summary produced with consumption stats.

---

## Section 2: Gap Analysis & Resolution

| # | Gap | Risk if Unfixed | Resolution |
|---|-----|-----------------|------------|
| 1 | Assembler not wired to Controller | D-047 headers, tier delivery, reread prevention all paper-only | 2C-1: Assembler created per-mission, artifacts stored after each stage, context delivered via `build_context_for_role()` before each stage |
| 2 | Expansion Broker not linked to Enforcer | Scope-denied agent has no expansion path, stage fails unnecessarily | 2C-2: `expansion_broker` parameter flows through runner → enforcer, deny messages include budget hints |
| 3 | Assembler has no telemetry | Reread tracking invisible, debugging impossible | 2C-3: `context_read` and `context_reread` events emitted on every artifact access |
| 4 | Enforcer missing 2/6 D-055 events | `mutation_surface_mismatch` and `policy_soft_denied` not implemented | 2C-4: Both events added — role-vs-surface authorization check + budget soft-deny |
| 5 | No per-mission structured summary | Quality gates (Sprint 5) need consumption data — no data exists | 2C-5: `{mission_id}-summary.json` with D-055 schema + `mission_completed`/`mission_failed` telemetry |
| 6 | Working set templates use "executor" not "remote-operator" | D-048 violation, Sprint 3 registry collision, audit inconsistency | 2C-6: Alias table, template dict, restrictive fallback for unknown roles |

---

## Section 3: Task Details

### 3.1 Task 2C-1: Assembler → Controller Integration

**The most critical gap.** Without this, the entire distribution economy is decorative.

**Changes to `agent/mission/controller.py`:**

```python
# Mission start — create Assembler + Broker
assembler = ContextAssembler(mission_id)
expansion_broker = ExpansionBroker(mission_id)

# After each stage completes — store output in Assembler
artifact_id = assembler.store_artifact(
    artifact_type="stage_output",
    data={response, stage_id, specialist, tool_calls, raw_artifacts},
    stage_id=stage_id, role=canonical_role, skill="",
    input_artifact_ids=prior_artifact_ids
)
mission["completedArtifactIds"].append(artifact_id)

# Before each stage starts — build tier-based context
context_package = assembler.build_context_for_role(
    role=specialist, skill="", stage_id=stage_id,
    artifact_ids=mission["completedArtifactIds"]
)
artifact_context = self._format_artifact_context(context_package)
```

**New mission state field:** `completedArtifactIds` — grows as stages complete, used by subsequent stages to request context.

**Legacy compatibility:** The old `previous_artifacts` preview mechanism is preserved as fallback. If Assembler context is available, it takes priority. Sprint 3 will remove the legacy path.

### 3.2 Task 2C-2: Expansion Broker → Enforcer Link

**Changes to `agent/context/working_set_enforcer.py`:**

- New `expansion_broker` parameter (optional, default None) on `enforce_working_set()` and sub-functions
- New `_expansion_hint()` helper: builds budget message from broker state
- Scope-deny messages for read, write, and directory operations now include: `"To request access, provide a reason via expansion request. Remaining expansion budget: {remaining}/{max}."`
- When `expansion_broker=None` (single-agent mode): no hint appended, backward compatible

**Parameter flow:**
```
MissionController.execute_mission()
  → expansion_broker = ExpansionBroker(mission_id)
  → _execute_stage(..., expansion_broker=expansion_broker)
    → run_agent_with_config(..., expansion_broker=expansion_broker)
      → enforce_working_set(..., expansion_broker=expansion_broker)
        → _expansion_hint(working_set, expansion_broker)
```

### 3.3 Task 2C-3: Assembler + Broker Telemetry

**Assembler (`agent/context/assembler.py`):**

Every `_log_consumption()` call now emits:
- `context_read` — normal artifact access (includes artifact_id, role, stage_id, tier, mission_id)
- `context_reread` — second full read by same role, auto-downgraded (includes original_requested_tier, downgraded_to)

**Expansion Broker (`agent/context/expansion_broker.py`):**

Every `request_expansion()` call now emits two events:
- `working_set_expansion_requested` — the request (role, files, reason)
- `working_set_expansion_decided` — the decision (granted/denied, deny_reason, remaining_budget)

### 3.4 Task 2C-4: Missing Enforcer Telemetry Events

**D-055 required 6 event types. Sprint 1H delivered 4. Sprint 2C adds the remaining 2.**

| Event Type | When | Sprint |
|------------|------|--------|
| `filesystem_tool_allowed` | Filesystem tool passed all checks | 1H |
| `policy_denied` | Hard deny (scope, forbidden, no path) | 1H |
| `budget_exhausted` | Read budget depleted | 1H |
| `path_resolution_failed` | Canonical resolution returned None | 1H |
| `mutation_surface_mismatch` | Role lacks authority for mutation surface | **2C** |
| `policy_soft_denied` | Non-fatal deny (budget exhaustion) | **2C** |

**`mutation_surface_mismatch` logic:**
- `mutationSurface == "system"` and role != `"remote-operator"` → deny + emit
- `mutationSurface == "code"` and role not in `("developer", "remote-operator", "executor")` → deny + emit

**`policy_soft_denied` logic:**
- Emitted alongside `budget_exhausted` on every budget depletion (both file_read and directory_read)

### 3.5 Task 2C-5: Per-Mission Structured Summary

**New method:** `_emit_mission_summary()` on MissionController

Called at mission completion (success or failure). Produces:

1. **JSON file:** `logs/missions/{mission_id}-summary.json`

```json
{
  "missionId": "mission-20260323121250-21064",
  "completedAt": "2026-03-23T12:13:30+00:00",
  "status": "completed",
  "stages": [
    {"stageId": "stage-1", "role": "analyst", "status": "completed",
     "toolCalls": 1, "policyDenies": 0}
  ],
  "totalPolicyDenies": 0,
  "totalRereads": 0,
  "totalExpansionRequests": 0,
  "totalExpansionGranted": 0,
  "totalExpansionDenied": 0,
  "artifactCount": 2,
  "cacheStats": {"hits": 1, "misses": 0, "entries": 2},
  "consumptionByTier": {"B": 1}
}
```

2. **Telemetry event:** `mission_completed` or `mission_failed` with summary metrics

### 3.6 Task 2C-6: Working Set Template Naming (D-048)

**Before:** `if specialist == "executor":` with hardcoded budgets.

**After:**
- `_ROLE_ALIASES` dict: `{"executor": "remote-operator"}`
- `_WORKING_SET_TEMPLATES` dict: keyed by canonical role, extensible for Sprint 3
- `_build_default_working_set()` resolves aliases, looks up template, falls back to restrictive defaults
- Unknown roles get: 5 file reads, 2 dir reads, 0 expansions (fail-safe)

---

## Section 4: Test Results

### Unit Tests

| Test | Result |
|------|--------|
| executor → remote-operator alias | PASS |
| remote-operator direct | PASS |
| unknown role → restrictive fallback | PASS |
| mutation_surface_mismatch (analyst writing) | PASS |
| budget exhaustion → policy_soft_denied | PASS |
| scope deny with expansion hint | PASS |
| scope deny without broker (backward compat) | PASS |
| context_read in telemetry | PASS |
| context_reread in telemetry | PASS |
| expansion telemetry events | PASS |

### Regression

| Test | Result |
|------|--------|
| Single-agent: `"CPU kullanımı ne?"` | PASS (completed) |
| Mission mode: 2-stage system query | PASS (completed, 2 stages, 4 artifacts) |
| Mission summary JSON produced | PASS (`{id}-summary.json` with all required fields) |

### Telemetry Verification (Live Mission)

```
Event types observed: context_read, policy_denied, mission_completed
Total events: 3
```

- `context_read` — Stage 2 read Stage 1's artifact via Assembler
- `policy_denied` — Enforcer blocked a directory listing outside scope
- `mission_completed` — Structured summary emitted at mission end

---

## Section 5: D-055 Telemetry Coverage — Complete

| # | Event Type | Source | Sprint |
|---|------------|--------|--------|
| 1 | `filesystem_tool_allowed` | Working Set Enforcer | 1H |
| 2 | `policy_denied` | Working Set Enforcer | 1H |
| 3 | `budget_exhausted` | Working Set Enforcer | 1H |
| 4 | `path_resolution_failed` | Working Set Enforcer | 1H |
| 5 | `mutation_surface_mismatch` | Working Set Enforcer | 2C |
| 6 | `policy_soft_denied` | Working Set Enforcer | 2C |
| 7 | `context_read` | Context Assembler | 2C |
| 8 | `context_reread` | Context Assembler | 2C |
| 9 | `working_set_expansion_requested` | Expansion Broker | 2C |
| 10 | `working_set_expansion_decided` | Expansion Broker | 2C |
| 11 | `mission_completed` | Mission Controller | 2C |
| 12 | `mission_failed` | Mission Controller | 2C |

All events write to `logs/policy-telemetry.jsonl` as single-line JSON objects with `timestamp`, `event`, and context-specific fields.

---

## Section 6: File Changes

| File | Task | Change |
|------|------|--------|
| `agent/mission/controller.py` | 2C-1, 2C-5, 2C-6 | Assembler + Broker instantiation, stage loop integration, `_format_artifact_context()`, `_emit_mission_summary()`, template dict + alias table |
| `agent/context/working_set_enforcer.py` | 2C-2, 2C-4 | `expansion_broker` param, `_expansion_hint()`, `mutation_surface_mismatch` + `policy_soft_denied` events |
| `agent/context/assembler.py` | 2C-3 | `context_read` + `context_reread` telemetry in `_log_consumption()` |
| `agent/context/expansion_broker.py` | 2C-3 | `working_set_expansion_requested` + `working_set_expansion_decided` telemetry |
| `agent/oc_agent_runner_lib.py` | 2C-2 | `expansion_broker` parameter plumbed through to enforcer |

---

## Section 7: Sprint 3 Readiness

Sprint 2C closes all integration prerequisites for Sprint 3 (Expanded Roles):

| Prerequisite | Status |
|--------------|--------|
| Assembler in pipeline, storing D-047 artifacts | Done |
| Tier-based context delivery per role | Done |
| Reread prevention active | Done |
| Expansion broker linked, budget hints in deny messages | Done |
| 12 telemetry event types covering all layers | Done |
| Per-mission structured summary with consumption stats | Done |
| Template dict extensible for 9 roles | Done |
| D-048 canonical naming (remote-operator) | Done |
| Unknown role gets restrictive fallback | Done |

Sprint 3 can now add 7 new roles to `_WORKING_SET_TEMPLATES` and `SPECIALIST_PROMPTS` with confidence that enforcement, distribution, and telemetry will work automatically.

---

## Section 8: Architecture After Sprint 2C

```
User Request
  -> oc-agent-runner.py
    -> [D-057] Startup Metadata Gate
    -> Single-agent: run_agent_with_config()
    -> Mission mode: MissionController.execute_mission()
      -> ContextAssembler(mission_id)          <- 2C-1
      -> ExpansionBroker(mission_id)           <- 2C-1
      -> Planner LLM: stages
      -> For each stage:
        -> [D-053] Fail-closed: working_set required
        -> [D-048] _build_default_working_set(template dict)  <- 2C-6
        -> assembler.build_context_for_role()  <- 2C-1
        -> _format_artifact_context()          <- 2C-1
        -> run_agent_with_config(working_set, expansion_broker)
          -> For each tool call:
            -> Working Set Enforcer
              -> mutation_surface_mismatch     <- 2C-4
              -> policy_soft_denied            <- 2C-4
              -> _expansion_hint()             <- 2C-2
              -> [D-055] 6/6 enforcer events
            -> Risk Engine -> Approval -> MCP
        -> assembler.store_artifact()          <- 2C-1
        -> context_read / context_reread       <- 2C-3
      -> _emit_mission_summary()               <- 2C-5
        -> {id}-summary.json
        -> mission_completed / mission_failed  <- 2C-5
```

---

## Section 9: Commit History

```
9494cc8 Sprint 2C: close integration gaps — assembler wired, telemetry complete
```

---

*Phase 4 Sprint 2C Report*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Date: 2026-03-23*
