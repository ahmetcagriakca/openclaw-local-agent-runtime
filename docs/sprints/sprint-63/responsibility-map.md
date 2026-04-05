# Controller Responsibility Map — Sprint 63 (B-137)

**Source:** `agent/mission/controller.py` (2197 lines, 28 methods)
**Purpose:** Pre-extraction boundary analysis for D-139

---

## Current Concern Inventory

The `MissionController` class currently owns **8 distinct concerns** across **28 methods**:

| # | Concern | Methods | LOC | % of Total |
|---|---------|---------|-----|------------|
| 1 | Orchestration Core | 7 | ~910 | 41% |
| 2 | Context & Working Set Management | 8 | ~285 | 13% |
| 3 | Mission Summary & Telemetry | 3 | ~194 | 9% |
| 4 | Stage Recovery & Resilience | 3 | ~158 | 7% |
| 5 | Mission Persistence | 4 | ~131 | 6% |
| 6 | Signal Handling (Pause/Resume) | 3 | ~81 | 4% |
| 7 | Approval Lifecycle | 1 (+inline) | ~129 | 6% |
| 8 | Capability Manifest | 1 | ~94 | 4% |
| — | Working Set Templates (data) | — | ~79 | 4% |
| — | Model/Agent Mapping (data) | — | ~6 | <1% |
| — | Imports + class definition | — | ~50 | 2% |
| — | Inline error handling in execute_mission | — | ~90 | 4% |

---

## Method → Future Service Mapping Table

### 1. Orchestration Core (stays in MissionController)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `__init__` | 29-48 | 20 | Constructor, dependency wiring |
| `execute_mission` | 50-647 | 598 | Main loop: plan → execute → gate → complete |
| `_plan_mission` | 649-811 | 163 | Complexity routing, LLM planning, template enforcement |
| `_force_template` | 813-829 | 17 | Force template when planner deviates |
| `_execute_stage` | 875-924 | 50 | Single stage dispatch to agent runner |
| `_classify_mission_risk` | 996-1015 | 20 | D-128 risk classification from tools |
| `_check_gates_and_loops` | 1459-1625 | 167 | Quality gate checks + feedback loop |

**Post-extraction:** ~910 LOC → ~500 LOC (after extracting inline error handling patterns)

### 2. MissionPersistenceAdapter (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_save_mission` | 1963-1987 | 25 | Atomic write mission JSON |
| `_persist_mission_state` | 1017-1042 | 26 | Atomic write state machine JSON |
| `_save_token_report` | 1989-2062 | 74 | Token report aggregation + write |
| `_find_stage_index` | 1859-1864 | 6 | Stage lookup by ID |

**Total:** 131 LOC
**Dependencies:** `MISSIONS_DIR`, `tempfile`, `json`, `os`, `datetime`
**Interface:** `save(mission)`, `save_state(state)`, `save_token_report(mission)`, `find_stage(stages, id)`
**Note:** All 4 methods use identical atomic write pattern (temp → fsync → os.replace). Extraction consolidates into single `_atomic_write_json(path, data)` helper.

### 3. StageRecoveryEngine (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_handle_stage_failure` | 1699-1832 | 134 | Recovery triage: circuit breaker, poison pill, backoff, manager invocation |
| `_enqueue_to_dlq` | 1834-1857 | 24 | DLQ enqueue for later retry |

**Total:** 158 LOC
**Dependencies:** `CircuitBreaker`, `is_poison_pill`, `sleep_with_backoff`, `DLQStore`, `PolicyTelemetry`
**Shared methods:** Uses `_create_recovery_stage` (Orchestration) and `_execute_stage` (Orchestration)
**Interface:** `handle_failure(stage, error, state, ...) -> RecoveryDecision`, `enqueue_dlq(mission)`

### 4. ApprovalStateManager (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_wait_for_approval` | 2136-2184 | 49 | Poll approval store, timeout=deny (D-138) |
| *(inline in execute_mission)* | 308-387 | 80 | ESCALATE block: create approval, wait, resume/fail |

**Total:** ~129 LOC
**Dependencies:** `ApprovalStore`, `MissionState`, `PolicyTelemetry`
**Interface:** `request_and_wait(mission_id, stage_id, ...) -> ApprovalDecision`
**Note:** Inline ESCALATE block should become a single method call after extraction.

### 5. MissionSummaryPublisher (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_emit_mission_summary` | 1044-1186 | 143 | Build + persist structured summary + telemetry |
| `_generate_summary` | 1402-1419 | 18 | LLM summary generation |
| `_aggregate_deny_forensics` | 1423-1455 | 33 | Deny forensics aggregation |

**Total:** 194 LOC
**Dependencies:** `ContextAssembler`, `ExpansionBroker`, `PolicyTelemetry`, LLM provider
**Interface:** `emit(mission_id, mission, assembler, broker, status, state)`, `generate_text(goal, stages, artifacts)`

### 6. SignalAdapter (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_check_and_handle_pause` | 2064-2090 | 27 | Check pause signal, transition state |
| `_wait_for_resume` | 2092-2134 | 43 | Block until resume/cancel/timeout |
| `_delete_signal` | 2187-2197 | 11 | Delete processed signal file |

