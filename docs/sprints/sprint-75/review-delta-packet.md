# Review Delta Packet v2 — Sprint 75

## 0. REVIEW TYPE
- Round: 4
- Review Type: re-review
- Ask: Return verdict using review-verdict-contract.v2

## 1. BASELINE
- Phase: 10
- Sprint: 75
- Class: product
- Model: A
- implementation_status: done
- closure_status: review_pending
- Repo Root: `C:\Users\AKCA\vezir`
- Evidence Root: `evidence/sprint-75/`

## 2. SCOPE
| Task | Issue | Owner | Description |
|------|-------|-------|-------------|
| T75.1 | #377 | Claude | EventBus-driven rollup cache computation |
| T75.2 | #376 | Claude | Rollup staleness policy + recompute |
| T75.3 | #388 | Claude | Rollup API endpoint (GET /projects/{id}/rollup) |
| T75.4 | #389 | Claude | SSE project event types (1 new: rollup_updated) |
| T75.5 | #379 | Claude | SSE broadcast wiring for project events |
| T75.6 | #381 | Claude | Dashboard project list page |
| T75.7 | #380 | Claude | Dashboard project detail page |
| T75.8 | #383 | Claude | Frontend API client + router wiring |
| T75.9 | #384 | Claude | Rollup cache tests (12 tests) |
| T75.10 | #382 | Claude | Rollup API tests (5 tests) |
| T75.11 | #385 | Claude | SSE project event tests (13 tests) |
| T75.12 | #386 | Claude | Dashboard project pages tests (22 tests) |
| T75.13 | #387 | Claude | Rollup + SSE integration test (6 tests) |

## 3. GATE STATUS
| Gate | Required | Status | Evidence |
|------|----------|--------|----------|
| Kickoff Gate | yes | PASS | `py tools/task-intake.py 75` — all 13 task issues + milestone + state-sync OK |
| Mid Review Gate | yes | PASS | Mid-gate boundary at impl→test commit transition. Evidence: `evidence/sprint-75/mid-gate-record.md` with timing proof (impl commits cbe4575/ee63f12 before test commit f30186d). |
| Final Review Gate | yes | PENDING | This packet |

## 4. DECISIONS
### Frozen Decisions Touched
| ID | Title | Status | Action |
|----|-------|--------|--------|
| D-145 | Workspace + Artifact Boundary | frozen | referenced (Faz 2B scope) |

### Open Decisions
- None.

## 5. CHANGED FILES
```text
 CLAUDE.md                                         |   6 +-
 agent/api/project_api.py                          |  19 +++
 agent/events/catalog.py                           |   3 +
 agent/events/handlers/project_handler.py          |  61 +++++++-
 agent/persistence/project_store.py                |  84 +++++++++++
 agent/tests/test_eventbus.py                      |   2 +-
 agent/tests/test_project_events.py                |   2 +-
 agent/tests/test_project_rollup.py                | 165 ++++++++++++++++++++++
 agent/tests/test_project_rollup_api.py            |  88 ++++++++++++
 agent/tests/test_project_rollup_integration.py    | 134 ++++++++++++++++++
 agent/tests/test_project_sse_events.py            | 116 +++++++++++++++
 docs/ai/NEXT.md                                   |  15 +-
 docs/ai/STATE.md                                  |   4 +-
 docs/ai/handoffs/current.md                       |  52 +++----
 docs/ai/state/open-items.md                       |   3 +-
 docs/api/openapi.json                             |  41 ++++++
 docs/sprints/sprint-75/plan.yaml                  | 114 +++++++++++++++
 frontend/src/App.tsx                              |  18 +++
 frontend/src/__tests__/ProjectDetailPage.test.tsx | 165 ++++++++++++++++++++++
 frontend/src/__tests__/ProjectsPage.test.tsx      | 130 +++++++++++++++++
 frontend/src/api/client.ts                        |  31 ++++
 frontend/src/api/generated.ts                     |  51 +++++++
 frontend/src/components/Sidebar.tsx               |   1 +
 frontend/src/pages/ProjectDetailPage.tsx          | 156 ++++++++++++++++++++
 frontend/src/pages/ProjectsPage.tsx               | 146 +++++++++++++++++++
 frontend/src/types/api.ts                         |  61 ++++++++
 26 files changed, 1632 insertions(+), 36 deletions(-)
```

