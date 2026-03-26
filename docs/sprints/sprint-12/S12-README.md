# Sprint 12 — Phase 5D: Polish + Phase Closure

**Repo path:** `docs/sprints/sprint-12/README.md`
**implementation_status:** not_started
**closure_status:** not_started
**Owner:** AKCA (operator)
**Implementer:** Claude Code
**Reviewers:** GPT (review gates), Claude (mid + final assessment)

---

## Goal

Achieve Phase 5 scoreboard 15/15 and close Phase 5. This is the final implementation sprint of Phase 5. Sprint 13 is stabilization (no new features).

## Scope

- API documentation (OpenAPI spec export)
- E2E test framework + 12+ scenarios
- Accessibility audit (Lighthouse > 90)
- Performance benchmark (baseline)
- Operator guide
- Legacy dashboard resolution (D-097)
- Phase 5 scoreboard verification + gap fix
- Phase 5 closure report
- Decision debt zero (D-001→D-101)

## Out of Scope

- Browser E2E (Phase 6, per D-098)
- Approval model changes (Phase 6, per D-099)
- Legacy dashboard code removal (Sprint 13)
- Folder migration (Sprint 13)

## Dependencies

| Dependency | Status | Blocker? |
|-----------|--------|----------|
| Sprint 11 closure_status=closed | ✅ Operator sign-off granted | Yes — repo-verified |
| Process Patch v4 accepted | ✅ 4/4 artifacts | Yes |
| OD-11→OD-16 frozen | ✅ D-097→D-101 | Yes |
| D-021→D-058 in DECISIONS.md | ✅ Extracted | Yes |
| GPT pre-sprint review PASS | ⬜ Packet v2 sent | Yes |

## Blocking Risks

| Risk | Mitigation |
|------|-----------|
| Lighthouse score below 90 | Iterative fix cycles. If 85-90, document gap, defer to Sprint 13. |
| E2E tests reveal backend bugs | Fix in-sprint (Task 12.9). Mid-review gate catches early. |
| Decision debt extraction errors | Verified with decision-debt-check.txt. Status vocab checked. |
| SSE evidence not reproducible | E2E scenario #6 covers SSE. Carry-forward from Sprint 11 if needed. |

## Acceptance Criteria

1. Phase 5 scoreboard 15/15 with evidence
2. All tests passing — counts from raw output (P-05)
3. Decision debt zero: D-001→D-101, no gaps
4. API documentation complete (OpenAPI spec)
5. Operator guide complete (≥ 8 sections)
6. Lighthouse accessibility > 90
7. Performance benchmark documented
8. Legacy dashboard resolved per D-097
9. Retrospective with ≥ 1 actionable output
10. GPT final review PASS + Claude assessment PASS

## Exit Criteria

- closure_status=closed granted by operator
- Phase 5 closure report produced
- 20 evidence files in evidence/sprint-12/
- Closure script: ELIGIBLE FOR CLOSURE REVIEW

## Files

| File | Purpose | Status |
|------|---------|--------|
| README.md | Sprint entry point (this file) | Active |
| SPRINT-12-TASK-BREAKDOWN.md | Plan, tasks, evidence, verification | Active |
| SPRINT-12-KICKOFF-GATE.md | Gate checklist | Active |
| SPRINT-12-MID-REVIEW.md | Mid-review report | Not yet |
| SPRINT-12-FINAL-REVIEW.md | Final review report | Not yet |
| SPRINT-12-RETROSPECTIVE.md | Retrospective | Not yet |
| SPRINT-12-CLOSURE-SUMMARY.md | Closure summary | Not yet |
| SPRINT-12-PHASE-CLOSURE.md | Phase 5 closure report | Not yet |

## Evidence Location

`evidence/sprint-12/` — 20 mandatory files. Evidence NOT stored under docs/.

## Closure Prerequisites

1. Phase 5 scoreboard 15/15
2. All tests passing — raw output counts
3. Decision debt zero (D-001→D-101)
4. GPT final review PASS + Claude assessment PASS
5. Retrospective complete
6. Closure script: ELIGIBLE FOR CLOSURE REVIEW
7. 20/20 evidence files
8. Operator sign-off (closure_status=closed)
