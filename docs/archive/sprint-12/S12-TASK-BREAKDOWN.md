# Sprint 12 — Task Breakdown (Phase 5D: Polish + Phase Closure)

**Repo path:** `docs/sprints/sprint-12/SPRINT-12-TASK-BREAKDOWN.md`
**Date:** 2026-03-26 (v3 — post GPT reviews)
**Phase:** 5D — Final sprint of Phase 5
**Goal:** Phase 5 scoreboard 15/15, close Phase 5
**implementation_status:** not_started
**closure_status:** not_started
**Owner:** AKCA (operator)

---

## Pre-Implementation (All Done)

All kickoff prerequisites resolved: OD-11→OD-16 frozen (D-097→D-101), decision debt cleared (101 entries, D-093/094/095 stubs), Process Patch v4 applied (4 artifacts), Sprint 11 repo-verified closed, folders created, closure script updated.

---

## Task Table

| Task | Description | Side | Owner | Dependency | Size |
|------|-------------|------|-------|------------|------|
| 12.1 | API documentation (OpenAPI spec) | Backend | Claude Code | Kickoff gate | M |
| 12.2 | E2E framework setup (httpx+pytest, D-098) | Test | Claude Code | Kickoff gate | M |
| 12.3 | E2E test scenarios (12+) | Test | Claude Code | 12.2 | L |
| 12.MID-REPORT | Mid-review report draft | Report | Claude Code | 12.1→12.3 | S |
| 12.MID | GPT mid-review | Review | GPT | 12.MID-REPORT | — |
| 12.CLAUDE-MID | Claude mid-assessment | Review | Claude | 12.MID-REPORT | — |
| 12.4 | Accessibility + Lighthouse > 90 | Frontend | Claude Code | Mid gate | M |
| 12.5 | Performance benchmark | Backend | Claude Code | Mid gate | S |
| 12.6 | User / operator guide | Docs | Claude Code | 12.1 | M |
| 12.7 | Legacy dashboard resolution (D-097) | Frontend | Claude Code | Kickoff gate | S |
| 12.8 | Phase 5 scoreboard verification | All | Claude Code | 12.1→12.7 | M |
| 12.9 | Scoreboard gap fix | All | Claude Code | 12.8 | M |
| 12.10 | Scoreboard re-verification | All | Claude Code | 12.9 | S |
| 12.REPORT | Final review report | Report | Claude Code | 12.10 | S |
| 12.RETRO | Sprint retrospective | Retro | Claude Code | 12.REPORT | S |
| 12.FINAL | GPT final + Claude assessment | Review | GPT+Claude | 12.REPORT+12.RETRO | — |
| 12.CLOSURE | Closure + Phase 5 closure report | Closure | Claude Code | 12.FINAL PASS | S |

**10 implementation + 7 process = 17 tasks**

---

## Phase 5 Scoreboard (15 criteria)

| # | Criterion | Source | Task |
|---|-----------|--------|------|
| 1 | 9 governed roles operational | Sprint 8 | verify 12.8 |
| 2 | Role health monitoring live | Sprint 9 | verify 12.8 |
| 3 | SSE real-time transport | Sprint 9 | verify 12.8 |
| 4 | Signal→Approval→Execution E2E | Sprint 10-11 | verify 12.8 |
| 5 | Atomic signal artifact bridge | Sprint 11 | verify 12.8 |
| 6 | Contract-first tests passing | Sprint 11 | verify 12.8 |
| 7 | Operator drill 5/5 | Sprint 11 | verify 12.8 |
| 8 | E2E tests 12+ scenarios | Sprint 12 | 12.3 |
| 9 | Accessibility Lighthouse > 90 | Sprint 12 | 12.4 |
| 10 | Performance benchmark | Sprint 12 | 12.5 |
| 11 | API documentation | Sprint 12 | 12.1 |
| 12 | Operator guide | Sprint 12 | 12.6 |
| 13 | Legacy dashboard resolved | Sprint 12 | 12.7 |
| 14 | Decision debt zero (D-001→D-101) | Sprint 12 | kickoff |
| 15 | All tests passing | Sprint 12 | 12.10 |

---

## Evidence Checklist (20 mandatory)

All at `evidence/sprint-12/`.

| # | File | Task |
|---|------|------|
| 1 | pytest-output.txt | 12.10 |
| 2 | vitest-output.txt | 12.10 |
| 3 | tsc-output.txt | 12.10 |
| 4 | lint-output.txt | 12.10 |
| 5 | build-output.txt | 12.10 |
| 6 | validator-output.txt | 12.10 |
| 7 | grep-evidence.txt | 12.10 |
| 8 | live-checks.txt | 12.10 |
| 9 | e2e-output.txt | 12.3/12.10 |
| 10 | lighthouse.txt | 12.4 |
| 11 | sse-evidence.txt | 12.10 |
| 12 | mutation-drill.txt | 12.10 |
| 13 | closure-check-output.txt | 12.10 |
| 14 | contract-evidence.txt | 12.10 |
| 15 | benchmark.txt | 12.5 |
| 16 | phase5-scoreboard.txt | 12.8 |
| 17 | phase5-scoreboard-final.txt | 12.10 |
| 18 | decision-debt-check.txt | kickoff |
| 19 | review-summary.md | 12.FINAL |
| 20 | file-manifest.txt | 12.CLOSURE |

---

## Risk Register

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Lighthouse < 90 | Iterative fixes. 85-90 = documented exception to Sprint 13. |
| R2 | E2E reveals backend bugs | Fix in 12.9. Mid-gate catches early. |
| R3 | Decision debt errors | Verified with grep + evidence file. |
| R4 | SSE not reproducible | E2E scenario #6 covers. Carry-forward from Sprint 11 if needed. |

---

## Verification Commands

```bash
grep -c "^## D-" docs/ai/DECISIONS.md                    # 101
grep "Status: proposed" docs/ai/DECISIONS.md              # 0
grep "Status:" docs/ai/DECISIONS.md | sort -u             # Frozen, Deprecated only
find docs/sprints/sprint-12/ -type f
find evidence/sprint-12/ -type f
python -m pytest tests/ --co -q 2>/dev/null | tail -1
npx vitest list 2>/dev/null | wc -l
python -m pytest tests/e2e/ --co -q 2>/dev/null | tail -1
curl -s http://localhost:8003/openapi.json | python -m json.tool | head -5
bash tools/sprint-closure-check.sh 12
```

---

## Implementation Notes

| Task | Planned | Implemented | Why Different |
|------|---------|-------------|---------------|
| 12.1→12.10 | — | — | — |

## File Manifest

| File | Action | Task |
|------|--------|------|
| docs/api/openapi.json | Create | 12.1 |
| tests/e2e/conftest.py | Create | 12.2 |
| tests/e2e/test_scenarios.py | Create | 12.3 |
| docs/OPERATOR-GUIDE.md | Create | 12.6 |
| tools/sprint-closure-check.sh | Modify | kickoff |
| docs/ai/DECISIONS.md | Modify | kickoff |

---

## Next Step

**Produced:** SPRINT-12-TASK-BREAKDOWN.md v3
**Next actor:** Operator
**Action:** GPT re-review PASS → authorize implementation.
**Blocking:** Yes — GPT PASS required.
