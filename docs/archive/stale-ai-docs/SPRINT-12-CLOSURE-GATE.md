# Sprint 12 Closure Gate + Phase 5 Scoreboard

**Date:** 2026-03-25
**Status:** TEMPLATE — Activates after Sprint 11 closure

---

## 1. Sprint 12 Kickoff Gate

Decisions to close within first 24 hours:

| OD | Decision | Outcome Options | Deadline |
|----|----------|----------------|----------|
| OD-11 | Legacy dashboard | `retire` · `parallel-run waiver` · `blocked by gap` | Day 1 |
| OD-12 | E2E framework | `playwright` · `cypress` | Day 1 |
| OD-14 | Approval sunset Phase 2 | `full removal` · `warning only (waiver)` | Day 1 |
| OD-15 | OpenAPI export | `auto-generated` · `manual` | Day 1 |
| OD-16 | D-068 amendment | `update to 6-state` · `revert code to 5-state` | Day 1 |

Max 2 may remain open. 3+ open → sprint does not start.

**D-093/D-094/D-095 must be written to DECISIONS.md:**
These decisions cannot leak into sprint implementation. OD-11→D-093, OD-12→D-094, OD-14→D-095 are frozen and written to DECISIONS.md within the first 24 hours.

Additional prerequisites:
- Sprint 11 `closure_status=closed`
- D-081→D-096 present in DECISIONS.md (Sprint 11 Task 0)
- D-021→D-058 extraction done in Sprint 12 Task 0
- `tools/sprint-closure-check.sh` up to date

---

## 2. Sprint 12 Task List (Draft)

| Task | Description | Effort | Dependency |
|------|-------------|--------|------------|
| 12.0 | DECISIONS.md debt: D-021→D-058 extraction | L | — |
| 12.0b | D-059→D-080 gap check + fix | S | 12.0 |
| 12.0c | D-093/D-094/D-095 freeze to DECISIONS.md | S | OD-11/12/14 frozen |
| 12.1 | Feature gap analysis: `:8002` vs `:8003` | S | — |
| 12.2 | Legacy dashboard decision (D-093 freeze) | S | 12.1 |
| 12.3 | E2E framework setup | M | OD-12 frozen |
| 12.4 | E2E test scenarios (12+) | L | 12.3 |
| 12.MID | GPT mid-review (E2E coverage) — BLOCKER | — | 12.4 |
| 12.5 | Bundle optimization (lazy routes, code split) | M | — |
| 12.6 | Accessibility audit + fixes | M | — |
| 12.7 | Keyboard navigation | M | 12.6 |
| 12.8 | API documentation (OpenAPI or manual) | M | OD-15 frozen |
| 12.9 | Operator user guide | M | — |
| 12.10 | Approval sunset Phase 2 (Telegram removal) | M | OD-14 frozen |
| 12.11 | Performance benchmark + evidence | S | 12.5 |
| 12.12 | D-068 amendment to DECISIONS.md | S | OD-16 frozen |
| 12.FINAL | GPT final + Claude assessment — BLOCKER | — | All |

---

## 3. Sprint 12 Exit Criteria

| # | Criterion | Task | Status |
|---|----------|------|--------|
| 1 | Legacy dashboard retired OR parallel-run waiver documented | 12.2 | ⬜ |
| 2 | E2E tests: 12+ scenarios, all PASS | 12.4 | ⬜ |
| 3 | Bundle JS < 100 KB gzip (baseline-relative) | 12.5, 12.11 | ⬜ |
| 4 | Lighthouse Performance > 90 | 12.11 | ⬜ |
| 5 | Lighthouse Accessibility > 90 | 12.6, 12.11 | ⬜ |
| 6 | Keyboard navigation all pages | 12.7 | ⬜ |
| 7 | API documented | 12.8 | ⬜ |
| 8 | User guide written | 12.9 | ⬜ |
| 9 | D-021→D-058 in DECISIONS.md (0 debt) | 12.0 | ⬜ |
| 10 | D-068 amendment written | 12.12 | ⬜ |
| 11 | Approval sunset Phase 2 applied or waived | 12.10 | ⬜ |
| 12 | Validator PASS | 12.FINAL | ⬜ |
| 13 | GPT review 0 blocking | 12.FINAL | ⬜ |
| 14 | Claude assessment 0 blocking | 12.FINAL | ⬜ |
| 15 | Closure packet complete | 12.FINAL | ⬜ |
| 16 | Retrospective produced with actions | 12.FINAL | ⬜ |

