# S21.RETRO — Sprint 21 Retrospective

**Sprint:** 21
**Phase:** 6
**Date:** 2026-03-28

---

## Did closure automation reduce manual work?

Yes. Five new tools automate previously manual closure steps:
- Review packet: auto-generates summary from sprint state
- Stale refs: catches broken file references across docs
- Archive manifest: produces move plan for sprint archival
- Merged-state check: verifies no loose branches
- Branch cleanup: lists/deletes merged remote branches

## What friction remains?

1. Closure preflight workflow had a Python env var bug on first run — fixed (PR #78), then verified end-to-end (S19 preflight SUCCESS 5/5)
2. Stale ref checker has many false positives from historical review docs referencing generic filenames
3. Archive manifest generates plan but doesn't execute moves (manual step remains)

## What went well?

1. All 6 tasks completed and merged in single session via gh CLI
2. gh CLI PR creation + merge eliminated browser dependency
3. Every tool has runtime evidence from actual execution
4. Tools are composable: merged-state check feeds into closure preflight

## Actionable Outputs

1. **Process:** Stale ref checker should exclude docs/ai/reviews/ (historical docs with expected stale refs)
2. **S22 candidate:** Archive execution script (actually moves files per manifest)
3. **S22 candidate:** Closure preflight end-to-end test via workflow_dispatch
