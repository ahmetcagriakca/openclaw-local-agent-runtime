# DECISIONS.md Delta — Sprint 12 Kickoff

**Date:** 2026-03-26
**Source:** Operator approval (OD-11→OD-16)
**Action:** Append to docs/ai/DECISIONS.md

---

## D-097: Legacy dashboard retired — removal deferred

**Phase:** 5D (Sprint 12) | **Status:** Frozen

**Context:** Mission Control (:8003 + :3000) fully replaces legacy health dashboard (:8002). Two dashboards running in parallel creates operational confusion and maintenance burden.

**Decision:** Legacy dashboard is deprecated in Sprint 12. Deprecation banner added to UI, startup log warning emitted. Code removal deferred to Sprint 13.

**Trade-off:** Keeping code in Sprint 12 avoids regression risk during Phase 5 closure. Removal in Sprint 13 (stabilization sprint) is lower risk.

**Impacted files:** Legacy dashboard UI (deprecation banner), startup script (log warning), OPERATOR-GUIDE.md (deprecation notice).

**Validation:** Deprecation banner visible at localhost:8002. Startup log contains warning. OPERATOR-GUIDE.md documents deprecation.

**Rollback:** Remove deprecation banner and log warning. Restore parallel-run status.

---

## D-098: API-level E2E with httpx + pytest — browser E2E deferred

**Phase:** 5D (Sprint 12) | **Status:** Frozen

**Context:** Phase 5 needs E2E coverage of Mission Control API. Browser-level E2E (Playwright/Cypress) adds infrastructure complexity without proportional value at this stage.

**Decision:** E2E tests use `httpx` + `pytest` for API-level testing. Browser E2E is deferred to Phase 6.

**Trade-off:** API-level E2E covers critical paths (roles, signals, approvals, SSE) without browser driver overhead. UI interaction coverage is deferred but not eliminated.

**Impacted files:** `tests/e2e/conftest.py`, `tests/e2e/test_smoke.py`, `tests/e2e/test_scenarios.py`.

**Validation:** `pytest tests/e2e/ -v` → 12+ PASS, 0 FAIL. Tests isolated from unit test suite.

**Rollback:** Add browser E2E framework alongside httpx tests. No conflict.

---

## D-099: Approval model changes are Phase 6 scope

**Phase:** 5D (Sprint 12) | **Status:** Frozen

**Context:** Current approval model is definition-level preapproval (D-012). Potential enhancements (dynamic approval, per-request approval, approval delegation) require design work beyond Phase 5 scope.

**Decision:** Approval model changes are out of Sprint 12 and Phase 5 scope. Current preapproval model (D-012) remains unchanged. Any approval evolution is Phase 6 work.

**Trade-off:** Defers flexibility for stability. Phase 5 closes with a proven, tested approval model rather than a partially redesigned one.

**Impacted files:** None in Sprint 12. D-012 remains authoritative.

**Validation:** No approval-related code changes in Sprint 12. `grep -r "approvalPolicy" defs/tasks/` shows preapproved only.

**Rollback:** N/A — this is a scope boundary, not a code change.

---

## D-100: OpenAPI spec auto-generated from FastAPI

**Phase:** 5D (Sprint 12) | **Status:** Frozen

**Context:** Mission Control API needs documentation. FastAPI has built-in OpenAPI schema generation. Hand-written specs create drift risk.

**Decision:** OpenAPI spec is generated from FastAPI built-in schema and exported to `docs/api/openapi.json`. No hand-written spec.

**Trade-off:** Auto-generated spec is always in sync with code. Custom documentation (examples, descriptions) added via FastAPI decorators, not external files.

**Impacted files:** `docs/api/openapi.json` (created), FastAPI route decorators (enhanced with response examples).

**Validation:** `curl localhost:8003/openapi.json | python -m json.tool` → valid JSON. Endpoint count matches actual routes.

**Rollback:** Delete `docs/api/openapi.json`. Revert decorator enhancements.

---

## D-101: SSE is Mission Control frontend transport only — amends D-068

**Phase:** 5D (Sprint 12) | **Status:** Frozen | **Amends:** D-068

**Context:** D-068 introduced SSE as a transport mechanism. Ambiguity exists about whether SSE expands Bridge contract responsibilities or is limited to Mission Control frontend.

**Decision:** SSE is a Mission Control frontend transport concern only. It does not amend or expand Bridge contract responsibilities. Bridge contract remains the four operations defined in D-011 (submit_task, get_task_status, cancel_task, get_health). SSE streams are served by Mission Control API (:8003) to the React frontend (:3000).

**Trade-off:** Clear ownership boundary. SSE complexity stays inside Mission Control. Bridge remains stateless single-invocation (D-018).

**Impacted files:** Mission Control API SSE endpoints, React frontend SSE consumer. Bridge code is NOT impacted.

**Validation:** `grep -r "SSE\|EventSource" bridge/` → 0 matches. SSE endpoints exist only in Mission Control API.

**Rollback:** If SSE needs to cross Bridge boundary in Phase 6+, a new decision record is required. D-101 must be explicitly deprecated first.