---

## 4. Phase 5 Closure Scoreboard

When Sprint 12 finishes, Phase 5 (Mission Control) can close. Not by feel — by scoreboard.

| # | Criterion | Owner | Evidence File | Status | Blocker | Closure Date |
|---|----------|-------|---------------|--------|---------|-------------|
| 1 | Backend API: 10+ endpoints, read + write | Sprint 8+11 | contract-evidence.txt | ⬜ | | |
| 2 | React dashboard: 5+ pages, responsive | Sprint 9 | e2e-output.txt | ⬜ | | |
| 3 | SSE live updates: real-time push | Sprint 10 | contract-evidence.txt (SSE section) | ⬜ | | |
| 4 | Intervention: approve, reject, cancel, retry | Sprint 11 | mutation-drill.txt | ⬜ | | |
| 5 | E2E browser tests: 12+ scenarios | Sprint 12 | e2e-output.txt | ⬜ | | |
| 6 | Legacy dashboard retired OR parallel-run waiver | Sprint 12 | gap-analysis.md | ⬜ | | |
| 7 | API documented | Sprint 12 | docs/ | ⬜ | | |
| 8 | User guide written | Sprint 12 | docs/ | ⬜ | | |
| 9 | Accessibility Lighthouse > 90 | Sprint 12 | lighthouse.txt | ⬜ | | |
| 10 | All frozen decisions D-059→D-096+ documented | Sprint 12 | DECISIONS.md | ⬜ | | |
| 11 | D-021→D-058 zero debt | Sprint 12 | DECISIONS.md grep | ⬜ | | |
| 12 | 200+ tests total, 0 failures | Sprint 12 | closure-check-output.txt | ⬜ | | |
| 13 | GPT final review 0 blocking | Sprint 12 | review-final.md | ⬜ | | |
| 14 | Claude final assessment 0 blocking | Sprint 12 | assessment.md | ⬜ | | |
| 15 | Operator sign-off | Sprint 12 | — | ⬜ | | |

**15/15 ✅ → Phase 5 CLOSED.**
Any item missing → Phase 5 remains OPEN, blocker identified, fix planned.

---

## 5. Legacy Dashboard Decision

`:8002 vs :8003` outcome must be exactly one of three:

| Outcome | Condition | Evidence |
|---------|-----------|----------|
| `retire` | `:8003` covers all `:8002` features | gap-analysis.md: 0 gaps |
| `parallel-run waiver` | Known gaps exist but are acceptable | gap-analysis.md: gap list + waiver reason |
| `blocked by gap` | Critical feature missing | gap-analysis.md: blocker list |

"We'll see" is forbidden.

---

## 6. Performance Targets (Baseline-Relative)

| Metric | Baseline (Sprint 9) | Post-SSE+Mutation | Target |
|--------|---------------------|-------------------|--------|
| JS bundle (gzip) | 60.67 KB | Sprint 10: ~65 KB est. | < 100 KB |
| CSS bundle (gzip) | 3.74 KB | ~5 KB est. | < 10 KB |
| Lighthouse Performance | NO EVIDENCE | | > 90 |
| Lighthouse Accessibility | NO EVIDENCE | | > 90 |

`NO EVIDENCE` is written in the report but does not count as success.

---

*Sprint 12 Closure Gate + Phase 5 Scoreboard — OpenClaw*
*Template — Activates after Sprint 11 closure*
