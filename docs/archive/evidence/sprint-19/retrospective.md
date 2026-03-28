# S19.RETRO — Sprint 19 Retrospective

**Sprint:** 19
**Phase:** 6
**Date:** 2026-03-27

---

## Did automation reduce manual work?

Yes. The issue-from-plan workflow created 12 GitHub issues automatically from plan.yaml in ~27 seconds. Previously this would have been manual issue creation. The validator script also automates plan/breakdown sync checking.

## Is branch-per-task working?

Yes, with manageable friction. Every task got its own branch and PR. The discipline was maintained throughout the sprint, including fix branches for workflow issues.

**Friction points:**
- Many PRs for a single sprint (24+ PRs including fixes and tests) — this is noisy but correct
- Browser-based PR creation/merge is time-consuming — could be automated with gh CLI
- Workflow fixes required multiple fix-test-merge cycles due to branch protection

## Should PR-per-task be activated for Sprint 20?

Already effectively in use. Branch protection forces PR for every merge. Recommend formalizing this in Sprint 20 as the standard workflow.

## What broke or was harder than expected?

1. **GitHub labels** — Workflow assumed labels existed. Fix: added label bootstrap step.
2. **Branch protection vs workflow push** — Workflow couldn't push to main. Fix: PR-based commit with `--admin` merge.
3. **Auto-merge unavailable on Free plan** — `gh pr merge --auto` requires paid plan. Fix: `--admin` flag.
4. **GitHub Actions PR permission** — Disabled by default. Had to enable in repo settings.
5. **Browser extension disconnections** — Chrome extension lost connection multiple times during session.

## What went well?

1. plan.yaml → issue creation pipeline works end-to-end
2. Validator catches mismatches correctly (tested both pass and fail)
3. Branch-per-task discipline was naturally enforced by protection
4. Idempotency works — re-running workflow doesn't create duplicates
5. All evidence captured inline during task execution

## Actionable Outputs

1. **S20 task:** Install `gh` CLI on development machine to speed up PR operations
2. **S20 task:** Add PR title/body validator (already in S20 plan)
3. **Process patch:** Document GitHub repo settings checklist (labels, actions permissions, branch protection) as pre-sprint setup
4. **Process patch:** Workflow should handle "No changes to commit" gracefully (already does)
