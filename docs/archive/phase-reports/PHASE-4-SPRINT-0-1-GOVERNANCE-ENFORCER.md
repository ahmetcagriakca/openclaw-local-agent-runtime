# Phase 4 — Sprint 0 + Sprint 1: Tool Governance & Working Set Enforcer

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Foundation layer for SDLC governance — tool metadata + filesystem enforcement middleware

---

## Section 1: Executive Summary

**What was built:** Two foundational layers that enable all subsequent Phase 4 sprints:

1. **Sprint 0 — Tool Catalog Governance Metadata:** Every tool in the 24-tool catalog now carries a `governance` block describing its filesystem behavior and mutation surface. This metadata drives the enforcer (Sprint 1) and future role-scoped policies (Sprint 3+).

2. **Sprint 1 — Working Set Enforcer:** A middleware layer that intercepts every filesystem tool call, resolves paths canonically (D-049), checks against a bounded working set (D-038/D-051), enforces read budgets, and blocks forbidden zones — all before the risk engine runs.

**Key principle:** The enforcer derives behavior from data (governance metadata), not hardcoded lists. Adding a new tool automatically inherits enforcement if its governance flags are set.

**Test results:** 24/24 tools validated, 9/9 enforcement cases passed, regression passed (existing flow unchanged).

---

## Section 2: Sprint 0 — Tool Governance Metadata

### 2.1 Schema

Every tool entry in `TOOL_CATALOG` now includes:

```python
"governance": {
    "filesystemTouching": bool,       # Does this tool access the filesystem?
    "mutationSurface": str,           # "none" | "code" | "system"
    "workingSetScopeRequired": bool,  # Must the enforcer check path scope?
    "requiresPathResolution": bool    # Must path be canonically resolved?
}
```

### 2.2 Classification Summary

| Category | Count | Tools |
|----------|:-----:|-------|
| Filesystem-touching | 5 | read_file, write_file, list_directory, search_files, find_in_files |
| Non-filesystem | 19 | All others |
| Mutation: code | 1 | write_file |
| Mutation: system | 10 | set_clipboard, open_application, open_url, close_application, lock_screen, system_shutdown, system_restart, submit_runtime_task, mcp_restart, mcp_restart |
| Mutation: none | 13 | All read-only tools |

### 2.3 Helper Functions

| Function | Purpose |
|----------|---------|
| `get_tool_governance(name)` | Return governance dict for a tool |
| `is_filesystem_touching(name)` | Check if tool touches filesystem |
| `get_mutation_surface(name)` | Get mutation surface: none/code/system |
| `validate_catalog_governance()` | Startup check — all 24 tools must have complete metadata |

### 2.4 Validation

```
OK: 24 tools, all governance metadata valid
write_file mutationSurface: code
read_file filesystemTouching: True
get_system_info filesystemTouching: False
```

---

## Section 3: Sprint 1 — Working Set Enforcer

### 3.1 Architecture

```
Tool call from LLM
  → Tool Gateway (tool exists? role allowed?)
  → Working Set Enforcer ← NEW (Sprint 1)
    → Is tool filesystem-touching? (governance metadata)
    → Extract path from params
    → Canonical resolution (D-049)
    → Forbidden zone check
    → Read/write authorization against working set
    → Budget check
  → Risk Engine (existing)
  → Approval Service (existing)
  → MCP execution
```

### 3.2 Components

| File | Purpose |
|------|---------|
| `agent/context/working_set.py` | WorkingSet, FileAccess, ReadBudget dataclasses |
| `agent/context/path_resolver.py` | Canonical path resolution + containment checks |
| `agent/context/working_set_enforcer.py` | Core enforcement function |

### 3.3 WorkingSet Schema

```python
@dataclass
class WorkingSet:
    stage_id: str                    # Which mission stage
    role: str                        # Which specialist role
    skill: str                       # Which skill is executing
    files: FileAccess                # Allowed file paths
    budget: ReadBudget               # Remaining read operations
    forbidden_directories: list[str] # Always denied
    forbidden_patterns: list[str]    # Regex patterns always denied

@dataclass
class FileAccess:
    read_only: list[str]             # Files the role may read
    read_write: list[str]            # Existing files the role may modify
    creatable: list[str]             # New files the role may create
    generated_outputs: list[str]     # Artifact output locations
    directory_list: list[str]        # Directories the role may list

@dataclass
class ReadBudget:
    max_file_reads: int              # Total allowed file reads
    max_directory_reads: int         # Total allowed directory reads
    max_expansions: int              # Total allowed expansions
    remaining_*: int                 # Decremented on each use
```

