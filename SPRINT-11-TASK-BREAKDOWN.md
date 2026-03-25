# Sprint 11 — Phase 5C: Intervention — Task Breakdown

**Date:** 2026-03-26
**implementation_status:** not_started
**closure_status:** not_started
**Author:** Operator (AKCA) + Claude Opus 4.6
**Prerequisite:** Sprint 10 closure_status=closed
**Risk Level:** HIGH — read-only → read-write transition, mutation safety critical
**Estimated Duration:** 5-7 days

---

## Section 1: Sprint Goal

Deliver operator intervention from the dashboard: approve, reject, retry, cancel. Transition from read-only sprints (8-9-10) to mutation sprint. Every mutation writes an atomic request artifact; runtime/controller remains the sole executor. Every mutation is auditable, server-confirmed, and SSE-correlated.

**Definition of Done (all must be true):**
- 4 mutation endpoints working (approve, reject, cancel, retry)
- CSRF protection on all mutation endpoints (D-089)
- Atomic request artifact bridge — no direct controller/service method calls (D-001, D-062, D-063)
- D-096 lifecycle enforced: requested → accepted → applied | rejected | timed_out
- Every mutation audited (requestId, tabId, sessionId, operation, targetId, outcome)
- SSE mutation events: mutation_requested, mutation_accepted, mutation_applied, mutation_rejected, mutation_timed_out
- Destructive actions (cancel, reject) require confirmation dialog (D-090)
- Server-confirmed UI refresh, no optimistic UI (D-091)
- Approval sunset Phase 1: dashboard approve \<id\>, Telegram yes/no deprecated warning (D-092)
- Contract-first tests all PASS (11 tests)
- Operator drill 5/5 PASS
- GPT mid-review PASS, GPT final review PASS
- Retrospective produced
- 0 TypeScript errors, 0 lint errors, production build success

---

## Section 2: Frozen Decisions

### D-089: CSRF — SameSite=Strict + Origin Header Check

**Phase:** 5C | **Status:** Frozen

Localhost + single-operator + modern browser → SameSite=Strict cookie + Origin header validation. Double-submit cookie unnecessary complexity for this environment. Mutation endpoints reject requests without valid Origin header (→ 403).

**Trade-off:** Less protection than double-submit cookie on older browsers. Acceptable: system is localhost-only (D-070).

### D-090: Mutation Confirmation — Confirm Dialog for Destructive Actions

**Phase:** 5C | **Status:** Frozen

Destructive actions (cancel, reject) → confirmation dialog before request. Non-destructive actions (approve, retry) → single click. No undo mechanism — mutations are irreversible.

### D-091: Mutation UI — Server-Confirmed (No Optimistic UI)

**Phase:** 5C | **Status:** Frozen

Mutation request → wait for server response → SSE event confirms state change → UI refreshes. No optimistic state updates. 100-500ms delay acceptable — operator dashboard, not real-time trading.

**Trade-off:** Slower UX but zero chance of showing incorrect state.

### D-092: Approval Sunset Phase 1

**Phase:** 5C | **Status:** Frozen

Dashboard approve \<approvalId\> / reject \<approvalId\>. Telegram yes/no still works but shows deprecated warning. Full removal in Sprint 12 (D-095).

### D-096: Mutation Response Contract — Full Lifecycle

**Phase:** 5C | **Status:** Frozen

Every mutation endpoint returns:
```json
{
  "requestId": "req-uuid",
  "lifecycleState": "requested",
  "targetId": "approval-id or mission-id",
  "requestedAt": "ISO-8601",
  "acceptedAt": null,
  "appliedAt": null,
  "rejectedReason": null,
  "timeoutAt": null
}
```

Lifecycle: `requested → accepted → applied | rejected | timed_out`
- `requested` = API persisted signal artifact. Response returns immediately.
- `accepted` = controller consumed signal, validation passed (SSE: mutation_accepted)
- `applied` = state transition completed (SSE: mutation_applied)
- `rejected` = validation failed (SSE: mutation_rejected)
- `timed_out` = controller did not process within 10s (SSE: mutation_timed_out)

