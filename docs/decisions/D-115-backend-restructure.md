# D-115: Backend Physical Topology / Ownership Boundaries

**Phase:** 6 (Sprint 26)
**Status:** Frozen
**Date:** 2026-03-28

---

## Decision

The `agent/` directory maintains its current modular structure. No physical restructure is needed — the architecture is already clean, acyclic, and well-organized.

## Analysis

### Current State (138 Python files)

| Module | Files | Purpose | Dependencies |
|--------|-------|---------|-------------|
| `api/` | 26 | REST endpoints, schemas, SSE | mission.role_registry |
| `events/` | 18 | EventBus + 13 governance handlers | isolated |
| `tests/` | 22 | Test suite | test-only |
| `mission/` | 11 | Orchestration, roles, quality gates | context, artifacts |
| `context/` | 10 | Memory, token budget, working set | isolated |
| `services/` | 8 | Approval, risk, tool catalog | context.policy_telemetry |
| `observability/` | 7 | Alerts, metrics, tracing | events.bus |
| `providers/` | 6 | LLM abstraction (Claude/GPT/Ollama) | isolated |
| `persistence/` | 4 | Mission/metric/trace stores | isolated |
| `artifacts/` | 2 | Schema validation | isolated |
| `auth/` | 2 | Session management | isolated |
| `utils/` | 2 | Atomic writes | isolated |

### Dependency Flow (Acyclic)

```
API → Mission → Context → (leaf)
       ↓
    Services → Context

Events ← Observability (consumers)

Providers, Persistence, Auth, Utils = isolated leaf nodes
```

**Zero circular dependencies detected.**

### Verdict: No Restructure Required

1. **Modules are already domain-bounded** — each has clear responsibility
2. **Dependency flow is acyclic** — no circular imports
3. **Naming is consistent** — module names match purpose
4. **Test coverage is co-located** — `tests/` mirrors module structure
5. **Import rules are already enforced** by natural module boundaries

### What Would a Restructure Change?

Proposed restructures in S14A/14B suggested moving files into `domain/`, `infrastructure/`, `application/` layers. This would:
- Break existing import paths across 138 files
- Require updating all test imports
- Add no functional value — current structure already separates concerns
- Risk introducing bugs in a stable, tested codebase

### Import Rules (Codified)

| Source Module | Can Import From | Cannot Import From |
|--------------|----------------|-------------------|
| `api/` | `mission/`, `services/`, `utils/` | `events/`, `providers/` |
| `mission/` | `context/`, `artifacts/` | `api/`, `events/`, `services/` |
| `services/` | `context/`, `persistence/` | `api/`, `mission/` |
| `events/` | (self only) | everything else |
| `observability/` | `events/` | `api/`, `mission/`, `services/` |
| `providers/` | (self only) | everything else |
| `context/` | (self only) | everything else |
| `persistence/` | (self only) | everything else |

## Carry-Forward

The "backend physical restructure" item from S14A/14B is **retired** by this decision. No further restructure work is needed unless the architecture grows beyond current module boundaries.

## Impact

- S14A/14B carryover item: **RETIRED**
- No file moves needed
- Import rules codified above
- Future module additions follow existing pattern