### 3.4 Enforcement Flow

1. **Non-filesystem tools** → pass through (no check)
2. **Extract path** from tool params (tool-specific mapping)
3. **Canonical resolution** → `os.path.realpath(os.path.normpath(path))`
4. **Forbidden zone check** → directory list + regex patterns
5. **Write check** (if `mutationSurface == "code"`) → must be in `read_write`, `creatable`, or `generated_outputs`
6. **Read check** → must be in `read_only`, `read_write`, `generated_outputs`, or under `directory_list`
7. **Budget check** → decrement remaining reads, deny if exhausted

### 3.5 Integration

`oc_agent_runner_lib.py` — enforcer runs between tool gateway and risk engine:

```python
# If working_set is provided, enforce before risk engine
if working_set:
    enforcement = enforce_working_set(tc.name, tc.params, working_set, gov)
    if not enforcement.allowed:
        # Return policy message to LLM, skip MCP execution
        ...
```

When `working_set=None` (default), the enforcer is completely bypassed — existing single-agent and mission flows are unaffected.

### 3.6 Test Results

| # | Test Case | Expected | Result |
|---|-----------|----------|--------|
| 1 | read_file on assigned path | ALLOW | PASS |
| 2 | read_file on outside path | DENY | PASS |
| 3 | write_file to results dir | ALLOW | PASS |
| 4 | write_file with no write access | DENY | PASS |
| 5 | list_directory on assigned dir | ALLOW | PASS |
| 6 | list_directory on outside dir | DENY | PASS |
| 7 | get_system_info (non-filesystem) | ALLOW | PASS |
| 8 | Budget exhausted | DENY | PASS |
| 9 | Forbidden path (System32) | DENY | PASS |

**Regression:** Single-agent `"CPU kullanımı ne?"` → completed, response correct.

---

## Section 4: File Map

### New Files (Sprint 0+1)

| File | Sprint | Purpose |
|------|--------|---------|
| `agent/context/__init__.py` | 1 | Package init |
| `agent/context/working_set.py` | 1 | WorkingSet, FileAccess, ReadBudget dataclasses |
| `agent/context/path_resolver.py` | 1 | Canonical resolution, containment, forbidden checks |
| `agent/context/working_set_enforcer.py` | 1 | Core enforcement middleware |

### Modified Files

| File | Sprint | Change |
|------|--------|--------|
| `agent/services/tool_catalog.py` | 0 | Added governance block to 24 tools + 4 helper functions |
| `agent/oc_agent_runner_lib.py` | 1 | Added `working_set` param + enforcer integration |

---

## Section 5: Design Decisions

| Decision | Rationale |
|----------|-----------|
| Governance metadata on tools (not hardcoded lists) | New tools auto-inherit enforcement; single source of truth |
| Enforcer before risk engine | Policy violations should never reach risk/approval flow |
| `working_set=None` bypasses entirely | Zero-cost backward compatibility for existing flows |
| Case-insensitive path comparison (Windows) | `os.path.normcase()` used throughout for Windows compatibility |
| Budget is per-stage, not per-mission | Each specialist gets its own read budget, prevents one stage from exhausting mission resources |

---

## Section 6: What This Unlocks

Sprint 0+1 are the **enforcement foundation** for all subsequent sprints:

| Sprint | Dependency on Sprint 0+1 |
|--------|--------------------------|
| Sprint 2 (Context Assembler) | Uses WorkingSet schema to build per-stage access |
| Sprint 3 (Expanded Roles) | Each role gets a working set with appropriate file access |
| Sprint 4 (Discovery Map) | Discovery results populate working set file lists |
| Sprint 5 (Quality Gates) | Gates verify no policy-denied tool calls occurred |

Without Sprint 0+1, the system has no mechanism to restrict what files an agent can access. With it, every filesystem operation is bounded, budgeted, and auditable.

---

*Phase 4 Sprint 0+1 Report*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Date: 2026-03-23*
