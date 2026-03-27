# Sprint 12 — Phase 5D: Polish + Phase Closure

**implementation_status:** not_started
**closure_status:** not_started
**Owner:** AKCA (operator), Claude Code (implementation), GPT (review)
**Goal:** Achieve Phase 5 scoreboard 15/15 and close Phase 5.

---

## Scope

Phase 5D is the final sprint of Phase 5 (Mission Control). It covers:
- API documentation (OpenAPI spec export)
- E2E test suite (12+ API-level scenarios via httpx + pytest)
- Accessibility audit (Lighthouse > 90)
- Performance benchmark (baseline, no regression threshold)
- Operator guide (operational runbook)
- Legacy dashboard resolution (deprecation per D-097)
- Phase 5 scoreboard verification (15/15 criteria)
- Phase 5 closure report

**Out of scope:** Browser-level E2E (Phase 6), approval model changes (Phase 6), legacy dashboard code removal (Sprint 13), folder migration of Sprint 7-11 material (Sprint 13).

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Sprint 11 closure_status=closed | ✅ | Operator sign-off 2026-03-26. Must be verified in `docs/ai/STATE.md`. |
| Process Patch v4 applied | ✅ | PROCESS-GATES.md v4 (22 sections), task template updated, closure-check.sh updated (P-05 auto test count + D-001→D-101 check). |
| OD-11→OD-16 frozen | ✅ | D-097→D-101 written to DECISIONS.md, 0 open decisions |
| D-021→D-058 in DECISIONS.md | ✅ | 38 decisions extracted, 101 total entries (D-001→D-101), gap check clean |
| Mission Control API running (:8003) | Required | Backend must be live for E2E, benchmark, OpenAPI export |
| React dev server running (:3000) | Required | Frontend must be live for Lighthouse audit |

## Blocking Risks

| Risk | Mitigation |
|------|------------|
| Decision debt extraction takes longer than expected | Time-box to 2 hours. If incomplete, list remaining gaps explicitly and mark as blocking. |
| Lighthouse < 90 after fixes | Document score and gap. If structural (e.g. third-party component), record exception with D-XXX. |
| E2E flaky tests | Isolate flaky tests. Minimum 12 stable scenarios required. Flaky tests do not count toward 12. |
| STATE.md not aligned with Sprint 11 closure | Fix STATE.md before any other kickoff work. |

## Acceptance Criteria

1. Phase 5 scoreboard 15/15 — each criterion with evidence reference
2. All tests passing (backend + frontend + E2E) — counts from raw script output
3. Decision debt zero: D-001→D-101 all in DECISIONS.md, status frozen (D-020 normalized from Active to frozen)
4. OpenAPI spec exported and complete
5. Operator guide covers all operational scenarios
6. Legacy dashboard status matches D-097

## Exit Criteria

1. GPT final review PASS (0 blocking)
2. Claude assessment PASS (0 blocking)
3. Retrospective complete with at least one actionable output
4. Closure script: ELIGIBLE FOR CLOSURE REVIEW
5. Phase 5 closure report produced
6. Operator sign-off: closure_status=closed

## Files

| File | Purpose | Status |
|------|---------|--------|
| SPRINT-12-README.md | Sprint entry point (this file) | Active |
| SPRINT-12-TASK-BREAKDOWN.md | Plan, task table, evidence checklist, verification commands | Active |
| SPRINT-12-KICKOFF-GATE.md | Gate checklist — all prerequisites for implementation start | Active |
| SPRINT-12-MID-REVIEW.md | Mid-review report | Created after first-half tasks |
| SPRINT-12-FINAL-REVIEW.md | Final review report | Created after all tasks |
| SPRINT-12-RETROSPECTIVE.md | Sprint retrospective (mandatory) | Created before final gate |
| SPRINT-12-CLOSURE-SUMMARY.md | Closure summary | Created before operator sign-off |
| PHASE-5-CLOSURE-REPORT.md (→ docs/phase-reports/) | Phase 5 closure report (Sprint 12 only) | Created at closure |

## Evidence Location

Raw evidence outputs: `evidence/sprint-12/`

Evidence is NOT stored under `docs/`. Narrative docs live in `docs/sprints/sprint-12/`. Raw outputs live in `evidence/sprint-12/`. Never mixed.

## Expected Evidence (Closure Packet — 20 mandatory files)

