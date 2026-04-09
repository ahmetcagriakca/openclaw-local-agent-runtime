# PR Issue Link Audit — D-152

**Date:** 2026-04-09
**Auditor:** Claude Code (Opus)
**Scope:** Current repo PR/issue linkage state

## Artifacts Created

| Artifact | Path | Status |
|----------|------|--------|
| Decision doc | `docs/decisions/D-152-issue-first-pr-link-gate.md` | Frozen |
| PR template | `.github/pull_request_template.md` | Updated with D-152 fields |
| Validator | `tools/pr-issue-link-check.py` | Fail-closed |
| Workflow | `.github/workflows/pr-issue-gate.yml` | Active on PR events |
| Tests | `tests/test_pr_issue_link_check.py` | 32 tests, all pass |
| issue-from-plan | `.github/workflows/issue-from-plan.yml` | Extended with linkage fields |
| close-merged-issues | `tools/close-merged-issues.py` | D-152 exempt support |
| project-validator | `tools/project-validator.py` | PR_MISSING_ISSUE_LINK code added |

## Test Matrix Results

| Case | Expected | Actual |
|------|----------|--------|
| Valid linkage (task + closes) | PASS | PASS |
| Missing task issue | FAIL | FAIL |
| Missing closes line | FAIL | FAIL |
| Wrong sprint number | FAIL | FAIL |
| Wrong parent issue | FAIL | FAIL |
| Wrong branch | FAIL | FAIL |
| Exempt PR (docs/chore/ci/fix/bootstrap) | PASS | PASS |
| Multiple task issues | FAIL | FAIL |
| Closes != task issue | FAIL | FAIL |
| Native "Closes #N" syntax | PASS | PASS |

## issues.json Extended Fields

New fields emitted by `issue-from-plan.yml`:
- `task_issue` — task issue number (same as `issue`)
- `parent_issue` — parent sprint issue number
- `branch_exempt` — true if task does not require a branch
- `pr_required` — true if task requires a PR for closure
- `allowed_pr_types` — list of allowed PR types
- `task_type` — task type from plan.yaml

## Governance Impact

- GOVERNANCE.md section 4 updated with PR link gate
- DECISIONS.md updated with D-151 + D-152
- STATE.md architectural decisions count updated (149 frozen)
- D-142 intake behavior preserved (extended, not weakened)
