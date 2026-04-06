# D-139: Controller Decomposition Boundary Freeze

**Phase:** Sprint 63 | **Status:** Frozen
**Author:** Claude Code (Opus) | **Date:** 2026-04-05
**Issues:** #325 (B-137), #326 (B-138)

---

## Context

`agent/mission/controller.py` has grown to 2197 lines with 28 methods spanning 8 distinct concerns. Change blast radius is high — any modification risks touching unrelated responsibilities. Before any extraction (S64+), boundaries must be frozen.

## Decision

### Boundary Definitions

The MissionController SHALL be decomposed into the following units:

| # | Service | Responsibility | Current LOC | Extraction Sprint |
|---|---------|---------------|-------------|-------------------|
| 0 | **MissionController** (core) | State transitions, stage dispatch, gate invocation, main loop | ~910 → ~500 | Stays |
| 1 | **MissionPersistenceAdapter** | Atomic write mission/state/token-report JSON to disk | 131 | S64 |
| 2 | **SignalAdapter** | Pause/resume/cancel signal check + wait loops | 81 | S64 |
| 3 | **MissionSummaryPublisher** | Structured summary build, LLM summary, deny forensics | 194 | S64 |
| 4 | **ApprovalStateManager** | Approval FSM lifecycle, timeout=deny, ESCALATE block | 129 | S65 |
| 5 | **StageRecoveryEngine** | Recovery triage, DLQ, circuit breaker, backoff, poison pill | 158 | S65 |
| 6 | **ContextManager** (sub-split) | Working set build, artifact context, discovery enrichment, agent selection | 285 | S66+ |
| 7 | **CapabilityManifestGenerator** | Startup-only capabilities.json generation | 94 | S66+ |

### Extraction Rules

1. **No behavior change.** Extraction is structural only. All existing tests must pass without modification.
2. **Dependency injection.** Extracted services are injected into MissionController via constructor.
3. **Callback pattern for circular deps.** StageRecoveryEngine receives `execute_fn: Callable` to break the Recovery ↔ Orchestration cycle.
4. **Atomic write consolidation.** PersistenceAdapter implements single `_atomic_write_json(path, data)` helper, replacing 4 duplicate patterns.
5. **Inline error block extraction.** The 7 duplicate `_fail_mission` patterns (~140 LOC) in `execute_mission` SHALL be consolidated into a single method before service extraction.
6. **File placement.** Extracted services go to `agent/mission/<service_name>.py` — same package, no cross-package import changes.

### Budget Enforcement Ownership (B-138)

**Decision:** Split ownership between Policy Engine and Controller.

| Component | Responsibility |
|-----------|---------------|
| **MissionController** | Tracks cumulative token count per mission (`_update_mission_budget()` — future S64 method). Accumulates `token_report.total_tokens` from each completed stage. |
| **PolicyEngine** | Evaluates budget rules. Existing `budget_exceeded → deny` rule (D-133) compares `policyContext.totalTokens` against `max_token_budget`. |
| **AlertEngine** | Fires alert at 80% threshold. Existing alert rule `budget_warning` (if present) or new rule in S64. |

**Data Flow:**

```
Stage N completes
    │
    ▼
Controller: cumulative_tokens += stage.token_report.total_tokens
    │
    ▼
Controller: build_policy_context() → includes totalTokens
    │
    ▼
PolicyEngine.evaluate(context, config)
    │
    ├─ totalTokens < max_budget * 0.8 → ALLOW
    ├─ totalTokens >= max_budget * 0.8 → ALLOW + alert_engine.fire("budget_warning")
    └─ totalTokens >= max_budget      → DENY "budget_exceeded"
    │
    ▼
Stage N+1 proceeds or mission FAILED
```

**Budget rule location:** `config/policies/` (YAML rule files, evaluated by PolicyEngine)
**No new code in S63** — this is design-only. Implementation in S64 (B-140).

## Consequences

- **Positive:** Controller LOC drops from 2197 to ~500. Each service is independently testable. Change blast radius reduced to single concern.
- **Negative:** 7 new files in `agent/mission/`. Import count increases. Extraction takes 2-3 sprints.
- **Risk:** Recovery ↔ Orchestration circular dependency. Mitigated by callback injection.

## Evidence

- `docs/sprints/sprint-63/responsibility-map.md` — full method mapping
- `docs/sprints/sprint-63/budget-data-flow.md` — budget enforcement design
- `docs/sprints/sprint-63/budget-enforcement-draft.yaml` — rule draft

## Status

**FROZEN** — 2026-04-05. No implementation until S64.
