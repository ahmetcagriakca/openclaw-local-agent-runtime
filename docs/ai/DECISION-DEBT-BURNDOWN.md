# Decision Debt Burn-Down Plan

**Date:** 2026-03-25
**Status:** ACTIVE — Sprint 11 Task 0 + Sprint 12 Task 0
**Target:** DECISIONS.md zero debt by Phase 5 closure

---

## 1. Current Debt Status

| Range | Count | Location | Status |
|-------|-------|----------|--------|
| D-001→D-020 | 20 | DECISIONS.md | ✅ Present |
| D-021→D-058 | 38 | Scattered in code/docs, NOT in DECISIONS.md | ❌ Debt |
| D-059→D-080 | 22 | Partially in DECISIONS.md, partially in session docs | ⚠ Partial |
| D-081→D-088 | 8 | In Sprint 9-10 task breakdowns, NOT in DECISIONS.md | ❌ Debt |
| D-089→D-096 | 8 | In Sprint 11 preliminary as DRAFT | ⬜ To be frozen |

**Total debt:** ~46 decisions outside DECISIONS.md.

---

## 2. Sprint 11 — Task 0: D-081→D-096 (13 decisions)

First work item of Sprint 11 kickoff. Completed BEFORE any code is written.

### Decisions to Write

| ID | Decision | Phase | Status |
|----|----------|-------|--------|
| D-081 | CSS Framework: Tailwind CSS utility-first | 5A-2 | Frozen |
| D-082 | Type Generation: Manual TS types from frozen Pydantic schemas | 5A-2 | Frozen |
| D-083 | Polling: Global 30s + manual refresh, Page Visibility pause | 5A-2 | Frozen |
| D-084 | Error Boundary: Per-panel isolation, per-route wrap | 5A-2 | Frozen |
| D-085 | File Watcher: Manual mtime polling 1s, pure Python os.stat | 5B | Frozen |
| D-086 | SSE Events: Per-entity invalidation signal, not per-field | 5B | Frozen |
| D-087 | SSE Auth: Localhost-only, D-070 extension, no extra token | 5B | Frozen |
| D-088 | SSE Reconnect: 1s→30s backoff, 3 fail → polling, Last-Event-ID persistence, 60s heartbeat timeout | 5B | Frozen |
| D-089 | CSRF: SameSite=Strict + Origin header check (localhost single-operator) | 5C | **Freeze at kickoff** |
| D-090 | Mutation Confirm: Confirmation dialog for destructive actions (cancel, reject) | 5C | **Freeze at kickoff** |
| D-091 | Mutation UI: Server-confirmed, no optimistic UI. Mutation-in-progress → SSE confirm → refresh | 5C | **Freeze at kickoff** |
| D-092 | Approval Sunset Phase 1: Dashboard approve \<id\>, Telegram yes/no deprecated warning | 5C | **Freeze at kickoff** |
| D-096 | Mutation Response: requestId + lifecycleState (requested→accepted→applied/rejected/timed_out). Fire-and-forget forbidden. | 5C | **Freeze at kickoff** |

### Mutation SSE Event Types (D-086 Extension)

Added to SSE event registry in Sprint 11:

| Event Type | Trigger | Data |
|-----------|---------|------|
| `mutation_requested` | API persisted signal artifact, response returned | `{ requestId, targetId, type }` |
| `mutation_accepted` | Controller consumed signal, validation passed | `{ requestId, targetId, type, newState }` |
| `mutation_applied` | Controller completed state transition | `{ requestId, targetId, type, newState }` |
| `mutation_rejected` | Controller validation failed | `{ requestId, targetId, reason }` |
| `mutation_timed_out` | Controller did not process within 10s | `{ requestId, targetId }` |

### Format

Each decision in DECISIONS.md: max 5 lines:

```markdown
## D-XXX: Title

**Phase:** N | **Status:** Frozen

One-line description. Trade-off: X weakened, Y strengthened.
```

### Acceptance Criteria

```bash
grep -c "^## D-" docs/ai/DECISIONS.md
# Before Sprint 11 Task 0: ~42
# After Sprint 11 Task 0: ~55 (+13)
```

### OD Freeze Status at Sprint 11 Kickoff

