# Sprint 12 — Task Breakdown (Phase 5D: Polish + Phase Closure)

**Date:** 2026-03-26
**Phase:** 5D — Final sprint of Phase 5
**Goal:** Achieve Phase 5 scoreboard 15/15, close Phase 5
**implementation_status:** not_started
**closure_status:** not_started

---

## Pre-Implementation Kickoff Resolution

The following items **must be resolved before the kickoff gate closes**. They are not sprint tasks — they are kickoff prerequisites. No implementation task begins until all are done.

### Open Decisions (5 — all must freeze before gate closes)

| ID | Topic | Proposed Resolution | Decision ID | Owner |
|----|-------|---------------------|-------------|-------|
| OD-11 | Legacy health dashboard (:8002) | Retire. Mission Control replaces it. Deprecation banner + startup warning. Removal in Sprint 13. | D-097 | Operator confirm |
| OD-12 | E2E test framework | `httpx` + `pytest` for API-level E2E. No browser E2E in Phase 5. Deferred to Phase 6. | D-098 | Operator confirm |
| OD-14 | Approval sunset — Phase 2 scope | Approval model changes are Phase 6 scope. Phase 5 keeps current preapproval model. | D-099 | Operator confirm |
| OD-15 | OpenAPI spec generation | Auto-generate from FastAPI (built-in). Export to `docs/api/openapi.json`. | D-100 | Operator confirm |
| OD-16 / D-068 | D-068 amendment | SSE transport applies to Mission Control frontend only, not Bridge contract. | D-101 (amends D-068) | Operator confirm |

### Decision Debt (strict pre-kickoff hygiene — B3)

All items below must complete before any implementation task starts. If implementation begins before this section is fully resolved, the sprint is off-baseline.

| Item | Status | Evidence |
|------|--------|----------|
| D-021→D-058 extracted into DECISIONS.md (38 decisions) | ⬜ | `grep -c "^## D-" docs/ai/DECISIONS.md` before/after |
| D-059→D-080 gap check, fix missing entries | ⬜ | Diff or count |
| D-093/094/095 frozen (status: `proposed` → `frozen`) | ⬜ | `grep "D-09[345]" docs/ai/DECISIONS.md` shows `Frozen` |
| D-089 text fixed: "Origin header check enforced server-side; SameSite is browser-context only" | ⬜ | `grep -A3 "D-089" docs/ai/DECISIONS.md` |
| Decision debt check output saved | ⬜ | `evidence/sprint-12/decision-debt-check.txt` |

**Decision status vocabulary:** `proposed | accepted | frozen | deprecated`. No other values. D-020 uses `Active` — this should be normalized to `frozen` or `accepted` during debt cleanup.

### Process Patch v4 Application (concrete artifacts — B2)

| Artifact | Repo Path | Status |
|----------|-----------|--------|
| Project instructions v3+ | `docs/shared/PROJECT_INSTRUCTIONS_v3_EN.md` | ⬜ |
| Process gates with P-01→P-10 | `docs/shared/PROCESS-GATES_EN.md` | ⬜ |
| Closure script with auto test count + Sprint 12 paths | `tools/sprint-closure-check.sh` | ⬜ |
| Sprint template with mandatory tasks | Verified by this task breakdown | ✅ |

### Kickoff Gate Closure Sequence

1. Verify Sprint 11 closed in `docs/ai/STATE.md` (fix if needed)
2. Operator confirms OD-11→OD-16 proposed resolutions (or provides alternatives)
3. D-097→D-101 written to DECISIONS.md, status=frozen
4. D-021→D-058 extracted, D-059→D-080 gaps fixed, D-093/094/095 frozen, D-089 fixed
5. Process Patch v4 artifacts applied to repo
6. Sprint folder `docs/sprints/sprint-12/` + evidence folder `evidence/sprint-12/` created
7. Operator sends **kickoff packet** to GPT: README + KICKOFF-GATE + TASK-BREAKDOWN + DECISIONS delta
8. GPT pre-sprint review PASS
9. Operator authorizes implementation start

**Until step 9 completes: implementation_status remains not_started.**

