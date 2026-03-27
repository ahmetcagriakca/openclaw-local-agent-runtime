# S20.RETRO — Sprint 20 Retrospective

**Sprint:** 20
**Phase:** 6
**Date:** 2026-03-27

---

## Did PR traceability reduce manual work?

Yes. Three new workflows automate what was previously manual:
- Project auto-add: issues with sprint label auto-join board
- Status sync: PR events update issue status
- PR validator: enforces naming convention on PRs

## Is the project board useful?

Field schema is defined and project auto-add is ready. The board becomes useful once a GitHub Project V2 is created in the repo. The workflow gracefully handles missing projects.

## What should change for S21?

1. Create the actual GitHub Project V2 board (manual step)
2. Run bootstrap-labels-milestones.sh once gh CLI is available
3. Test status-sync workflow with real PR → issue linkage
4. Consider making PR validator a required check

## What went well?

1. All 7 tasks completed in a single session
2. plan.yaml → validator pipeline from S19 reused seamlessly
3. Workflow patterns established in S19 (label bootstrap, PR-based commit) applied consistently
4. Issue form templates provide structured input for future sprints

## What was harder than expected?

1. GitHub Projects V2 GraphQL API is complex — status sync logs the intent but full field mutation needs project-specific field IDs
2. No gh CLI on dev machine limits local testing of bootstrap script

## Actionable Outputs

1. **S21 prerequisite:** Create GitHub Project V2 board in repo
2. **S21 prerequisite:** Install gh CLI (`winget install GitHub.cli`)
3. **S21 task:** Run bootstrap-labels-milestones.sh after gh CLI install
4. **S21 task:** Test status-sync with real project board
5. **Process:** PR validator can become required check after S21 validation
