# Sprint 71 Retrospective

## What went well

1. **Clean implementation** — All 5 tasks completed in a single session with no blockers.
2. **State consistency** — Caught stale open-items.md via state-sync --check during intake gate testing, fixed immediately.
3. **Test coverage** — 40 tests covering all intake gate functions with proper mocking (patch.object for hyphenated module name).
4. **CI green first try** — PR #356 passed all checks on first push.

## What could improve

1. **Hyphenated module naming** — `task-intake.py` naming convention (matching other tools) caused `@patch("task-intake.gh")` failures. Used `patch.object(intake, "gh")` as workaround. Consider underscore naming for new tools in future.
2. **Project V2 credential gap** — T71.4 workflow code was implemented without verifying that `GITHUB_TOKEN` has Project V2 access. This is a pre-existing infrastructure limitation (Project V2 GraphQL requires PAT). Should have been caught during task planning and scoped as "code-prep + credential dependency" from the start. Created B-148 (#358) for follow-up.
3. **GPT review cycle count** — 6 rounds due to evidence completeness escalation + T71.4 overclaim. Earlier honest scoping would have avoided rounds 3-6.

## Patterns to keep

- Running task-intake.py against the active sprint as a smoke test during development.
- Using state-sync --check as a pre-implementation gate catches stale docs early.
- `patch.object(module, "fn")` pattern for testing hyphenated module names.

## Metrics

- Tasks: 5/5 completed
- Tests: +40 new (102 root total, 1887 overall)
- Decisions: 0 new
- CI: All green
- Time: Single session