API response always returns `lifecycleState=requested`. Subsequent states via SSE only. Client stores requestId, correlates via SSE. Fire-and-forget forbidden.

### OD-10 Resolution: Retry Semantics

**Status:** Frozen

Retry = existing controller `retry_mission()` triggered via atomic signal artifact → creates new mission with link to failed original. Same semantics as runtime retry (D-008 chain depth limit applies).

### OD-13 Resolution: Mutation Rate Limit

**Status:** Waived

Localhost single-operator system. D-070 provides sufficient access control. No additional rate limiting for Sprint 11. If multi-user access is added in the future, rate limiting becomes mandatory.

---

## Section 3: Mutation Bridge Architecture

**Single Rule (D-001, D-062, D-063):**
API mutation endpoint only writes atomic request artifact; runtime/controller remains sole executor.

### Signal Flow

```
Dashboard UI
  → POST /api/v1/approvals/{id}/approve
    → API validates request (CSRF, FSM state, target exists)
    → API writes atomic signal artifact:
        logs/missions/{missionId}/approve-request-{uuid}.json
    → SSE: mutation_requested (best-effort emit, may be missed)
    → API returns { lifecycleState: "requested", requestId: uuid }

Note: ordering is artifact persisted → SSE best-effort → HTTP response.
Response is source of truth. If SSE mutation_requested is missed,
client still has lifecycleState=requested from the response.

Controller (next poll cycle, ~1s):
  → Reads signal artifact
  → Validates (FSM state check, idempotency)
  → If valid:
      → approval_service.approve(id)
      → FSM state transition
      → Removes signal artifact
      → SSE: mutation_accepted → mutation_applied
  → If invalid:
      → SSE: mutation_rejected (reason)
  → If timeout (10s):
      → SSE: mutation_timed_out
```

### Signal Artifact Format

```json
{
  "requestId": "req-uuid",
  "type": "approve",
  "targetId": "approval-id",
  "missionId": "mission-id",
  "requestedAt": "ISO-8601",
  "source": "dashboard",
  "operatorInfo": {
    "tabId": "tab-uuid",
    "sessionId": "session-id"
  }
}
```

### Mutation Endpoints

| Method | Path | Action | Signal Artifact |
|--------|------|--------|----------------|
| POST | `/api/v1/approvals/{id}/approve` | Approve pending approval | `approve-request-{uuid}.json` |
| POST | `/api/v1/approvals/{id}/reject` | Reject pending approval | `reject-request-{uuid}.json` |
| POST | `/api/v1/missions/{id}/cancel` | Cancel running mission | `cancel-request-{uuid}.json` |
| POST | `/api/v1/missions/{id}/retry` | Retry failed mission | `retry-request-{uuid}.json` |

### Audit Log Fields

Every mutation logs to `logs/mission-control-api.log`:
- `timestamp`, `source: "dashboard"`, `operation`, `targetId`, `outcome`, `requestId`, `tabId`, `sessionId`

---

## Section 4: SSE Mutation Events (D-086 Extension)

Added to Sprint 10 event registry:

| Event Type | Trigger | Data |
|-----------|---------|------|
| `mutation_requested` | API persisted signal artifact | `{ requestId, targetId, type }` |
| `mutation_accepted` | Controller consumed signal, validation passed | `{ requestId, targetId, type }` |
| `mutation_applied` | Controller completed state transition | `{ requestId, targetId, type, newState }` |
| `mutation_rejected` | Controller validation failed | `{ requestId, targetId, reason }` |
| `mutation_timed_out` | Controller did not process within 10s | `{ requestId, targetId }` |

Frontend correlates via `requestId`: mutation button → store requestId → listen SSE → match → update UI.

**Event ordering rule:** Signal artifact atomically persisted → SSE `mutation_requested` best-effort emit → HTTP response returns `lifecycleState=requested`. Response is the source of truth. If SSE `mutation_requested` is lost (disconnect, race), client proceeds on HTTP response alone. SSE events for subsequent states (`accepted`, `applied`, `rejected`, `timed_out`) remain the only channel.

---

## Section 5: Task List