---

## Task Table

| Task | Description | Side | Owner | Dependency | Size |
|------|-------------|------|-------|------------|------|
| 12.1 | API documentation (OpenAPI spec) | Backend | Claude Code | Kickoff gate closed | M |
| 12.2 | E2E framework setup + config | Test | Claude Code | Kickoff gate closed | M |
| 12.3 | E2E test scenarios (12+ scenarios) | Test | Claude Code | 12.2 | L |
| 12.MID-REPORT | Mid-review report draft | Report | Claude Code | 12.1→12.3 | S |
| 12.MID | GPT mid-review | Review | GPT | 12.MID-REPORT | — |
| 12.CLAUDE-MID | Claude mid-assessment | Review | Claude | 12.MID-REPORT | — |
| 12.4 | Accessibility audit + Lighthouse > 90 | Frontend | Claude Code | 12.MID + 12.CLAUDE-MID | M |
| 12.5 | Performance benchmark | Backend | Claude Code | 12.MID + 12.CLAUDE-MID | S |
| 12.6 | User / operator guide | Docs | Claude Code | 12.1 | M |
| 12.7 | Legacy dashboard resolution | Frontend | Claude Code | Kickoff gate (D-097) | S |
| 12.8 | Phase 5 scoreboard verification | All | Claude Code | 12.1→12.7 | M |
| 12.9 | Scoreboard gap fix | All | Claude Code | 12.8 (if gaps found) | M |
| 12.10 | Scoreboard re-verification + full test run | All | Claude Code | 12.9 | S |
| 12.REPORT | Final review report draft | Report | Claude Code | 12.10 | S |
| 12.RETRO | Sprint retrospective draft | Retro | Claude Code | 12.REPORT | S |
| 12.FINAL | GPT final review + Claude assessment | Review | GPT + Claude | 12.REPORT + 12.RETRO | — |
| 12.CLOSURE | Closure summary + Phase 5 closure report | Closure | Claude Code | 12.FINAL PASS | S |

**Total implementation tasks:** 10 (12.1→12.10)
**Total mandatory process tasks:** 7 (MID-REPORT, MID, CLAUDE-MID, REPORT, RETRO, FINAL, CLOSURE)

---

## First Half Tasks (12.1→12.3)

### Task 12.1 — API Documentation (OpenAPI Spec)

**Goal:** Complete, accurate API documentation for Mission Control API.

**Subtasks:**
1. Verify FastAPI auto-generates OpenAPI schema at `/docs` and `/openapi.json`
2. Export OpenAPI JSON to `docs/api/openapi.json`
3. Verify all endpoints documented: roles, tasks, health, signals, approvals, SSE
4. Add response examples for each endpoint
5. Add error response documentation (4xx/5xx)

**Evidence:**
- `curl http://localhost:8003/openapi.json | python -m json.tool | head -50` → valid JSON
- Endpoint count: `jq '.paths | keys | length' docs/api/openapi.json`
- Schema validation: `python -c "import json; d=json.load(open('docs/api/openapi.json')); print('openapi:', d['openapi'], 'paths:', len(d['paths']))"`

**Acceptance:** OpenAPI spec exported, all endpoints documented, response examples present.

---

### Task 12.2 — E2E Framework Setup + Config

**Goal:** E2E test infrastructure ready for scenario execution.

**Depends on:** D-098 (httpx + pytest)

**Subtasks:**
1. Create `tests/e2e/` directory
2. Create `tests/e2e/conftest.py` with fixtures: running backend, test client, seed data
3. Create `tests/e2e/test_smoke.py` with basic health + role listing smoke test
4. Verify E2E tests run independently from unit tests: `pytest tests/e2e/ -v`

**Evidence:**
- `pytest tests/e2e/ -v` → PASS (smoke tests)
- `find tests/e2e/ -name "*.py" | wc -l` → at least 2 files

**Acceptance:** E2E framework operational, smoke tests passing, isolated from unit tests.

---

### Task 12.3 — E2E Test Scenarios (12+ scenarios)

**Goal:** Comprehensive E2E coverage of Mission Control critical paths.

