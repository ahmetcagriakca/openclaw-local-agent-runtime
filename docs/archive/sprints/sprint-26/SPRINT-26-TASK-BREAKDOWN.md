# Sprint 26 — Task Breakdown

**Sprint:** 26
**Phase:** 6
**Title:** Foundation Hardening — Dev Runtime + Contract Guards + Live E2E
**Model:** A

**Goal:** Pay down real blockers: freeze backend restructure plan (D-115), establish reproducible dev runtime (D-116), guard SDK contract drift, remove S14A live mission waiver, expand frontend test coverage.

---

## Track 1: Architecture + Dev Runtime

**26.1 — Backend restructure freeze pack**

Convert S14A/S14B backend physical restructure from vague carryover into a frozen execution map. No file moves — planning only.

**Repo scope:** `docs/ai/DECISIONS.md` (D-115), `docs/decisions/`
**Depends on:** —
**Branch:** `sprint-26/t26.1-restructure-plan`

**Implementation:**
1. Analyze current `agent/` directory structure — map modules, dependencies, ownership
2. Propose target folder/module map with clear boundaries
3. Define import/dependency rules (what can import what)
4. Create migration sequencing (which moves first, dependency order)
5. Freeze as D-115: backend physical topology / ownership boundary decision

**Acceptance:**
1. D-115 frozen with target topology, import rules, migration sequence
2. No "to be decided during implementation" — all boundaries explicit
3. Blast radius documented per migration step
4. Evidence: D-115 content + dependency analysis output

---

**26.2 — Docker dev environment baseline**

Reproducible one-command local/dev runtime for API + dependencies.

**Repo scope:** `docker-compose.yml`, `Dockerfile`, `docs/shared/`
**Depends on:** —
**Branch:** `sprint-26/t26.2-docker-dev`

**Implementation:**
1. Create `Dockerfile` for Vezir API (Python 3.14 + FastAPI + uvicorn)
2. Create `docker-compose.yml` with API service + health checks
3. Add seed/init script for test data
4. Create operator runbook in `docs/shared/DEV-RUNTIME.md`
5. Verify: `docker compose up` → API healthy on :8003

**Acceptance:**
1. One-command startup (`docker compose up`)
2. API health check passes within 30s
3. No hidden manual prerequisites
4. Evidence: docker boot output + health check output

---

## Gates

**26.G1 — Mid Review Gate**

After Track 1 (26.1 + 26.2). Review: D-115 completeness, Docker boot reliability. Branch-exempt.

---

## Track 2: Contract Guards + Verification

**26.3 — SDK drift detection CI gate**

Regenerate TypeScript SDK in CI, compare against checked-in version, fail on drift.

**Repo scope:** `.github/workflows/ci.yml`, `tools/export_openapi.py`
**Depends on:** 26.G1
**Branch:** `sprint-26/t26.3-sdk-drift`

**Implementation:**
1. Add CI step: `python tools/export_openapi.py` → regenerate `openapi.json`
2. Run `npm run generate:api` → regenerate `generated.ts`
3. `git diff --exit-code frontend/src/api/generated.ts docs/api/openapi.json`
4. Fail CI if drift detected, upload diff as artifact

**Acceptance:**
1. Uncommitted SDK drift fails CI
2. Intentional changes require committed regenerated artifacts
3. Evidence: CI run log (pass + intentional drift fail)

---

**26.4 — Live mission E2E baseline**

Remove S14A waiver with one deterministic live mission happy-path test.

**Repo scope:** `tests/e2e/`, `docker-compose.yml`
**Depends on:** 26.G1 (Docker runtime must work)
**Branch:** `sprint-26/t26.4-live-mission-e2e`

**Implementation:**
1. Write E2E test: create mission → execute → verify completed state
2. Use Docker dev environment for runtime
3. Capture raw execution output
4. Document failure triage notes

**Acceptance:**
1. One happy-path mission flow passes deterministically
2. Pass/fail is deterministic (no flaky)
3. Raw output saved in artifacts
4. S14A waiver can be retired

---

**26.5 — Frontend component test expansion**

Expand coverage around mission-related components and SDK consumer boundaries.

**Repo scope:** `frontend/src/__tests__/`
**Depends on:** 26.G1
**Branch:** `sprint-26/t26.5-component-tests`

**Implementation:**
1. Add tests for StageCard (states, error display, gate results)
2. Add tests for ConfirmDialog (confirm/cancel flows)
3. Add tests for Sidebar (navigation, active state)
4. Cover loading/error states
5. Target: 50+ total frontend tests (from 39)

**Acceptance:**
1. 10+ new component tests
2. Tests cover contract/error states, not just snapshots
3. All existing tests still pass
4. Evidence: vitest output with 49+ tests

---

**26.G2 — Final Review Gate**

Full evidence: pytest + vitest + tsc + docker boot + SDK drift CI + e2e output. Branch-exempt.

**26.RETRO — Retrospective**

Answer: Is Docker dev env reliable? Is SDK drift gate noisy? Is live E2E deterministic?

**26.CLOSURE — Sprint Closure**

All branches merged. Evidence in artifacts/. GPT operator sets `closure_status=closed`.

---

## Decisions to Freeze

| ID | Topic | When |
|----|-------|------|
| D-115 | Backend physical topology / ownership boundaries | Before 26.1 implementation |
| D-116 | Docker dev runtime topology / service composition | Before 26.2 implementation |

---

## Carry-Forward (explicit defer)

| Item | Reason | Target |
|------|--------|--------|
| Multi-user auth | Requires dev runtime first | S27+ |
| Jaeger/Grafana deployment | Infrastructure scope | S27+ |
| Plugin system | Roadmap, not blocker | S27+ |
| Mission templates/presets | Roadmap | S28+ |
| Cost tracking/billing | Roadmap | S28+ |
| Webhook notifications | Roadmap | S28+ |

---

## Output Files

| Task | Output |
|------|--------|
| 26.1 | `docs/ai/DECISIONS.md` (D-115) |
| 26.2 | `Dockerfile`, `docker-compose.yml`, `docs/shared/DEV-RUNTIME.md` |
| 26.3 | `.github/workflows/ci.yml` (SDK drift step) |
| 26.4 | `tests/e2e/mission-flow.spec.ts` |
| 26.5 | `frontend/src/__tests__/*.test.tsx` (10+ new) |
