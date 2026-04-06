# Review Delta Packet v2 — Sprint {N}

<!--
Send this as the user payload to the review model.
Do not paste full handoffs, prior sprint history, or narrative summaries.
This packet is delta-only and closure-focused.
-->

## 0. REVIEW TYPE
- Round: {1 | 2 | 3+}
- Review Type: {closure | re-review}
- Ask: Return verdict using review-verdict-contract.v2

## 1. BASELINE
- Phase: {phase}
- Sprint: {N}
- Class: {product | governance}
- Model: {A | B}
- implementation_status: {not_started | in_progress | done}
- closure_status: {not_started | evidence_pending | review_pending | closed}
- Repo Root: `{path}`
- Evidence Root: `evidence/sprint-{N}/`

## 2. SCOPE
| Task | Issue | Owner | Description |
|------|-------|-------|-------------|
| T-{N}.01 | #{issue} | {owner} | {one-line} |
| T-{N}.02 | #{issue} | {owner} | {one-line} |

## 3. GATE STATUS
| Gate | Required | Status | Evidence |
|------|----------|--------|----------|
| Kickoff Gate | yes | {PASS/HOLD} | {decision/task doc/checklist path} |
| Mid Review Gate | yes | {PASS/HOLD/N/A} | {task/evidence path} |
| Final Review Gate | yes | {PASS/HOLD} | {closure packet / review summary path} |

## 4. DECISIONS
### Frozen Decisions Touched
| ID | Title | Status | Action |
|----|-------|--------|--------|
| D-{XXX} | {title} | frozen | {new | amended | referenced} |

### Open Decisions
- None.

## 5. CHANGED FILES
```text
{git diff --stat or explicit file list}
```

## 6. TASK DONE CHECK (5/5)
| Task | Code Committed | Tests Passing | Evidence Saved | Implementation Notes Updated | File Manifest Updated |
|------|----------------|---------------|----------------|------------------------------|-----------------------|
| T-{N}.01 | {Y/N} | {Y/N} | {Y/N} | {Y/N} | {Y/N} |
| T-{N}.02 | {Y/N} | {Y/N} | {Y/N} | {Y/N} | {Y/N} |

## 7. TEST SUMMARY
| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| Backend (pytest) | {N} | {N} | {+N/0} |
| Frontend (vitest) | {N} | {N} | {+N/0} |
| E2E (playwright) | {N} | {N} | {+N/0} |
| TSC errors | {N} | {N} | {delta} |
| Lint errors | {N} | {N} | {delta} |

## 8. EVIDENCE MANIFEST
Use `PRESENT`, `MISSING`, or `NO EVIDENCE` only. Do not use `N/A` unless the sprint threshold or platform rule truly exempts the artifact.

| File | Status | Source Command |
|------|--------|----------------|
| pytest-output.txt | {status} | `python -m pytest ...` |
| vitest-output.txt | {status} | `npx vitest run` |
| tsc-output.txt | {status} | `npx tsc --noEmit` |
| lint-output.txt | {status} | `npm run lint` |
| build-output.txt | {status} | `npm run build` |
| validator-output.txt | {status} | `python tools/project-validator.py` |
| grep-evidence.txt | {status} | `{grep command}` |
| live-checks.txt | {status} | `{curl/check commands}` |
| closure-check-output.txt | {status} | `bash tools/sprint-closure-check.sh {N}` |
| review-summary.md | {status} | `review artifact path` |
| file-manifest.txt | {status} | `manifest path` |
| retrospective.md | {status} | `retrospective path` |
| sse-evidence.txt | {status} | `{S10+ if required}` |
| mutation-drill.txt | {status} | `{S11+ if required}` |
| e2e-output.txt | {status} | `{S12+ if required}` |
| lighthouse.txt | {status} | `{S12+ if required}` |

## 9. CLAIMS TO VERIFY
1. {specific, checkable claim}
2. {specific, checkable claim}
3. {specific, checkable claim}

## 10. OPEN RISKS / WAIVERS
- None.

## 11. STOP CONDITIONS ALREADY CHECKED
- No stale closure packet used.
- No future task is cited as evidence for a current blocker.
- No status language outside canonical model.
- No missing raw output masked as a report.

## 12. PATCHES APPLIED (Round 2+ only)
| Patch | Blocker Ref | Fix Description | Commit | New Evidence |
|-------|-------------|-----------------|--------|--------------|
| P1 | B1 | {what changed} | {sha} | {artifact/path} |
| P2 | B2 | {what changed} | {sha} | {artifact/path} |