**Minimum 12 scenarios:**

| # | Scenario | Covers |
|---|----------|--------|
| 1 | Health endpoint returns ok | API availability |
| 2 | List all roles → 9 governed roles present | Role governance |
| 3 | Get single role detail | Role API |
| 4 | List tasks → returns array | Task API |
| 5 | Submit signal → accepted | Signal creation |
| 6 | SSE stream connects and receives events | Real-time transport |
| 7 | Approval request → pending lifecycle | Approval flow |
| 8 | Approval accept → status transition | Approval mutation |
| 9 | Approval reject → status transition | Approval mutation |
| 10 | Invalid signal → 422 | Input validation |
| 11 | Unknown role → 404 | Error handling |
| 12 | Concurrent signal submission | Concurrency safety |

**Evidence:**
- `pytest tests/e2e/ -v` → 12+ PASS, 0 FAIL
- `pytest tests/e2e/ --co -q | tail -1` → collected count ≥ 12
- Raw output saved to `evidence/sprint-12/e2e-output.txt`

**Acceptance:** 12+ E2E scenarios passing. All critical paths covered.

---

## Mid-Review Gate

### Task 12.MID-REPORT — Mid-Review Report Draft

**Trigger:** Tasks 12.1→12.3 complete.
**Output:** `docs/sprints/sprint-12/SPRINT-12-MID-REVIEW.md`
**Content:** Task status table, evidence summary, decision compliance check, drift notes.

### Task 12.MID — GPT Mid-Review

**Input:** SPRINT-12-MID-REVIEW.md
**Checks:** Contract drift, decision compliance, evidence completeness, E2E coverage.
**Verdict:** PASS / FAIL with findings.

### Task 12.CLAUDE-MID — Claude Mid-Assessment

**Runs parallel with 12.MID.**
**Checks:** Living document up to date, evidence checklist progress, decision compliance (D-097→D-101 honored), folder structure correct.
**Verdict:** PASS / FAIL with findings.

**Gate rule:** Both 12.MID and 12.CLAUDE-MID must PASS before second-half tasks begin.

---

## Second Half Tasks (12.4→12.10)

### Task 12.4 — Accessibility Audit + Lighthouse > 90

**Goal:** Mission Control React UI meets accessibility baseline.

**Subtasks:**
1. Run Lighthouse audit on Mission Control pages (localhost:3000)
2. Fix critical accessibility issues (ARIA labels, color contrast, keyboard navigation)
3. Re-run Lighthouse → score > 90
4. Save report to `evidence/sprint-12/lighthouse.txt`

**Evidence:** `evidence/sprint-12/lighthouse.txt` with accessibility score > 90.

**Acceptance:** Lighthouse accessibility > 90, report saved.

---

### Task 12.5 — Performance Benchmark

**Goal:** Baseline performance numbers for Mission Control API.

**Subtasks:**
1. Benchmark key endpoints: health, roles list, tasks list, signal submit
2. Record: response time p50/p95/p99, requests/sec under load
3. Save results to `evidence/sprint-12/benchmark.txt`

**Evidence:** `evidence/sprint-12/benchmark.txt` with tabular results, all endpoints < 500ms at p95.

**Acceptance:** Benchmark complete, results documented.

---

### Task 12.6 — User / Operator Guide

**Goal:** Operational documentation for running and managing Mission Control.

**Subtasks:**
1. Create `docs/OPERATOR-GUIDE.md`
2. Sections: installation, startup, port map, role governance, signal flow, approval flow, SSE monitoring, troubleshooting
3. Include all 4 ports (8001 WMCP, 8002 Legacy, 8003 MC API, 3000 React)
4. Include common operator tasks: restart, health check, log locations

**Promotion justification:** OPERATOR-GUIDE.md lives at `docs/` (not sprint-scoped) because it is a permanent operational document, not sprint-local. This follows the promotion rule: governance-relevant, cross-sprint, referenced by future phases.

**Evidence:** File exists, `grep "^##" docs/OPERATOR-GUIDE.md | wc -l` → ≥ 8 sections.

**Acceptance:** Guide covers all operational scenarios. Readable by non-developer operator.

