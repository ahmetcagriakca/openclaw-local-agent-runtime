# Phase 4 — Sprint 1H + Sprint 2: Governance Hardening & Context Assembler

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Governance enforcement hardening + artifact distribution economy engine

---

## Section 1: Executive Summary

**What was built:** Two critical layers that make the multi-agent system production-grade:

1. **Sprint 1H — Governance Hardening:** Four hardening tasks that elevate Sprint 1's enforcer from prototype to operationally reliable. Mission mode is now fail-closed (D-053), runtime validates its own metadata on startup (D-057), every enforcer decision is telemetry-logged (D-055), and the path resolver blocks 9 Windows-specific attack vectors (D-058).

2. **Sprint 2 — Context Assembler:** The distribution economy engine — stores artifacts with identity headers (D-047), delivers context at 5 cost tiers (D-041), auto-downgrades redundant reads (D-042), caches summaries for zero-cost reuse (D-040), and enforces role-based expansion budgets.

**Test results:** 18/18 hardening tests + 35/35 assembler tests + regression = all green.

---

## Section 2: Sprint 1H — Governance Hardening

### 2.1 Task 1H-1: Mission Mode Fail-Closed (D-053)

**Problem:** Mission stages could run without a working set, bypassing all filesystem enforcement.

**Solution:** Added a pre-dispatch check in `execute_mission()`. If a stage's `working_set` is None in mission mode, the stage is immediately failed with a `POLICY:` message and the mission aborts. Default working sets are now auto-generated per specialist role during planning.

**Files modified:**
- `agent/mission/controller.py` — fail-closed gate + `_build_default_working_set()` method

**Default working sets:**

| Specialist | File Reads | Dir Reads | Expansions | Generated Outputs |
|------------|:----------:|:---------:|:----------:|:-----------------:|
| analyst | 20 | 10 | 3 | none |
| executor | 10 | 5 | 2 | results/ |

**Backward compatibility:** Single-agent mode (`working_set=None`) continues to work — enforcer bypass only applies outside mission context.

### 2.2 Task 1H-2: Startup Metadata Gate (D-057)

**Problem:** If a tool lacked governance metadata, the enforcer would silently skip checks.

**Solution:** `validate_catalog_governance()` runs on every startup, before any LLM or MCP call. If any tool is missing governance fields, runtime exits with `FATAL` and error details.

**File modified:** `agent/oc-agent-runner.py` — gate inserted after arg parsing, before dispatch.

**Behavior:**
- Normal startup: gate passes silently, zero output
- Missing metadata: `FATAL: Tool catalog governance validation failed:` + details + `exit 1`

### 2.3 Task 1H-3: Policy Telemetry Events (D-055)

**Problem:** Enforcer decisions were invisible — no way to audit why a tool call was allowed or denied.

**Solution:** New `policy_telemetry.py` module emits structured JSONL events to `logs/policy-telemetry.jsonl`. Every enforcer decision point now calls `emit_policy_event()`.

**Files:**
- `agent/context/policy_telemetry.py` — NEW: JSONL event emitter
- `agent/context/working_set_enforcer.py` — MODIFIED: telemetry calls at every decision point

**Event types:**

| Event | When |
|-------|------|
| `filesystem_tool_allowed` | Filesystem tool passed all checks |
| `policy_denied` | Tool call blocked by scope/write/forbidden check |
| `budget_exhausted` | Read budget depleted |
| `path_resolution_failed` | Canonical path resolution returned None |

**Event schema:**
```json
{
  "timestamp": "2026-03-23T11:00:00+00:00",
  "event": "policy_denied",
  "tool": "read_file",
  "role": "analyst",
  "stage_id": "stage-1",
  "reason": "read_scope",
  "resolved_path": "C:\\Users\\AKCA\\Desktop\\secret.txt"
}
```

### 2.4 Task 1H-4: Path Hardening (D-058)

**Problem:** Sprint 1's path resolver handled basic traversal but lacked Windows-specific attack vector coverage.

**Solution:** Added null byte and UNC path rejection to `resolve_canonical()`. Created 9-case D-058 test corpus covering all attack vectors from the design document.

**File modified:** `agent/context/path_resolver.py` — null byte + UNC checks added.

**D-058 Test Corpus:**

| # | Attack Vector | Result |
|---|---------------|--------|
| 1 | Basic traversal (`..\..\Windows\System32`) | DENY |
| 2 | Unix-style traversal (`../../../etc/passwd`) | DENY |
| 3 | Mixed slash normalization (`agent/services\file.py`) | Normalizes correctly |
| 4 | Case variation (`OC\Agent\Services\Tool_Catalog.PY`) | Case-insensitive match |
| 5 | Junction-like escape (`temp_junction\..\..\System32`) | DENY |
| 6 | Symlink outside scope (`C:\Users\Public\symlink`) | DENY |
| 7 | Creatable with embedded traversal | DENY |
| 8 | Null byte injection (`file.py\x00.txt`) | DENY (None returned) |
| 9 | UNC path (`\\server\share\...`) | DENY (None returned) |

