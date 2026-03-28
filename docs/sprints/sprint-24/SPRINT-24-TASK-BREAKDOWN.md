# Sprint 24 — Task Breakdown

**Sprint:** 24
**Phase:** 6
**Title:** CI Gate Hardening / Operational Safety
**Model:** A

**Goal:** Harden Phase 6 with measurable CI gates (benchmark regression, Playwright API smoke) and operational safety (Dependabot fix, PROJECT_TOKEN governance).

---

## Track 1: CI Gates

**24.1 — Benchmark regression gate**

Implement D-109 follow-up: checked-in JSON baseline from `tools/benchmark_api.py` output, compare step that fails CI when latency regresses beyond tolerance.

**Repo scope:** `tools/benchmark_api.py`, `.github/workflows/benchmark.yml`, `baseline/`
**Depends on:** —
**Branch:** `sprint-24/t24.1-benchmark-gate`

**Implementation:**
1. Run `benchmark_api.py` to generate baseline JSON (per-endpoint medians)
2. Create `baseline/benchmark-baseline.json` with canonical results
3. Add compare script: `tools/benchmark_compare.py` — loads baseline, compares against new run, fails if regression > threshold
4. Wire into `.github/workflows/benchmark.yml` as compare step
5. Document threshold policy: ±25% median tolerance, single run on ubuntu-latest
6. Add update instructions: operator re-runs baseline generation, commits new file

**Acceptance:**
1. Baseline file committed with documented source
2. CI compare step passes on clean run
3. Deliberate regression (artificial delay) causes CI fail
4. Threshold and update policy documented
5. Evidence: benchmark workflow run log (pass + fail)

**Verification commands:**
```bash
python tools/benchmark_api.py  # requires Vezir API on :8003
python tools/benchmark_compare.py baseline/benchmark-baseline.json new-run.json
```

**Evidence required:** CI workflow run logs (pass case + fail case)

---

**24.2 — Playwright API smoke in GitHub Actions**

Add CI job that boots Vezir API via uvicorn, runs Playwright smoke tests against it.

**Repo scope:** `.github/workflows/`, `tests/e2e/`
**Depends on:** —
**Branch:** `sprint-24/t24.2-playwright-ci`

**Implementation:**
1. Add CI job step: install Python deps, start `uvicorn agent.api.server:app` on 127.0.0.1:8003
2. Health poll loop (max 30s) until API responds
3. Install Playwright browsers
4. Run `tests/e2e/` smoke specs
5. Capture logs and artifacts on failure
6. Document failure modes: boot timeout, test flake, missing deps

**Acceptance:**
1. Job green on clean tree
2. Boot failure → deterministic CI fail with clear error
3. Smoke test failure → CI fail with test output
4. Evidence: CI workflow run log

**Verification commands:**
```bash
cd agent && uvicorn api.server:app --host 127.0.0.1 --port 8003 &
sleep 5 && npx playwright test tests/e2e/
```

**Evidence required:** CI workflow run log showing API boot + test pass

---

## Gates

**24.G1 — Mid Review Gate**

After Track 1 (24.1 + 24.2). Review: benchmark gate logic, Playwright CI stability, evidence collected. Branch-exempt.

---

## Track 2: Operational Safety

**24.3 — Dependabot moderate vulnerability remediation**

Fix the single moderate vulnerability on default branch reported by Dependabot.

**Repo scope:** `package.json`, `package-lock.json` or equivalent
**Depends on:** 24.G1
**Branch:** `sprint-24/t24.3-dependabot-fix`

**Implementation:**
1. Check `https://github.com/ahmetcagriakca/vezir/security/dependabot/1` for advisory details
2. Apply version bump or dependency replacement
3. Verify build and tests still pass
4. Verify `npm audit` (or equivalent) shows 0 moderate+ vulnerabilities

**Acceptance:**
1. Moderate vulnerability count: 0
2. CI passes after remediation
3. Advisory mapping documented in commit message
4. Evidence: before/after audit output

**Verification commands:**
```bash
npm audit --audit-level=moderate
```

**Evidence required:** Before/after audit output

---

**24.4 — PROJECT_TOKEN operational hardening**

Document and govern the PROJECT_TOKEN secret used by status-sync workflow.

**Repo scope:** `docs/shared/`, `.github/workflows/status-sync.yml`
**Depends on:** 24.G1
**Branch:** `sprint-24/t24.4-token-docs`

**Implementation:**
1. Create `docs/shared/SECRETS-CONTRACT.md`: token inventory, owner, rotation trigger, rollback procedure
2. Add inline comments in status-sync.yml documenting token requirement
3. Grep all workflows for secret usage — ensure no undocumented secrets
4. Document rotation runbook: how to generate new PAT, update secret, verify

**Acceptance:**
1. SECRETS-CONTRACT.md committed with all active secrets documented
2. Rotation path explicit (not placeholder)
3. All workflow secret references have inline documentation
4. Evidence: grep output showing all secret usages are documented

**Verification commands:**
```bash
grep -r "secrets\." .github/workflows/ --include="*.yml"
```

**Evidence required:** Secret usage grep + SECRETS-CONTRACT.md content

---

**24.G2 — Final Review Gate**

Full evidence: pytest + vitest + tsc + ruff + benchmark + playwright CI + audit output; sprint artifact index. Branch-exempt.

**24.RETRO — Retrospective**

Answer: Is benchmark gate noisy or stable? Is Playwright CI reliable? What to prioritize in S25 (OpenAPI SDK, frontend tests, archive)?

**24.CLOSURE — Sprint Closure**

All implementation task branches merged to `main`; evidence under `docs/sprints/sprint-24/artifacts/`; GPT operator sets `closure_status=closed`.

---

## Carry-Forward (explicit defer)

| Item | Reason | Target |
|------|--------|--------|
| Archive --execute | Operator decision pending | S25 |
| Frontend Vitest component tests | Separate capability track | S25 |
| OpenAPI → TypeScript SDK | Separate scope | S25+ |
| Backend restructure, Docker, Live E2E | Phase 6 roadmap | Unassigned |
| Multi-user auth, Jaeger | Phase 6 roadmap | Unassigned |

---

## Output Files

| Task | Output |
|------|--------|
| 24.1 | `baseline/benchmark-baseline.json`, `tools/benchmark_compare.py`, `.github/workflows/benchmark.yml` |
| 24.2 | `.github/workflows/` (CI job), `tests/e2e/` |
| 24.3 | `package.json` / `package-lock.json` (version bump) |
| 24.4 | `docs/shared/SECRETS-CONTRACT.md`, workflow inline docs |