---

### Task 12.7 — Legacy Dashboard Resolution

**Goal:** Implement D-097 decision.

**If D-097 = retire (proposed):**
1. Add deprecation banner to legacy dashboard UI
2. Add startup log warning: "Legacy dashboard (:8002) is deprecated. Use Mission Control (:8003 + :3000)."
3. Do NOT remove code in Sprint 12 (removal is Sprint 13 scope)
4. Update OPERATOR-GUIDE.md with deprecation notice

**Once D-097 is frozen, the waiver branch is dead.** This task executes the frozen decision only. No branching language after freeze.

**Evidence:** Deprecation banner visible at localhost:8002, startup log contains warning, OPERATOR-GUIDE.md updated.

**Acceptance:** Legacy dashboard status matches D-097 frozen decision exactly.

---

### Task 12.8 — Phase 5 Scoreboard Verification

**Goal:** Verify current state of all 15 Phase 5 closure criteria. Report gaps.

| # | Criterion | Source | Verification |
|---|-----------|--------|-------------|
| 1 | 9 governed roles operational | Sprint 8 | `curl localhost:8003/api/roles \| jq length` → 9 |
| 2 | Role health monitoring live | Sprint 9 | `curl localhost:8003/api/health` → ok |
| 3 | SSE real-time transport working | Sprint 9 | SSE connect test → save to `evidence/sprint-12/sse-evidence.txt` |
| 4 | Signal → Approval → Execution pipeline E2E | Sprint 10-11 | E2E test suite |
| 5 | Atomic signal artifact bridge | Sprint 11 | ownership-grep evidence |
| 6 | Contract-first tests passing | Sprint 11 | `pytest tests/ -k contract -v` |
| 7 | Operator drill 5/5 | Sprint 11 | Sprint 11 evidence (reference) |
| 8 | E2E tests 12+ scenarios | Sprint 12 (12.3) | `pytest tests/e2e/ --co -q` |
| 9 | Accessibility Lighthouse > 90 | Sprint 12 (12.4) | lighthouse.txt |
| 10 | Performance benchmark documented | Sprint 12 (12.5) | benchmark.txt |
| 11 | API documentation complete | Sprint 12 (12.1) | openapi.json exists + endpoint count |
| 12 | Operator guide complete | Sprint 12 (12.6) | OPERATOR-GUIDE.md exists |
| 13 | Legacy dashboard resolved | Sprint 12 (12.7) | D-097 implementation verified |
| 14 | Decision debt zero (D-001→D-101) | Sprint 12 (kickoff) | `grep "Status: proposed" DECISIONS.md` → 0 |
| 15 | All tests passing (backend + frontend + E2E) | Sprint 12 | Full test run, auto-counted |

**Output:** `evidence/sprint-12/phase5-scoreboard.txt` — each criterion: PASS / FAIL / PARTIAL with evidence reference.

**Acceptance:** Scoreboard produced. Every criterion has a verdict.

---

### Task 12.9 — Scoreboard Gap Fix

**Trigger:** 12.8 found one or more gaps.
**If 12.8 = 15/15 PASS:** This task is skipped (marked N/A).

**For each gap:** Identify root cause → implement fix → record in Implementation Notes.

**Acceptance:** All gaps from 12.8 addressed. Each fix has evidence.

---

### Task 12.10 — Scoreboard Re-Verification + Full Test Run

**Trigger:** 12.9 complete (or 12.8 was already 15/15).

**Subtasks:**
1. Re-run full test suite: `pytest tests/ -v` + `npx vitest run` + `pytest tests/e2e/ -v`
2. Run `npx tsc --noEmit` → save to `evidence/sprint-12/tsc-output.txt`
3. Run linter → save to `evidence/sprint-12/lint-output.txt`
4. Run build → save to `evidence/sprint-12/build-output.txt`
5. Run validator → save to `evidence/sprint-12/validator-output.txt`
6. Run grep evidence checks → save to `evidence/sprint-12/grep-evidence.txt`
7. Run live endpoint checks → save to `evidence/sprint-12/live-checks.txt`
8. Verify SSE transport → save to `evidence/sprint-12/sse-evidence.txt`
9. Auto-count test totals from raw script output (P-05 rule)
10. Re-run scoreboard verification commands from 12.8
11. Run closure script: `bash tools/sprint-closure-check.sh 12`
12. Produce final `evidence/sprint-12/phase5-scoreboard-final.txt`