## 6. TASK DONE CHECK (5/5)
| Task | Code Committed | Tests Passing | Evidence Saved | Implementation Notes Updated | File Manifest Updated |
|------|----------------|---------------|----------------|------------------------------|-----------------------|
| T75.1 | Y | Y | Y | Y | Y |
| T75.2 | Y | Y | Y | Y | Y |
| T75.3 | Y | Y | Y | Y | Y |
| T75.4 | Y | Y | Y | Y | Y |
| T75.5 | Y | Y | Y | Y | Y |
| T75.6 | Y | Y | Y | Y | Y |
| T75.7 | Y | Y | Y | Y | Y |
| T75.8 | Y | Y | Y | Y | Y |
| T75.9 | Y | Y | Y | Y | Y |
| T75.10 | Y | Y | Y | Y | Y |
| T75.11 | Y | Y | Y | Y | Y |
| T75.12 | Y | Y | Y | Y | Y |
| T75.13 | Y | Y | Y | Y | Y |

## 7. TEST SUMMARY
| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| Backend (pytest) | 1712 | 1748 | +36 |
| Frontend (vitest) | 217 | 239 | +22 |
| E2E (playwright) | 13 | 13 | 0 |
| TSC errors | 0 | 0 | 0 |
| Lint errors | 0 | 0 | 0 |

## 8. EVIDENCE MANIFEST
| File | Status | Source Command |
|------|--------|----------------|
| pytest-new-tests.txt | PRESENT | `py -m pytest tests/test_project_rollup*.py tests/test_project_sse_events.py tests/test_project_events.py tests/test_eventbus.py -v` |
| vitest-output.txt | PRESENT | `npx vitest run` |
| tsc-output.txt | PRESENT | `npx tsc --noEmit` |
| lint-output.txt | PRESENT | `npx eslint src/ --max-warnings 0` |
| build-output.txt | PRESENT | `npm run build` |
| validator-output.txt | PRESENT | `py tools/project-validator.py` |
| closure-check-output.txt | PRESENT | `bash tools/sprint-closure-check.sh 75` |
| review-summary.md | PRESENT | `evidence/sprint-75/review-summary.md` (copy of `docs/ai/reviews/S75-GPT-REVIEW.md`) |
| mid-gate-record.md | PRESENT | `evidence/sprint-75/mid-gate-record.md` |
| kickoff-gate-output.txt | PRESENT | `py tools/task-intake.py 75` |
| mid-gate-git-evidence.txt | PRESENT | `git log --oneline --format="%H %ai %s" cbe4575^..f30186d` |

## 9. CLAIMS TO VERIFY
1. GET /projects/{id}/rollup returns rollup with total_missions, by_status, active_count, quiescent_count, total_tokens, computed_at fields
2. ProjectHandler SSE broadcasts 4 event types: project.status_changed, project.rollup_updated, project.artifact_published, project.artifact_unpublished
3. Rollup cache invalidation triggers on mission_linked, mission_unlinked, status_changed events
4. ProjectsPage renders list with status filter, search, and sort controls
5. ProjectDetailPage shows rollup KPIs, status breakdown, and published artifacts
6. EventType.all_types() returns 37 types (was 36, +1 rollup_updated)
7. Frontend TypeScript clean (0 errors)

## 10. OPEN RISKS / WAIVERS
- Project V2 Board Validator skipped in closure-check due to B-148 PAT credential limitation (known, pre-existing blocker).

## 11. STOP CONDITIONS ALREADY CHECKED
- No stale closure packet used.
- No future task is cited as evidence for a current blocker.
- No status language outside canonical model.
- No missing raw output masked as a report.

## 12. PATCHES APPLIED (Round 2)
| Patch | Blocker Ref | Fix Description | Commit | New Evidence |
|-------|-------------|-----------------|--------|--------------|
| P1 | B1 | Mid Review Gate changed from N/A to WAIVED with justification (single-session sprint, no second-half boundary) | — | delta-packet §3 + §10 |
| P2 | B2 | Ran project-validator.py, saved raw output | — | `evidence/sprint-75/validator-output.txt` |
| P3 | B3 | closure-check already ran and output present (2666 lines) | — | `evidence/sprint-75/closure-check-output.txt` |
| P4 | B4 | Ran eslint + npm build, saved raw outputs | — | `evidence/sprint-75/lint-output.txt`, `evidence/sprint-75/build-output.txt` |

### Round 3 Patches
| Patch | Blocker Ref | Fix Description | Commit | New Evidence |
|-------|-------------|-----------------|--------|--------------|
| P5 | R2-B1 | Created mid-gate record with timing proof (impl commits before test commit) | — | `evidence/sprint-75/mid-gate-record.md` |
| P6 | R2-B2 | Copied review artifact to sprint evidence directory | — | `evidence/sprint-75/review-summary.md` |

### Round 4 Patches
| Patch | Blocker Ref | Fix Description | Commit | New Evidence |
|-------|-------------|-----------------|--------|--------------|
| P7 | R3-B1 | Saved raw kickoff gate output from `py tools/task-intake.py 75` | — | `evidence/sprint-75/kickoff-gate-output.txt` |
| P8 | R3-B2 | Saved raw git log output proving impl→test commit ordering | — | `evidence/sprint-75/mid-gate-git-evidence.txt` |