| Task | Description | Effort | Side | Dependency |
|------|-------------|--------|------|------------|
| 11.0 | DECISIONS.md debt: write D-081→D-096 (13 decisions) | M | Docs | — |
| 11.1 | Contract-first test suite (11 tests) | L | Backend | 11.0 |
| 11.2 | CSRF middleware (SameSite + Origin) | S | Backend | — |
| 11.3 | Mutation audit logger | S | Backend | — |
| 11.4 | Atomic request artifact bridge | M | Backend | 11.1 |
| 11.5 | Approve/Reject endpoints + MutationResponse | L | Backend | 11.1, 11.2, 11.3, 11.4 |
| 11.6 | Cancel/Retry endpoints | L | Backend | 11.1, 11.2, 11.3, 11.4 |
| **11.MID** | **GPT mid-sprint review — BLOCKER** | — | GPT | 11.5, 11.6 |
| 11.7 | Confirmation dialog component | S | Frontend | — |
| 11.8 | Approval page mutation buttons | M | Frontend | 11.5 ready |
| 11.9 | Mission detail cancel/retry buttons | M | Frontend | 11.6 ready |
| 11.10 | Mutation feedback (spinner, error toast, SSE confirm) | M | Frontend | 11.8, 11.9 |
| 11.11 | Approval sunset warning (Telegram deprecated) | S | Backend | 11.5 |
| 11.12 | Manual operator drill (5 scenarios) | M | Operator | 11.10 |
| **11.FINAL** | **GPT final review + Claude assessment — BLOCKER** | — | GPT+Claude | 11.12 |

**Rules:**
- 11.MID PASS required before 11.7+ starts
- 11.FINAL PASS required before closure_status advances
- 1 task = 1 commit minimum

---

## Section 6: Task Cards

### Task 11.0 — DECISIONS.md Debt Burn-Down

| Field | Value |
|-------|-------|
| File | `docs/ai/DECISIONS.md` |
| Effort | M |

Write D-081→D-096 to DECISIONS.md. Max 5 lines per decision. Include mutation SSE event types. See DECISION-DEBT-BURNDOWN.md for full list.

**Acceptance:** Each of D-081, D-082, D-083, D-084, D-085, D-086, D-087, D-088, D-089, D-090, D-091, D-092, D-096 present in DECISIONS.md.

```bash
for ID in D-081 D-082 D-083 D-084 D-085 D-086 D-087 D-088 D-089 D-090 D-091 D-092 D-096; do
  grep -q "$ID" docs/ai/DECISIONS.md && echo "$ID ✅" || echo "$ID ❌ MISSING"
done
```

---

### Task 11.1 — Contract-First Test Suite

| Field | Value |
|-------|-------|
| File | `agent/tests/test_mutation_contracts.py` |
| Effort | L |
| Dependency | 11.0 |

Tests written BEFORE endpoint code. All initially FAIL.

| # | Test | Expected |
|---|------|----------|
| 1 | POST mutation → lifecycleState=requested | requestedAt populated, acceptedAt null |
| 2 | requested → accepted → applied (SSE) | mutation_accepted + mutation_applied with requestId |
| 3 | requested → accepted → rejected (SSE) | mutation_rejected, rejectedReason populated |
| 4 | requested → timed_out (SSE) | mutation_timed_out after 10s |
| 5 | duplicate mutation on same target while active/pending → 409 | same targetId + same action + pending window → conflict. requestId is for correlation, not idempotency |
| 6 | invalid FSM state → rejected | approve on non-approval_wait |
| 7 | audit log fields present | requestId, tabId, sessionId, operation, targetId |
| 8 | atomic request artifact created | signal file exists after POST |
| 9 | CSRF: missing Origin → 403 | Origin header validation |
| 10 | 2-tab race: simultaneous approve | first 200, second 409 |
| 11 | cancel during active execution | graceful abort, FSM transition |