**Combined results:** 9/9 D-058 + 9/9 Sprint 1 regression = 18/18 passed.

### 2.5 Sprint 1H Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Mission mode fail-closed | PASS — working_set=None blocks stage |
| 2 | Startup metadata gate | PASS — broken tool exits with FATAL |
| 3 | Policy telemetry | PASS — 4 event types logged to JSONL |
| 4 | Path hardening | PASS — 18/18 tests (D-058 + Sprint 1) |
| 5 | Regression | PASS — single-agent + mission mode working |

---

## Section 3: Sprint 2 — Context Assembler + Artifact Identity

### 3.1 Task 2-1: Artifact Identity Header (D-047)

Every artifact now carries a mandatory identity header with 12 fields:

```python
@dataclass
class ArtifactHeader:
    artifactId: str           # "art-20260323-stage-2-analyst" (unique)
    artifactType: str         # "discovery_map", "requirements_brief", etc.
    version: int              # Monotonic version number
    missionId: str            # Parent mission
    producedByStage: str      # Which stage created this
    producedByRole: str       # Which role created this
    producedBySkill: str      # Which skill was executing
    producedAt: str           # ISO timestamp
    inputArtifactIds: list    # Lineage — which artifacts were consumed
    contentHash: str          # "sha256:..." — deterministic
    sizeTokens: int           # Estimated token count
    compressionAvailable: dict # Available compression tiers
```

**Key properties:**
- `contentHash` is deterministic: same data always produces same hash
- `artifactId` is unique: timestamp-based with microsecond resolution
- `validate_artifact_header()` catches missing fields

**File:** `agent/context/artifact_identity.py`

### 3.2 Task 2-2: Summary Cache (D-040 partial)

Zero-cost summary reuse through in-memory caching.

**File:** `agent/context/summary_cache.py`

**Components:**

| Function | Purpose |
|----------|---------|
| `SummaryCache` | Key-value cache with hit/miss tracking |
| `generate_basic_summary()` | Structural summary without LLM — preserves keys, truncates values |
| `generate_metadata_view()` | Tier A delivery — field names + types, no content bodies |

**Performance validated:**
- Summary size: 168 bytes vs 2045 bytes original = **8.2%** (well under 30% target)
- Cache hit/miss counting accurate

### 3.3 Task 2-3: Context Assembler Core (D-040/D-041/D-042)

The distribution economy engine. Central component that stores artifacts, delivers context at the cheapest sufficient tier, and prevents redundant reads.

**File:** `agent/context/assembler.py`

**5-Tier Delivery (D-041):**

| Tier | Name | Content | Cost |
|------|------|---------|------|
| A | Metadata | Field names + types + IDs, no bodies | Minimal |
| B | Summary | Structural summary, <30% of original | Low |
| C | Scoped | Role-relevant excerpt (summary for now, Sprint 3+ narrows) | Medium |
| D | Full | Complete wrapped artifact with header | High |
| E | Full+Neighbors | Full + related files (Sprint 4 adds neighbor attachment) | Highest |

**Role-Default Tier Matrix (D-041):**

| Role | Default Tier | Rationale |
|------|:------------:|-----------|
| product-owner | B | Needs overview, not details |
| analyst | D | Needs full data for analysis |
| architect | D | Needs full data for design |
| project-manager | B | Needs status, not implementation |
| developer | C | Needs relevant sections only |
| tester | C | Needs relevant sections only |
| reviewer | C | Needs relevant sections only |
| manager | B | Needs summary for oversight |
| remote-operator | D | Needs full data for system ops |

**Reread Auto-Downgrade (D-042):**
- First full read (tier D/E): delivered in full, logged
- Second full read by same role: auto-downgraded to tier B (summary), logged with `reread=True` and `downgradedFrom`
- Different role requesting same artifact: not a reread, delivered in full

**Consumption Logging:**
Every artifact read is logged with: artifactId, role, stageId, tier, reread flag, timestamp.

### 3.4 Task 2-4: Expansion Broker (D-042)

Handles working set expansion requests with role-based budget enforcement.

**File:** `agent/context/expansion_broker.py`

**Budget per role:**

| Role | Max Expansions | Rationale |
|------|:--------------:|-----------|
| developer | 8 | Most likely to need additional files |
| reviewer | 5 | May need to follow code references |
| tester | 3 | Limited scope, test-focused |
| analyst | 999 | Self-expanding by design |
| architect | 999 | Self-expanding by design |
| Others | 0 | No expansion rights |