| OD | Decision | Outcome |
|----|----------|---------|
| OD-8 | CSRF → D-089: SameSite + Origin | FROZEN |
| OD-10 | Retry semantics → existing controller retry + new mission | FROZEN |
| OD-13 | Rate limit → WAIVED (localhost single-operator, D-070 sufficient) | WAIVED |
| D-096 | Mutation response contract | FROZEN |

Remaining open: 0. Sprint 11 starts with zero open decisions.

---

## 3. Sprint 12 — Task 0: D-021→D-058 (38 decisions) + D-093/D-094/D-095 Freeze

### 3a. D-021→D-058 Extraction

Phase 4 Agent System decisions. Scattered across code and docs, never written to DECISIONS.md.

### Sources

These decisions will be extracted from:
- `docs/ai/PHASE-4-DESIGN-INDEX.md`
- Sprint 3-6 task breakdowns
- Design comments in `agent/mission/controller.py`
- Archived session docs and repo history

### Expected Decision Areas

| Range | Topic |
|-------|-------|
| D-021→D-030 | Role registry, skill contracts, 9 role definitions |
| D-031→D-040 | Context Assembler, artifact identity, 5-tier delivery |
| D-041→D-045 | Working Set Enforcer, filesystem boundary |
| D-046→D-050 | Complexity router, stage templates |
| D-051→D-055 | Quality gates, feedback loops, policy telemetry |
| D-056→D-058 | Mission state machine, cost budgets, startup metadata |

### 3b. D-093/D-094/D-095 Freeze (Sprint 12 Kickoff)

These 3 decisions are Sprint 12's core decisions. Written to DECISIONS.md within first 24 hours:

| ID | Decision | Freeze Input |
|----|----------|-------------|
| D-093 | Legacy dashboard: retire vs parallel-run vs blocked | 12.1 feature gap analysis result |
| D-094 | E2E framework: Playwright vs Cypress | OD-12 resolution |
| D-095 | Approval sunset Phase 2: full removal vs warning-only waiver | OD-14 resolution |

**Rule:** These 3 decisions cannot leak into Sprint 12 implementation. Frozen or waived within first 24 hours. Cannot remain open.

### Acceptance Criteria

```bash
grep -c "^## D-" docs/ai/DECISIONS.md
# After Sprint 12 Task 0: ~93+ (existing + 38 extraction + 3 freeze)
# Zero debt: D-001→D-096 all present
```

### Phase 5 Closure Gate

D-021→D-058 + D-093/D-094/D-095 missing from DECISIONS.md → Phase 5 cannot close. Scoreboard items #10 and #11.

---

## 4. Sprint 12 Additional: D-059→D-080 Gap Check

These decisions are partially in DECISIONS.md. During Sprint 12 Task 0, missing ones are completed.

```bash
for i in $(seq 59 80); do
  grep -q "D-0$i\|D-$i" docs/ai/DECISIONS.md || echo "MISSING: D-$i"
done
```

---

## 5. Timeline

```
Sprint 11 Kickoff (Day 0):
  ├── Task 0: D-081→D-096 + OD freeze → DECISIONS.md (~2 hours)
  ├── Task 1: Contract-first tests (decisions now referenceable)
  └── ... implementation ...

Sprint 12 Kickoff (Day 0):
  ├── Task 0: D-021→D-058 extraction → DECISIONS.md (~4 hours)
  ├── Task 0b: D-059→D-080 gap check + fix (~1 hour)
  ├── Task 0c: D-093/D-094/D-095 freeze → DECISIONS.md (~1 hour)
  └── ... implementation ...

Sprint 12 Closure:
  └── Scoreboard #11: D-021→D-058 zero debt → ✅
```

---

## 6. Verification

Final check at Sprint 12 closure:

```bash
# All D-001→D-096 present?
for i in $(seq 1 96); do
  ID=$(printf "D-%03d" $i)
  grep -q "$ID" docs/ai/DECISIONS.md || echo "MISSING: $ID"
done

# Expected output: nothing (0 missing)
# Especially verify: D-021→D-058 (Phase 4 extraction)
#                    D-093, D-094, D-095 (Sprint 12 freeze)
```

---

*Decision Debt Burn-Down Plan — Vezir Platform*
*Sprint 11: D-081→D-096 (13 decisions + 4 OD freeze)*
*Sprint 12: D-021→D-058 (38 decision extraction) + D-093/D-094/D-095 freeze*
*Phase 5 Closure: Zero debt*