**Acceptance:** 11 FAILED, 0 ERROR (endpoints don't exist yet)
**Evidence (initial):** `pytest tests/test_mutation_contracts.py -v > evidence/sprint-11/contract-tests-initial.txt`
**Evidence (final):** `pytest tests/test_mutation_contracts.py -v > evidence/sprint-11/contract-tests-final.txt` (after endpoints implemented, 11 PASSED)

---

### Task 11.2 — CSRF Middleware

| Field | Value |
|-------|-------|
| File | `agent/api/csrf_middleware.py` |
| Effort | S |

SameSite=Strict + Origin header check (D-089). Reject non-localhost Origin → 403. Applied to all POST endpoints only.

---

### Task 11.3 — Mutation Audit Logger

| Field | Value |
|-------|-------|
| File | `agent/api/mutation_audit.py` |
| Effort | S |

Log every mutation: timestamp, source, operation, targetId, outcome, requestId, tabId, sessionId. Append to `logs/mission-control-api.log`.

---

### Task 11.4 — Atomic Request Artifact Bridge

| Field | Value |
|-------|-------|
| File | `agent/api/mutation_bridge.py` |
| Effort | M |
| Dependency | 11.1 |

Write signal artifacts atomically (D-071 pattern). Controller reads and consumes. No direct service/method call from API layer.

---

### Task 11.5 — Approve/Reject Endpoints

| Field | Value |
|-------|-------|
| File | `agent/api/approval_mutation_api.py` |
| Effort | L |
| Dependency | 11.1, 11.2, 11.3, 11.4 |

POST `/api/v1/approvals/{id}/approve` and `/reject`. MutationResponse with D-096 lifecycle. Signal artifact via mutation_bridge. SSE events via SSEManager.

---

### Task 11.6 — Cancel/Retry Endpoints

| Field | Value |
|-------|-------|
| File | `agent/api/mission_mutation_api.py` |
| Effort | L |
| Dependency | 11.1, 11.2, 11.3, 11.4 |

POST `/api/v1/missions/{id}/cancel` and `/retry`. Same pattern as 11.5.

---

### Task 11.7 — Confirmation Dialog Component

| Field | Value |
|-------|-------|
| File | `frontend/src/components/ConfirmDialog.tsx` |
| Effort | S |

Reusable dialog for destructive actions (D-090). Title, message, confirm/cancel buttons. Red styling for destructive.

---

### Task 11.8 — Approval Page Mutation Buttons

| Field | Value |
|-------|-------|
| File | `frontend/src/pages/ApprovalsPage.tsx` (modified) |
| Effort | M |

Pending approval → Approve (green) + Reject (red, confirm dialog). Disabled + spinner during request. SSE mutation_applied → refresh.

---

### Task 11.9 — Mission Detail Cancel/Retry Buttons

| Field | Value |
|-------|-------|
| File | `frontend/src/pages/MissionDetailPage.tsx` (modified) |
| Effort | M |

Running mission → Cancel (red, confirm dialog). Failed/aborted → Retry (blue). Completed → no buttons.

---

### Task 11.10 — Mutation Feedback

| Field | Value |
|-------|-------|
| File | `frontend/src/hooks/useMutation.ts`, page modifications |
| Effort | M |
| Dependency | 11.8, 11.9 |

| State | UI |
|-------|-----|
| Sending | Button disabled + spinner |
| Success (SSE mutation_applied) | Page refresh, new state visible |
| Failure (SSE mutation_rejected) | Error toast + button re-enabled |
| Timeout (10s, SSE mutation_timed_out) | "Operation timed out" warning + manual refresh |

---

### Task 11.11 — Approval Sunset Warning

| Field | Value |
|-------|-------|
| File | `agent/services/approval_service.py` (modified) |
| Effort | S |

When Telegram yes/no approval is used, log deprecation warning. D-092 Phase 1.

---

### Task 11.12 — Manual Operator Drill

| Field | Value |
|-------|-------|
| File | `evidence/sprint-11/mutation-drill.txt` |
| Effort | M |
| Dependency | 11.10 |

Backend + frontend running. 5 live scenarios:

| # | Scenario | Expected | PASS/FAIL |
|---|----------|----------|-----------|
| 1 | 2 tabs approve same approval | First 200, second 409 | |
| 2 | Retry while mission pending | Rejected (invalid state) | |
| 3 | Cancel during active LLM call | Graceful abort + SSE event | |
| 4 | Heartbeat timeout then mutation | Polling fallback, mutation works | |
| 5 | Stale SSE + manual refresh after mutation | Current state visible | |

5/5 PASS required before 11.FINAL.

---

## Section 7: Exit Criteria

| # | Criterion | Task | Status |
|---|----------|------|--------|
| 1 | 4 mutation endpoints working | 11.5, 11.6 | ⬜ |
| 2 | CSRF evidence present | 11.2 | ⬜ |
| 3 | requestId lifecycle evidence (requested→applied) | 11.1, 11.5 | ⬜ |
| 4 | SSE mutation event correlation working | 11.10 | ⬜ |
| 5 | 2-tab race test PASS | 11.12 | ⬜ |
| 6 | cancel/retry live drill PASS | 11.12 | ⬜ |
| 7 | Validator PASS | 11.FINAL | ⬜ |
| 8 | GPT mid-review 0 blocking | 11.MID | ⬜ |
| 9 | GPT final review 0 blocking | 11.FINAL | ⬜ |
| 10 | Claude assessment 0 blocking | 11.FINAL | ⬜ |
| 11 | Contract-first tests all PASS | 11.1→11.6 | ⬜ |
| 12 | Operator drill 5/5 PASS | 11.12 | ⬜ |
| 13 | Closure packet complete | 11.FINAL | ⬜ |
| 14 | Retrospective produced with actions | 11.FINAL | ⬜ |
| 15 | No direct service/method call in API layer | 11.4 | ⬜ |

---

## Section 8: Evidence Checklist

| Evidence | Command | File | Status |
|----------|---------|------|--------|
| Backend tests | `pytest tests/ -v` | closure-check-output.txt | ⬜ |
| Frontend tests | `npx vitest run` | closure-check-output.txt | ⬜ |
| TypeScript | `npx tsc --noEmit` | closure-check-output.txt | ⬜ |
| Lint | `npm run lint` | closure-check-output.txt | ⬜ |
| Build | `npm run build` | closure-check-output.txt | ⬜ |
| Validator | `validate_sprint_docs.py --sprint 11` | closure-check-output.txt | ⬜ |
| Contract grep: events | `grep -rn 'mutation_requested\|mutation_accepted\|mutation_applied\|mutation_rejected\|mutation_timed_out' agent/api/` | contract-evidence.txt | ⬜ |
| Contract grep: lifecycle | `grep -rn 'requestId\|lifecycleState' agent/api/schemas.py` | contract-evidence.txt | ⬜ |
| Contract grep: no direct exec | `grep -rn 'def approve\|def reject\|def cancel_mission\|def retry_mission' agent/api/` → expect CLEAN | contract-evidence.txt | ⬜ |
| Mutation curl | live endpoint POST tests | contract-evidence.txt | ⬜ |
| CSRF check | `curl -X POST without Origin → 403` | contract-evidence.txt | ⬜ |
| Operator drill | 5 scenario manual test | mutation-drill.txt | ⬜ |
| GPT mid review | review summary | review-mid.md | ⬜ |
| GPT final review | review summary | review-final.md | ⬜ |
| Ownership negative grep | `grep -rnE 'from.*controller\|import.*controller\|from.*service\|import.*service' agent/api/` | ownership-grep.txt | ⬜ |
| Bridge negative grep | `grep -rnE '\.approve\(\|\.reject\(\|\.cancel_mission\(\|\.retry_mission\(' agent/api/` | bridge-check.txt | ⬜ |
| Schema additive compatibility | MutationResponse additive check + read-model schemas intact | schema-compatibility.txt | ⬜ |
| Full lifecycle event set | `grep -rnE 'mutation_requested\|mutation_accepted\|...\|requestId\|lifecycleState' agent/ frontend/` | contract-evidence.txt | ⬜ |
| Live endpoint checks | approval/cancel/retry endpoint POST verification | live-checks.txt | ⬜ |

### 11.FINAL Raw Evidence Checklist

- [ ] `evidence/sprint-11/ownership-grep.txt` saved
- [ ] `evidence/sprint-11/bridge-check.txt` saved
- [ ] `evidence/sprint-11/schema-compatibility.txt` saved
- [ ] `evidence/sprint-11/contract-evidence.txt` includes full lifecycle event set
- [ ] `evidence/sprint-11/mutation-drill.txt` saved
- [ ] `evidence/sprint-11/live-checks.txt` includes approval/cancel/retry endpoint checks

### 11.FINAL Additional Acceptance Criteria

9. Raw grep evidence proves API layer does not directly execute controller/service mutation logic.
10. Raw compatibility evidence proves mutation schema is additive and does not break existing read-model contracts.
11. Manual operator drill evidence exists for two-tab race, cancel, retry, timeout, and SSE correlation.

---

## Section 9: Implementation Notes

| Planned | Actual | Reason |
|---------|--------|--------|
| (Copilot updates during sprint) | | |

---

## Section 10: File Manifest (Updated at closure)

| File | Type | Task |
|------|------|------|
| (Generated from actual repo state at closure) | | |

---

## Section 11: Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mutation bypasses runtime (D-001 violation) | CRITICAL | 11.4: atomic signal artifact only. Script checks no direct method call in API layer |
| CSRF token bypass | HIGH | D-089: SameSite + Origin. Localhost-only (D-070) |
| Race condition: 2 tabs same approval | MEDIUM | Server-side idempotency: already approved → 409 |
| Approval state transition invalid | MEDIUM | FSM validation: only approval_wait → approve/reject |
| Cancel during active LLM call | MEDIUM | Graceful cancellation signal, timeout |
| Signal artifact left unprocessed | LOW | Controller polls every 1s. 10s timeout → mutation_timed_out SSE |

**Risk mitigation rule:** API mutation endpoint only writes atomic request artifact; runtime/controller remains sole executor (D-001, D-062, D-063).

---

## Section 12: Sprint 11 Kickoff Gate

All must be ✅ before Task 11.0 starts:

| # | Gate | Owner | Status |
|---|------|-------|--------|
| 1 | Sprint 10 closure_status=closed | Operator | ⬜ |
| 2 | Process package merged (PROCESS-GATES.md, closure script, etc.) | Copilot | ⬜ |
| 3 | D-089 frozen (CSRF) | Claude | ⬜ |
| 4 | D-090 frozen (confirm dialog) | Claude | ⬜ |
| 5 | D-091 frozen (server-confirmed, no optimistic) | Claude | ⬜ |
| 6 | D-092 frozen (approval sunset Phase 1) | Claude | ⬜ |
| 7 | D-096 frozen (mutation lifecycle) | Claude | ⬜ |
| 8 | OD-10 frozen (retry semantics) | Claude | ⬜ |
| 9 | OD-13 waived (rate limit) | Claude | ⬜ |
| 10 | evidence/sprint-11/ directory created | Copilot | ⬜ |
| 11 | Pre-sprint GPT review PASS | GPT | ⬜ |
| 12 | Mutation SSE event types defined (Section 4) | Claude | ⬜ |

12/12 ✅ → implementation starts with Task 11.0.

---

## Section 13: Closure Deliverables

When implementation_status=done:

1. `bash tools/sprint-closure-check.sh 11` → evidence/sprint-11/closure-check-output.txt
2. Contract grep → evidence/sprint-11/contract-evidence.txt
3. Operator drill → evidence/sprint-11/mutation-drill.txt
4. This document: Results section + exit criteria updated
5. STATE.md updated (1 line)
6. NEXT.md updated

No separate phase report. This document's Results section is sufficient.

---

## Section 14: Retrospective

(Produced at sprint end — minimum content per PROCESS-GATES.md Section 13)

---

*Sprint 11 Task Breakdown — OpenClaw Mission Control Center Intervention*
*Date: 2026-03-26*
*Operator: AKCA | Architect: Claude Opus 4.6*
*Decisions Frozen: D-089, D-090, D-091, D-092, D-096*
*Decisions Waived: OD-13 (rate limit)*
*Decisions Resolved: OD-10 (retry semantics)*