**Evidence:** All 19 mandatory files produced in `evidence/sprint-12/`.

**Acceptance:** Phase 5 scoreboard 15/15 confirmed. All test counts from raw output. Closure script: ELIGIBLE FOR CLOSURE REVIEW.

---

## Closure Tasks

### Task 12.REPORT — Final Review Report Draft

**Trigger:** Task 12.10 complete with 15/15.
**Output:** `docs/sprints/sprint-12/SPRINT-12-FINAL-REVIEW.md`
**Content:** Full task results, evidence summary, scoreboard 15/15, decision registry, test counts from raw output.

### Task 12.RETRO — Sprint Retrospective

**Output:** `docs/sprints/sprint-12/SPRINT-12-RETROSPECTIVE.md`
**Must produce at least one of:** new D-XXX, task patch, process gate patch, script patch, scoreboard update.
**Mandatory content:** What worked, what broke, drift, root cause, next-sprint action, stop rules.

### Task 12.FINAL — GPT Final Review + Claude Assessment

**Input:** SPRINT-12-FINAL-REVIEW.md + SPRINT-12-RETROSPECTIVE.md + all evidence files
**GPT:** Full review, 0 blocking required.
**Claude:** Architecture + governance + Phase 5 closure assessment.
**Both must PASS.**

### Task 12.CLOSURE — Closure Summary + Phase 5 Closure Report

**Output:**
- `docs/sprints/sprint-12/SPRINT-12-CLOSURE-SUMMARY.md`
- `docs/sprints/sprint-12/SPRINT-12-PHASE-CLOSURE.md`

**Phase 5 Closure Report content:** Phase 5 goal vs actual, scoreboard 15/15 evidence, Sprint 8→12 summary, decision registry D-059→D-101, carried items to Phase 6, architecture compliance statement.

---

## Evidence Checklist (Closure Packet Standard — 20 mandatory files)

All evidence goes to `evidence/sprint-12/`. Reports are not evidence — they reference evidence.

| # | Evidence File | Task | Mandatory | Baseline Rule |
|---|---------------|------|-----------|---------------|
| 1 | pytest-output.txt | 12.10 | ✅ | All sprints |
| 2 | vitest-output.txt | 12.10 | ✅ | All sprints |
| 3 | tsc-output.txt | 12.10 | ✅ | All sprints |
| 4 | lint-output.txt | 12.10 | ✅ | All sprints |
| 5 | build-output.txt | 12.10 | ✅ | All sprints |
| 6 | validator-output.txt | 12.10 | ✅ | All sprints |
| 7 | grep-evidence.txt | 12.10 | ✅ | All sprints |
| 8 | live-checks.txt | 12.10 | ✅ | All sprints |
| 9 | sse-evidence.txt | 12.8/12.10 | ✅ | Sprint 10+ |
| 10 | e2e-output.txt | 12.3/12.10 | ✅ | Sprint 12+ |
| 11 | lighthouse.txt | 12.4 | ✅ | Sprint 12+ |
| 12 | closure-check-output.txt | 12.10 | ✅ | All sprints |
| 13 | contract-evidence.txt | 12.10 | ✅ | All sprints |
| 14 | benchmark.txt | 12.5 | ✅ | Sprint 12 (new) |
| 15 | phase5-scoreboard.txt | 12.8 | ✅ | Sprint 12 (new) |
| 16 | phase5-scoreboard-final.txt | 12.10 | ✅ | Sprint 12 (new) |
| 17 | decision-debt-check.txt | kickoff | ✅ | Sprint 12 (new) |
| 18 | review-summary.md | 12.FINAL | ✅ | All sprints |
| 19 | file-manifest.txt | 12.CLOSURE | ✅ | All sprints |
| 20 | mutation-drill.txt | 12.10 | ✅ | Sprint 11+ — copied from Sprint 11 evidence (not re-executed) |

