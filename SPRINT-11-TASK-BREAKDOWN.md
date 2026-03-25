# Sprint 11 — Phase 5C: Intervention — Task Breakdown

**Date:** 2026-03-25
**implementation_status:** not_started
**closure_status:** not_started
**Prerequisite:** Sprint 10 closure_status=closed
**Author:** Operator (AKCA) + Claude (Copilot)
**Risk Level:** HIGH — mutation endpoints, state transitions, concurrency

---

## Sprint Goal

Dashboard'dan approve/deny/cancel/retry aksiyonları. API mutation endpoint'leri atomic request artifact pattern ile çalışır (D-096). Controller sole executor kalır (D-001). Fire-and-forget yasak.

**Definition of Done:**
- 4 mutation endpoint: approve, reject, cancel, retry
- CSRF middleware (D-089)
- Mutation audit logger (requestId, tabId, sessionId)
- Atomic request artifact bridge (D-001, D-062, D-063)
- MutationResponse contract: requestId + lifecycleState (D-096)
- SSE mutation events: requested → accepted → applied/rejected/timed_out
- Frontend: confirmation dialog (D-090), mutation buttons, SSE confirm (D-091)
- Approval sunset Phase 1 (D-092)
- Contract-first test suite (11 tests)
- Operator drill 5/5 PASS
- GPT mid + final review PASS

---

## Frozen Decisions (Sprint 11)

| ID | Decision | Phase |
|----|----------|-------|
| D-089 | CSRF: SameSite=Strict + Origin check | 5C |
| D-090 | Confirm dialog for destructive actions | 5C |
| D-091 | Server-confirmed mutation, no optimistic UI | 5C |
| D-092 | Approval sunset Phase 1: Telegram deprecated | 5C |
| D-096 | Mutation response: requestId + lifecycleState. Fire-and-forget forbidden | 5C |

---

## Task List

| Task | Description | Effort | Side | Dependency |
|------|-------------|--------|------|------------|
| 11.0 | DECISIONS.md debt: write D-081→D-096 | M | Claude/Copilot | — |
| 11.1 | Contract-first test suite (11 tests) | L | Backend | 11.0 |
| 11.2 | CSRF middleware (SameSite + Origin) | S | Backend | — |
| 11.3 | Mutation audit logger (requestId, tabId, sessionId) | S | Backend | — |
| 11.4 | Atomic request artifact bridge | M | Backend | 11.1 |
| 11.5 | Approve/Reject endpoints + MutationResponse contract | L | Backend | 11.1, 11.2, 11.3, 11.4 |
| 11.6 | Cancel/Retry endpoints | L | Backend | 11.1, 11.2, 11.3, 11.4 |
| 11.MID | GPT mid-sprint review — BLOCKER | — | GPT | 11.5, 11.6 |
| 11.7 | Confirmation dialog component | S | Frontend | — |
| 11.8 | Approval page mutation buttons | M | Frontend | 11.5 backend ready |
| 11.9 | Mission detail cancel/retry buttons | M | Frontend | 11.6 backend ready |
| 11.10 | Mutation feedback (spinner, error, SSE confirm) | M | Frontend | 11.8, 11.9 |
| 11.11 | Approval sunset warning (Telegram deprecated) | S | Backend | 11.5 |
| 11.12 | Manual operator drill (5 scenarios) | M | Operator | 11.10 |
| 11.FINAL | GPT final review + Claude assessment — BLOCKER | — | GPT + Claude | 11.12 |

**Rule:** 11.MID PASS required before 11.7+ can start. 11.FINAL PASS required before closure_status advances.

---

## Task Cards

### Task 11.0 — DECISIONS.md Debt Burn-Down

| Field | Value |
|-------|-------|
| ID | 11.0 |
| File | `docs/ai/DECISIONS.md` |
| Effort | M |
| Dependency | — |
| Dependents | 11.1 (contract tests reference decisions) |

#### Scope

Write Sprint 9-10 decisions to DECISIONS.md:

| ID | Decision | Phase |
|----|----------|-------|
| D-081 | Tailwind CSS | 5A-2 |
| D-082 | Manual TS types from frozen schemas | 5A-2 |
| D-083 | Global 30s polling + manual refresh | 5A-2 |
| D-084 | Per-panel ErrorBoundary | 5A-2 |
| D-085 | Manual mtime polling (1s, cross-platform) | 5B |
| D-086 | Per-entity SSE events | 5B |
| D-087 | SSE localhost-only auth (D-070 extension) | 5B |
| D-088 | Exponential backoff + polling fallback | 5B |
| D-089 | CSRF: SameSite=Strict + Origin check | 5C |
| D-090 | Confirm dialog for destructive actions | 5C |
| D-091 | Server-confirmed mutation (no optimistic UI) | 5C |
| D-092 | Approval sunset Phase 1 (Telegram deprecated) | 5C |
| D-096 | Mutation response contract: requestId + lifecycleState | 5C |

Also define and record mutation SSE event types:
- `mutation_requested` — API persisted signal artifact, response returned
- `mutation_accepted` — controller consumed signal, validation passed
- `mutation_applied` — controller completed state transition
- `mutation_rejected` — controller validation failed
- `mutation_timed_out` — controller did not process within 10s

Format: max 5 lines per decision.

#### Acceptance Criteria

1. D-081→D-096 present in DECISIONS.md (13 new decisions)
2. Mutation SSE event types recorded
3. Max 5 lines per decision
4. `grep "D-096" docs/ai/DECISIONS.md` → result found

#### Evidence

```bash
grep -c "^## D-" docs/ai/DECISIONS.md
# Expected: previous count + 13
```

---

### Task 11.1 — Contract-First Test Suite

| Field | Value |
|-------|-------|
| ID | 11.1 |
| File | `agent/tests/test_mutation_contracts.py` |
| Effort | L |
| Dependency | 11.0 (decisions frozen) |
| Dependents | 11.4, 11.5, 11.6 |

#### Scope

Tests written BEFORE endpoint code. All tests initially FAIL.

| # | Test | Expected |
|---|------|----------|
| 1 | POST mutation → immediate response with lifecycleState=requested | requestedAt populated, acceptedAt null |
| 2 | requestId lifecycle: requested → accepted → applied (SSE) | mutation_accepted + mutation_applied events with requestId |
| 3 | requestId lifecycle: requested → accepted → rejected (SSE) | mutation_rejected event, rejectedReason populated |
| 4 | requestId lifecycle: requested → timed_out (SSE) | mutation_timed_out event after 10s |
| 5 | duplicate mutation → 409 | idempotency (same requestId) |
| 6 | invalid FSM state → rejected | approve on non-approval_wait state |
| 7 | audit log fields present | requestId, tabId, sessionId, operation, targetId |
| 8 | atomic request artifact created | signal file exists after POST |
| 9 | CSRF: missing Origin → 403 | Origin header validation |
| 10 | 2-tab race: simultaneous approve → first 200, second 409 | concurrency |
| 11 | cancel during active execution → graceful abort | FSM transition |

#### Acceptance Criteria

1. 11 tests in file
2. Committed BEFORE endpoint code exists
3. All tests FAIL (no endpoints yet)
4. `pytest tests/test_mutation_contracts.py -v` → 11 FAILED, 0 ERROR

#### Evidence

```bash
pytest tests/test_mutation_contracts.py -v 2>&1 | tee evidence/sprint-11/contract-tests-initial.txt
# Expected: 11 FAILED (no endpoints)
```

---

### Task 11.12 — Manual Operator Drill

| Field | Value |
|-------|-------|
| ID | 11.12 |
| File | `evidence/sprint-11/mutation-drill.txt` |
| Effort | M |
| Dependency | 11.10 (all mutation UI working) |
| Dependents | 11.FINAL |

#### Scope

With backend + frontend running, 5 live scenarios:

| # | Scenario | Expected | PASS/FAIL |
|---|----------|----------|-----------|
| 1 | 2 tabs approve same approval | First 200, second 409 | |
| 2 | Retry while mission pending | Rejected (invalid state) | |
| 3 | Cancel during active LLM call | Graceful abort + SSE mutation_applied event | |
| 4 | Heartbeat timeout then mutation attempt | Polling fallback, mutation still works | |
| 5 | Stale SSE + manual refresh after mutation | Current state visible | |

