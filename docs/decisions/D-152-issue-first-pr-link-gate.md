# D-152: Issue-First PR Link Gate

**Status:** Frozen
**Date:** 2026-04-09
**Sprint:** D-152 (standalone)
**Author:** AKCA (operator)

## Context

PR #448 (D-151) was opened before its GitHub issue existed. GPT review flagged this as a workflow violation. The repo's governance model (D-142) requires issue-first intake, but no automated gate enforces issue-to-PR linkage at PR creation time.

## Decision

Every implementation PR must be linked to a task issue before it can pass CI. The linkage gate is fail-closed: a PR without a valid task issue reference fails the `pr-issue-gate` workflow check.

### Rules

1. **Issue-first**: A GitHub issue must exist before a PR is opened for implementation work.
2. **Machine-readable linkage**: PR body must contain `Task-Issue: #<id>` and `Closes: #<task-issue>` fields.
3. **Fail-closed gate**: `tools/pr-issue-link-check.py` validates linkage. Missing or invalid linkage = FAIL.
4. **Exempt categories**: PRs with titles starting with `docs:`, `chore:`, `ci:`, `fix:` (hotfix), or `bootstrap:` are exempt from task-issue linkage. Exempt PRs must still have a summary.
5. **Single task per PR**: An implementation PR must reference exactly one task issue. Multi-task PRs are rejected.
6. **Sprint alignment**: If `Sprint:` field is present, it must match the task issue's milestone sprint number.
7. **issues.json extension**: `issue-from-plan.yml` emits `parent_issue`, `task_issue`, `branch`, `branch_exempt`, `pr_required`, `allowed_pr_types`, and `task_type` fields for each task.

### Preserves

- D-142 intake behavior (extended, not weakened)
- Fail-closed governance posture
- Existing sprint kickoff gate (`tools/task-intake.py`)

## Consequences

- Implementation PRs without task issues are blocked by CI.
- Docs/chore/ci/hotfix PRs remain lightweight (exempt path).
- `issues.json` becomes the authoritative linkage manifest for PR validation.
- Sprint closure can deterministically verify all tasks have merged PRs.