**Mutation-drill note:** Sprint 12 is not a mutation sprint (Phase 5D = polish). `mutation-drill.txt` is included per Sprint 11+ baseline rule but is a copy/reference of Sprint 11 evidence, not a re-execution. Phase 5 scoreboard criterion #7 references the original drill results.

**SSE evidence:** Required per Sprint 10+ rule. Produced during scoreboard verification (12.8, criterion #3). Saved to `sse-evidence.txt`.

**Rule:** If any mandatory file is missing at closure, closure script must exit non-zero. Missing file = `NO EVIDENCE` in output.

---

## Verification Commands

```bash
# Decision debt check
grep -c "^## D-" docs/ai/DECISIONS.md
grep "Status: proposed" docs/ai/DECISIONS.md

# Folder structure
find docs/sprints/sprint-12/ -type f
find evidence/sprint-12/ -type f

# Test counts (auto from script — P-05)
python -m pytest tests/ --co -q 2>/dev/null | tail -1
npx vitest list 2>/dev/null | wc -l
python -m pytest tests/e2e/ --co -q 2>/dev/null | tail -1

# E2E run
pytest tests/e2e/ -v

# TypeScript check
npx tsc --noEmit

# Lighthouse
# (run via Chrome DevTools or npx lighthouse)

# OpenAPI
curl -s http://localhost:8003/openapi.json | python -m json.tool | head -5

# SSE evidence
curl -s -N http://localhost:8003/api/sse --max-time 5

# Phase 5 scoreboard
cat evidence/sprint-12/phase5-scoreboard-final.txt

# Closure script
bash tools/sprint-closure-check.sh 12

# Sprint 11 closure verification
grep -A2 "Sprint 11" docs/ai/STATE.md
```

---

## Implementation Notes

_Updated during sprint. Drift recorded same day._

| Task | Planned | Implemented | Why Different |
|------|---------|-------------|---------------|
| 12.1 | — | — | — |
| 12.2 | — | — | — |
| 12.3 | — | — | — |
| 12.4 | — | — | — |
| 12.5 | — | — | — |
| 12.6 | — | — | — |
| 12.7 | — | — | — |
| 12.8 | — | — | — |
| 12.9 | — | — | — |
| 12.10 | — | — | — |

---

## File Manifest

_Updated during sprint._

| File | Action | Task | Status |
|------|--------|------|--------|
| docs/sprints/sprint-12/README.md | Create | kickoff | — |
| docs/sprints/sprint-12/SPRINT-12-KICKOFF-GATE.md | Create | kickoff | — |
| docs/sprints/sprint-12/SPRINT-12-TASK-BREAKDOWN.md | Create | kickoff | — |
| docs/ai/DECISIONS.md | Modify (38+ entries + 5 new + fixes) | kickoff | — |
| docs/shared/PROJECT_INSTRUCTIONS_v3_EN.md | Create/Update | kickoff (P.Patch v4) | — |
| docs/shared/PROCESS-GATES_EN.md | Create/Update | kickoff (P.Patch v4) | — |
| tools/sprint-closure-check.sh | Modify | kickoff (P.Patch v4) | — |
| docs/api/openapi.json | Create | 12.1 | — |
| tests/e2e/conftest.py | Create | 12.2 | — |
| tests/e2e/test_smoke.py | Create | 12.2 | — |
| tests/e2e/test_scenarios.py | Create | 12.3 | — |
| docs/OPERATOR-GUIDE.md | Create | 12.6 | — |
| evidence/sprint-12/ | Create directory | kickoff | — |

---

## Next Step

**Produced:** SPRINT-12-TASK-BREAKDOWN.md (v3 — all GPT review blockers addressed)
**Next actor:** Operator
**Action:** Confirm OD-11→OD-16 proposed resolutions. Then kickoff resolution sequence begins: decisions → debt → Process Patch → folder setup → GPT packet review.
**Blocking:** Yes — no implementation before all kickoff prerequisites met AND GPT pre-sprint review PASS.
