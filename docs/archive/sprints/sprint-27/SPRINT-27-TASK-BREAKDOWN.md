# Sprint 27 — Task Breakdown

**Sprint:** 27
**Phase:** 6
**Title:** Identity Foundation + Deterministic Delivery
**Model:** A

**Goal:** Establish multi-user auth baseline (D-104/D-108), add mock LLM provider for deterministic E2E, and Docker build CI gate.

---

## Track 1: Auth Foundation

**27.1 — Multi-user auth freeze pack**

Reconcile D-104/D-108 into a single implementation contract. No code — planning and decision freeze only.

**Repo scope:** `docs/ai/DECISIONS.md`, `docs/decisions/`
**Depends on:** —
**Branch:** `sprint-27/t27.1-auth-freeze`

**Implementation:**
1. Review D-104 (multi-user auth decision) and D-108 (session model)
2. Define: auth boundary, tenant/user/role model, session lifecycle
3. Map impacted files (middleware, routes, frontend)
4. Define migration path and backward compatibility
5. Freeze as D-117: multi-user auth implementation contract

**Acceptance:**
1. D-117 frozen with auth model, role hierarchy, session lifecycle
2. Impacted files mapped
3. No ambiguity — implementation can start from this contract
4. Evidence: D-117 content

---

**27.2 — Backend multi-user auth baseline**

Implement auth middleware, user/session resolution, protected routes.

**Repo scope:** `agent/auth/`, `agent/api/`
**Depends on:** 27.1 (D-117 must be frozen)
**Branch:** `sprint-27/t27.2-backend-auth`

**Implementation:**
1. Create auth middleware: token validation, user context extraction
2. Add user/role model with operator and viewer roles
3. Protect mutation endpoints (approve, reject, cancel, retry)
4. Read-only endpoints remain public
5. Add auth tests

**Acceptance:**
1. Auth middleware active on mutation endpoints
2. Unauthenticated mutation → 401
3. Read-only endpoints work without auth
4. Auth tests pass
5. Evidence: pytest output with auth tests

---

## Gates

**27.G1 — Mid Review Gate**

After Track 1 (27.1 + 27.2). Review: D-117 completeness, auth middleware coverage. Branch-exempt.

---

## Track 2: Frontend Auth + Determinism

**27.3 — Frontend auth/session baseline**

Add login flow, route guards, user context to React UI.

**Repo scope:** `frontend/src/`
**Depends on:** 27.G1
**Branch:** `sprint-27/t27.3-frontend-auth`

**Implementation:**
1. Add auth context provider (user state, login/logout)
2. Add route guard HOC for protected pages
3. Add login page (simple token-based for MVP)
4. Handle 401 responses (redirect to login)
5. Add auth component tests

**Acceptance:**
1. Login flow works
2. Protected routes redirect unauthenticated users
3. Auth context available in components
4. Evidence: vitest output with auth tests

---

**27.4 — Mock LLM provider for deterministic E2E**

Add test double provider that returns stable fixture responses.

**Repo scope:** `agent/providers/`, `tests/`
**Depends on:** 27.G1
**Branch:** `sprint-27/t27.4-mock-provider`

**Implementation:**
1. Create `agent/providers/mock_provider.py` implementing base provider interface
2. Return deterministic fixture responses per role/prompt
3. Add E2E test using mock provider for mission execution
4. Ensure mock and live E2E lanes coexist

**Acceptance:**
1. Mock provider returns deterministic responses
2. E2E test with mock provider passes
3. Live E2E tests unaffected
4. Evidence: pytest + e2e output

---

**27.5 — Docker build CI smoke gate**

Build Docker image in CI, verify startup, fail on errors.

**Repo scope:** `.github/workflows/ci.yml`
**Depends on:** 27.G1
**Branch:** `sprint-27/t27.5-docker-ci`

**Implementation:**
1. Add CI job: `docker build -t vezir-api .`
2. Start container, health poll (30s max)
3. Fail CI if build or boot fails
4. Upload build log as artifact

**Acceptance:**
1. Docker build succeeds in CI
2. Container starts and health check passes
3. Build failure → CI fail
4. Evidence: CI workflow run log

---

**27.G2 — Final Review Gate**

Full evidence. Branch-exempt.

**27.RETRO — Retrospective**

Answer: Is auth model right? Is mock provider useful? Is Docker CI reliable?

**27.CLOSURE — Sprint Closure**

All branches merged. GPT operator `closure_status=closed`.

---

## Decisions to Freeze

| ID | Topic | When |
|----|-------|------|
| D-117 | Multi-user auth implementation contract | Before 27.2 |

## Carry-Forward

| Item | Reason | Target |
|------|--------|--------|
| Jaeger/Grafana | Auth first | S28 |
| Plugin system | Auth first | S28+ |
| Mission templates | Auth ownership needed | S28+ |
| Cost tracking | Auth + billing model | S29+ |
| Webhook notifications | Auth permissions | S28+ |

## Output Files

| Task | Output |
|------|--------|
| 27.1 | `docs/decisions/D-117-auth-contract.md` |
| 27.2 | `agent/auth/middleware.py`, auth tests |
| 27.3 | `frontend/src/auth/`, login page, route guards |
| 27.4 | `agent/providers/mock_provider.py`, mock E2E test |
| 27.5 | CI Docker build job |
