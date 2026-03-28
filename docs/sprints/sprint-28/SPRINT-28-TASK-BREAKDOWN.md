# Sprint 28 — Task Breakdown

**Sprint:** 28
**Phase:** 6
**Title:** Auth Hardening + Operational Observability
**Model:** A

**Goal:** Harden auth lifecycle (integration tests, token expiration, session management), deploy Jaeger/Grafana baseline, add auth+observability closure gate.

---

## Track 1: Auth Lifecycle Hardening

**28.1 — Auth integration test baseline**

Add integration tests that exercise the auth middleware with real config/auth.json.

**Repo scope:** `agent/tests/`, `config/`
**Branch:** `sprint-28/t28.1-auth-integration-tests`

**Implementation:**
1. Create test fixture that writes temp auth.json with test keys
2. Test: valid operator key → 200 on mutation
3. Test: valid viewer key → 403 on mutation
4. Test: invalid key → 401
5. Test: missing header → 401 (when auth enabled)
6. Test: no auth.json → mutations allowed (backward compat)

**Acceptance:** 6+ new auth integration tests, all pass with pytest

---

**28.2 — Session expiration and token rotation**

Add token expiration support and rotation handling.

**Repo scope:** `agent/auth/`, `frontend/src/auth/`
**Branch:** `sprint-28/t28.2-session-expiration`

**Implementation:**
1. Add `expires_at` field to auth.json key entries
2. Validate expiration in key validation
3. Return 401 with "Token expired" for expired keys
4. Frontend: detect 401, redirect to login, clear stored key
5. Add expiration tests

**Acceptance:** Expired keys rejected, frontend handles 401 gracefully

---

## Gates

**28.G1 — Mid Review Gate**

After Track 1. Branch-exempt.

---

## Track 2: Observability + Closure

**28.3 — Frontend auth/session test expansion**

Deepen frontend test coverage around auth lifecycle.

**Repo scope:** `frontend/src/__tests__/`
**Branch:** `sprint-28/t28.3-frontend-auth-tests`
**Depends on:** 28.G1

**Implementation:**
1. Test LoginPage: form validation, submit, error display
2. Test session expiration UX (401 detection)
3. Test route guard behavior
4. Target: 70+ total frontend tests

**Acceptance:** 10+ new tests, 70+ total

---

**28.4 — Jaeger/Grafana deployment baseline**

Add observability stack to Docker Compose for local dev.

**Repo scope:** `docker-compose.yml`, `docs/shared/`
**Branch:** `sprint-28/t28.4-observability-stack`
**Depends on:** 28.G1

**Implementation:**
1. Add Jaeger container to docker-compose.yml (all-in-one)
2. Configure OTel exporter in API to send traces to Jaeger
3. Add Grafana container with basic dashboard config
4. Update DEV-RUNTIME.md with observability instructions
5. Verify traces visible in Jaeger UI

**Acceptance:** Jaeger receives traces from API, Grafana accessible

---

**28.5 — Auth + observability closure gate**

Update closure validation for auth and observability requirements.

**Repo scope:** `tools/`, `.github/workflows/`
**Branch:** `sprint-28/t28.5-closure-gate`
**Depends on:** 28.G1

**Implementation:**
1. Add auth config presence check to closure validation
2. Add trace header emission check
3. Update closure script with new checks
4. Evidence: grep output for auth/trace coverage

**Acceptance:** Closure gate checks auth and observability baseline

---

**28.G2 — Final Review Gate**
**28.RETRO — Retrospective**
**28.CLOSURE — Sprint Closure**

---

## Carry-Forward

| Item | Target |
|------|--------|
| Plugin system | S29+ |
| Mission templates | S29+ |
| Cost tracking/billing | S29+ |
| Webhook notifications | S29+ |

## Output Files

| Task | Output |
|------|--------|
| 28.1 | `agent/tests/test_auth_integration.py` |
| 28.2 | `agent/auth/keys.py` (expiration), frontend 401 handling |
| 28.3 | `frontend/src/__tests__/*.test.tsx` |
| 28.4 | `docker-compose.yml` (Jaeger, Grafana) |
| 28.5 | Updated closure scripts |