| # | File | Source Task |
|---|------|------------|
| 1 | pytest-output.txt | 12.10 |
| 2 | vitest-output.txt | 12.10 |
| 3 | tsc-output.txt | 12.10 |
| 4 | lint-output.txt | 12.10 |
| 5 | build-output.txt | 12.10 |
| 6 | validator-output.txt | 12.10 |
| 7 | grep-evidence.txt | 12.10 |
| 8 | live-checks.txt | 12.10 |
| 9 | e2e-output.txt | 12.3 / 12.10 |
| 10 | lighthouse.txt | 12.4 |
| 11 | sse-evidence.txt | 12.10 (Sprint 10+ mandatory) |
| 12 | mutation-drill.txt | 12.10 (Sprint 11+ mandatory) |
| 13 | closure-check-output.txt | 12.10 |
| 14 | contract-evidence.txt | 12.10 |
| 15 | benchmark.txt | 12.5 |
| 16 | phase5-scoreboard.txt | 12.8 |
| 17 | phase5-scoreboard-final.txt | 12.10 |
| 18 | decision-debt-check.txt | kickoff |
| 19 | review-summary.md | 12.FINAL |
| 20 | file-manifest.txt | 12.CLOSURE |

## Verification Commands

```bash
# Full test suite
python -m pytest tests/ -v
npx vitest run
python -m pytest tests/e2e/ -v

# Test counts (auto-parsed, P-05)
python -m pytest tests/ --co -q 2>/dev/null | tail -1
npx vitest list 2>/dev/null | wc -l

# TypeScript / lint / build
npx tsc --noEmit
npx eslint src/
npm run build

# OpenAPI
curl -s http://localhost:8003/openapi.json | python -m json.tool | head -5

# Lighthouse
npx lighthouse http://localhost:3000 --output json --output-path evidence/sprint-12/lighthouse.txt

# SSE evidence
curl -N http://localhost:8003/api/v1/events/stream --max-time 5

# Closure script
bash tools/sprint-closure-check.sh 12
```

## Produced Artifacts

| Artifact | Location | Promotion Note |
|----------|----------|----------------|
| OpenAPI spec | docs/api/openapi.json | Sprint-local |
| Operator guide | docs/OPERATOR-GUIDE.md | Promoted to shared: cross-sprint, governance-relevant, referenced by Sprint 12+. Owner: AKCA. Source: Sprint 12. Sunset: when replaced by dedicated ops platform. |
| Phase 5 closure report | docs/sprints/sprint-12/PHASE-5-CLOSURE-REPORT.md (→ docs/phase-reports/) | Sprint-local |
| E2E test suite | tests/e2e/ | Permanent test infrastructure |

## Open Decisions (Kickoff Blockers)

These must all be frozen **before the kickoff gate closes**. They are not sprint tasks.

| ID | Topic | Proposed Resolution | Status |
|----|-------|---------------------|--------|
| OD-11 | Legacy dashboard | Retire (D-097) | ✅ FROZEN |
| OD-12 | E2E framework | httpx + pytest (D-098) | ✅ FROZEN |
| OD-14 | Approval sunset | Phase 6 scope (D-099) | ✅ FROZEN |
| OD-15 | OpenAPI generation | FastAPI auto-gen (D-100) | ✅ FROZEN |
| OD-16 | D-068 amendment | SSE = MC frontend only (D-101) | ✅ FROZEN |

## Decision Status Vocabulary

Decisions use exactly four statuses: `proposed | accepted | frozen | deprecated`.

D-020 status normalized from `Active` to `Frozen` during kickoff. All decisions now use standard vocabulary.

## Closure Prerequisites

1. Phase 5 scoreboard 15/15 (evidence in `evidence/sprint-12/phase5-scoreboard-final.txt`)
2. All tests passing — counts from raw output (P-05 rule)
3. Decision debt zero (D-001→D-101)
4. GPT final review PASS
5. Claude assessment PASS
6. Retrospective complete with actionable output
7. Closure script: ELIGIBLE FOR CLOSURE REVIEW
8. Operator sign-off (closure_status=closed)

---

## Repo Placement

This file and all Sprint 12 narrative docs live at `docs/sprints/sprint-12/` in the repo. Block E verified: `ls docs/sprints/sprint-12/` confirms physical placement.