**Total:** 81 LOC
**Dependencies:** `mutation_bridge.has_pending_signal`, `MissionState`, `Path`
**Interface:** `check_pause(mission_id) -> bool`, `wait_resume(mission_id, timeout) -> bool`

### 7. ContextManager (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_format_artifact_context` | 926-994 | 69 | Distance-based tiered truncation |
| `_enrich_working_set_from_discovery` | 831-873 | 43 | Discovery map enrichment |
| `_build_default_working_set` | 1269-1321 | 53 | D-048/D-053 working set construction |
| `_resolve_artifact_type` | 1324-1332 | 9 | Skill → artifact type mapping |
| `_validate_artifact_schema` | 1334-1350 | 17 | Non-blocking schema validation |
| `_get_latest_artifact_data` | 1684-1695 | 12 | Artifact lookup helper |
| `_select_agent_for_role` | 1360-1400 | 41 | D-043 provider selection |
| `_create_rework_stages` | 1627-1659 | 33 | Rework stage factory |
| `_create_recovery_stage` | 1661-1682 | 22 | Recovery stage factory |

**Total:** ~285 LOC (some methods shared across concerns)
**Note:** This concern splits further into WorkingSetBuilder, ArtifactContextFormatter, StageFactory

### 8. CapabilityManifest (extract)

| Method | Lines | LOC | Responsibility |
|--------|-------|-----|----------------|
| `_update_capability_manifest` | 1868-1961 | 94 | Auto-generate capabilities.json |

**Total:** 94 LOC
**Dependencies:** `specialists.SPECIALIST_PROMPTS`, `tempfile`, `json`
**Interface:** `update()` — called once at startup

---

## Inter-Concern Dependency Graph

```
                    ┌─────────────────────────────┐
                    │   Orchestration Core (910)   │
                    │   execute_mission            │
                    │   _plan_mission              │
                    │   _check_gates_and_loops     │
                    └──────────┬──────────────────┘
                               │
          ┌────────┬───────────┼───────────┬──────────┬──────────┐
          │        │           │           │          │          │
          ▼        ▼           ▼           ▼          ▼          ▼
    ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
    │Persistence│ │Recovery  │ │Approval │ │Summary │ │Signal  │ │Context   │
    │Adapter   │ │Engine    │ │State    │ │Publish │ │Adapter │ │Manager   │
    │(131)     │ │(158)     │ │(129)    │ │(194)   │ │(81)    │ │(285)     │
    └──────────┘ └──────────┘ └─────────┘ └────────┘ └────────┘ └──────────┘
         │              │           │          │                      │
         │              ├───────────┘          │                      │
         │              │                      │                      │
         ▼              ▼                      ▼                      ▼
    ┌──────────┐  ┌──────────┐          ┌──────────┐          ┌──────────┐
    │MISSIONS_ │  │DLQStore  │          │Assembler │          │Working   │
    │DIR (disk)│  │CircuitBr.│          │Expansion │          │Set/Role  │
    └──────────┘  └──────────┘          └──────────┘          └──────────┘
```

**Key dependency flows:**
1. Orchestration → all 6 extracted services (fan-out)
2. Recovery → Orchestration (`_execute_stage`, `_create_recovery_stage`) — bidirectional
3. Summary → Assembler + Expansion Broker (read-only)
4. Persistence → disk only (no service deps)
5. Approval → ApprovalStore (external)
6. Signal → mutation_bridge (external)

**Circular dependency risk:**
- Recovery ↔ Orchestration: Recovery calls `_execute_stage` for manager recovery_triage. Post-extraction, RecoveryEngine takes an `execute_fn` callback.

---

## Extraction Priority

| Priority | Service | Reason | Sprint |
|----------|---------|--------|--------|
| 1 | MissionPersistenceAdapter | Zero dependencies, pure I/O, atomic write consolidation | S64 |
| 2 | SignalAdapter | Zero deps, clean boundary, 81 LOC | S64 |
| 3 | MissionSummaryPublisher | Read-only from Assembler, no mutation | S64 |
| 4 | ApprovalStateManager | Clean FSM boundary, B-134 wiring isolated | S65 |
| 5 | StageRecoveryEngine | Bidirectional dep needs callback pattern | S65 |
| 6 | ContextManager (split) | Largest, needs sub-decomposition | S66+ |
| 7 | CapabilityManifest | Startup-only, lowest urgency | S66+ |

---

## Inline Error Handling Pattern

`execute_mission` contains **7 nearly identical error-handling blocks** (lines 186-219, 241-269, 524-542, 580-592, 600-614, 556-572, 364-387). Each follows:

```python
mission["status"] = "failed"
mission["error"] = failure_reason
mission["finishedAt"] = datetime.now(timezone.utc).isoformat()
mission_state.transition_to(MissionStatus.FAILED, failure_reason)
self._save_mission(mission)
self._persist_mission_state(mission_state)
self._enqueue_to_dlq(mission)
self._emit_mission_summary(...)
return mission
```

**Recommendation:** Extract to `_fail_mission(mission, mission_state, reason, assembler, broker) -> dict` — reduces execute_mission by ~140 lines.