**Enforcement rules:**
- Expansion without `reason` → denied
- Role with no expansion rights → denied
- Budget exhausted → denied with count details
- Every request produces a D-042 schema-compliant record

### 3.5 Sprint 2 Integration Test Results

**35/35 tests passed:**

| Category | Tests | Result |
|----------|:-----:|--------|
| Artifact identity header | 9 | 9/9 PASS |
| Summary cache | 6 | 6/6 PASS |
| Context Assembler | 12 | 12/12 PASS |
| Expansion broker | 8 | 8/8 PASS |

**Key validations:**
- contentHash deterministic (same data = same hash)
- Summary 8.2% of original (target: <30%)
- Reread downgrade: architect's second D read returned summary string
- Role defaults: manager got B, analyst got D
- Expansion budget: developer's 9th request denied at limit 8
- Manager expansion denied (no rights)
- Expansion without reason denied

### 3.6 Sprint 2 Exit Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Artifact identity header: 12 fields, deterministic hash | PASS |
| 2 | Summary cache: hit/miss, summary <30% | PASS (8.2%) |
| 3 | Context Assembler: 5-tier, reread downgrade, consumption log | PASS |
| 4 | Expansion broker: role budget, D-042 schema | PASS |
| 5 | Integration test: end-to-end | PASS (35/35) |
| 6 | Regression: Sprint 1 enforcer | PASS (18/18) |
| 7 | Regression: single-agent mode | PASS |

---

## Section 4: File Map

### New Files

| File | Sprint | Purpose |
|------|--------|---------|
| `agent/context/policy_telemetry.py` | 1H-3 | JSONL event emitter for enforcer decisions |
| `agent/context/artifact_identity.py` | 2-1 | D-047 artifact header creation + validation |
| `agent/context/summary_cache.py` | 2-2 | Summary cache + basic summary/metadata generation |
| `agent/context/assembler.py` | 2-3 | Context Assembler — 5-tier delivery engine |
| `agent/context/expansion_broker.py` | 2-4 | D-042 expansion request handling |

### Modified Files

| File | Sprint | Change |
|------|--------|--------|
| `agent/context/working_set_enforcer.py` | 1H-3 | Added telemetry emit at every decision point |
| `agent/context/path_resolver.py` | 1H-4 | Added null byte + UNC path rejection |
| `agent/mission/controller.py` | 1H-1 | Fail-closed gate + default working set builder |
| `agent/oc-agent-runner.py` | 1H-2 | Startup governance validation gate |

---

## Section 5: Architecture After Sprint 1H + 2

```
User Request
  -> oc-agent-runner.py
    -> [D-057] Startup Metadata Gate (validate_catalog_governance)
    -> Single-agent mode: run_agent_with_config()
    -> Mission mode: MissionController.execute_mission()
      -> [D-053] Fail-closed: working_set required per stage
      -> Planner LLM: break goal into stages
      -> For each stage:
        -> _build_default_working_set()
        -> run_agent_with_config(working_set=ws)
          -> LLM generates tool calls
          -> For each tool call:
            -> [D-049] Working Set Enforcer
              -> Path resolution (canonical, null byte, UNC)
              -> Forbidden zone check
              -> Scope check (read/write authorization)
              -> Budget check
              -> [D-055] Telemetry event emitted
            -> Risk Engine
            -> Approval Service
            -> MCP execution
          -> Artifacts stored via ArtifactStore
      -> [D-047] Artifact identity headers (future: via Context Assembler)
      -> [D-041] 5-tier context delivery (future: via Context Assembler)
      -> [D-042] Reread prevention + expansion broker (future integration)
      -> Summary generation
```

**Context Assembler is built and tested but not yet wired into the Mission Controller's stage loop.** Sprint 3 (expanded roles) or Sprint 4 (discovery map) will integrate it — the assembler needs role/skill definitions to produce meaningful working sets and tier selections.

---

## Section 6: What This Unlocks

| Sprint | Dependency on 1H+2 |
|--------|---------------------|
| Sprint 3 (Expanded Roles) | Roles get working sets from assembler, tier defaults from D-041 matrix |
| Sprint 4 (Discovery Map) | Discovery results stored as artifacts with D-047 headers, cached summaries |
| Sprint 5 (Quality Gates) | Gates read artifacts via assembler tiers, check consumption stats |
| Sprint 6 (Integration) | Full pipeline uses enforcer + assembler + expansion broker |

---

## Section 7: Commit History

```
7683e96 Sprint 1H: governance hardening — fail-closed, startup gate, telemetry, path hardening
4734122 Sprint 2: Context Assembler + Artifact Identity + Summary Cache + Expansion Broker
```

---

*Phase 4 Sprint 1H + Sprint 2 Report*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Date: 2026-03-23*
