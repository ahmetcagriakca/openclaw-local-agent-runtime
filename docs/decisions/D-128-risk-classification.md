# D-128: Risk Classification Contract

**ID:** D-128
**Status:** Frozen
**Phase:** 7 / Sprint 35
**Date:** 2026-03-29

---

## Context

Mission execution uses tools with varying risk levels (read-only vs system-admin). No risk classification exists — all missions are treated equally regardless of tool danger. This prevents risk-aware scheduling, auditing, and future policy enforcement.

## Decision

### Risk Levels

| Level | Definition | Example Tools |
|-------|-----------|---------------|
| low | Read-only tools, no side effects | file_read, search, list_files |
| medium | Write tools, reversible side effects | file_write, create_directory |
| high | Network/exec tools, potentially irreversible | http_request, run_command, shell_exec |
| critical | Admin/system tools, broad impact | system_config, service_restart, delete_recursive |

### Classification Source

- Static mapping: tool name → risk level, defined in capability manifest or risk engine config
- Source of truth: `agent/services/risk_engine.py`
- No dynamic/runtime classification — mapping is deterministic

### Unknown Tool Default

- Any tool not in the mapping defaults to **high** (fail-safe principle)
- Unknown != zero risk

### Computation Lifecycle

- **When:** Computed once at mission creation time, before first stage execution
- **Writer:** `MissionController` (single writer, no other component writes risk_level)
- **Persistence:** Stored in mission state JSON via `mission_store.py`, field: `risk_level`
- **Immutability:** Never recomputed during or after execution. Tool catalog changes after creation do not affect existing missions.

### API Exposure

- **Internal only** in Sprint 35
- `risk_level` is persisted in mission state JSON but NOT exposed in `MissionSummary` or any public API response model
- Future API exposure requires a new decision record

### Validation Method

- Test: create mission → verify `risk_level` persisted in state JSON
- Test: reload mission → verify same value
- Test: mutate tool mapping after creation → verify value unchanged
- Test: MissionSummary serialization does NOT include `risk_level`
- Test: unknown tool → risk_level = high

### Impacted Files

| File | Change |
|------|--------|
| `agent/services/risk_engine.py` | Risk level computation + tool mapping |
| `agent/mission/controller.py` | Call risk engine at mission creation |
| `agent/persistence/mission_store.py` | Persist risk_level field |
| `agent/tests/test_risk_*.py` | Risk classification tests |

### Rollback Condition

- If risk classification introduces mission creation regression (existing tests fail), revert the risk_level field addition and keep the decision frozen for re-implementation in next sprint.
- Rollback does not un-freeze D-128; it defers implementation.

## Consequences

- Missions carry a risk classification from creation
- Future sprints can use risk_level for policy enforcement, approval routing, audit filtering
- No API contract change in Sprint 35