5/5 PASS required before closure_status can advance.

#### Evidence

Each scenario result written to `evidence/sprint-11/mutation-drill.txt`.

---

## Risk Table

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Race condition on concurrent approve | HIGH | MEDIUM | API mutation endpoint only writes atomic request artifact; runtime/controller remains sole executor (D-001, D-062, D-063) |
| CSRF on mutation endpoint | HIGH | LOW | D-089: SameSite=Strict + Origin header check |
| Fire-and-forget mutation | HIGH | MEDIUM | D-096: requestId + lifecycleState mandatory |
| SSE disconnect during mutation | MEDIUM | MEDIUM | D-091: server-confirmed, polling fallback |
| Optimistic UI state corruption | HIGH | LOW | D-091: no optimistic UI, wait for SSE confirm |

---

## Implementation Notes
| Planned | Actual | Reason |
|---------|--------|--------|
| (Copilot updates during sprint) | | |

## File Manifest (Updated at closure)
| File | Type | Task |
|------|------|------|
| (Generated from actual repo state at closure) | | |

## Evidence Checklist
| Evidence | Command | File | Status |
|----------|---------|------|--------|
| Backend tests | `pytest tests/ -v` | closure-check-output.txt | ⬜ |
| Frontend tests | `npx vitest run` | closure-check-output.txt | ⬜ |
| TypeScript | `npx tsc --noEmit` | closure-check-output.txt | ⬜ |
| Lint | `npm run lint` | closure-check-output.txt | ⬜ |
| Build | `npm run build` | closure-check-output.txt | ⬜ |
| Validator | `validate_sprint_docs.py --sprint 11` | closure-check-output.txt | ⬜ |
| Contract grep | grep mutation contracts | contract-evidence.txt | ⬜ |
| Mutation curl | live endpoint tests | contract-evidence.txt | ⬜ |
| Operator drill | 5 scenario manual test | mutation-drill.txt | ⬜ |
| GPT mid review | review summary | review-mid.md | ⬜ |
| GPT final review | review summary | review-final.md | ⬜ |

## Exit Criteria
| # | Criterion | Task | Status |
|---|----------|------|--------|
| 1 | 4 mutation endpoints working | 11.5, 11.6 | ⬜ |
| 2 | CSRF evidence present | 11.2 | ⬜ |
| 3 | requestId lifecycle evidence present | 11.1, 11.5 | ⬜ |
| 4 | SSE mutation event correlation present | 11.10 | ⬜ |
| 5 | 2-tab race test PASS | 11.12 | ⬜ |
| 6 | cancel/retry live drill PASS | 11.12 | ⬜ |
| 7 | Validator PASS | 11.FINAL | ⬜ |
| 8 | GPT review 0 blocking | 11.FINAL | ⬜ |
| 9 | Claude assessment 0 blocking | 11.FINAL | ⬜ |
| 10 | Closure packet complete | 11.FINAL | ⬜ |
| 11 | Contract-first tests all PASS | 11.1→11.6 | ⬜ |
| 12 | Operator drill 5/5 PASS | 11.12 | ⬜ |
| 13 | Retrospective produced | 11.FINAL | ⬜ |

## Retrospective
(Produced at sprint end — minimum content per Section 14 of PROJECT_INSTRUCTIONS)

## Closure Deliverables

When Sprint 11 implementation_status=done:

1. `bash tools/sprint-closure-check.sh 11` → evidence/sprint-11/closure-check-output.txt
2. Contract grep evidence → evidence/sprint-11/contract-evidence.txt
3. Operator drill → evidence/sprint-11/mutation-drill.txt
4. Task breakdown Results section updated
5. STATE.md updated (1 line)
6. NEXT.md updated
7. Retrospective section completed

No separate phase report. Task breakdown Results section is sufficient.

---

*Sprint 11 Task Breakdown — OpenClaw Mission Control Center Phase 5C: Intervention*
*Date: 2026-03-25*
*Operator: AKCA | Agent: Claude (Copilot)*
*Decisions: D-089, D-090, D-091, D-092, D-096*
