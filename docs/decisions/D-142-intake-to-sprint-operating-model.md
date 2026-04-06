# D-142 — Intake-to-Sprint Operating Model Freeze

- **ID:** D-142
- **Title:** Intake-to-Sprint Operating Model Freeze
- **Status:** frozen
- **Phase:** 9 (Sprint 69)
- **Date:** 2026-04-06
- **Owner:** AKCA
- **Recommended by:** Claude (Phase 9 intake review)

-----

## Context

- Current repo behavior has contract drift between frozen decisions, workflows, validator rules, and operator/session protocols.
- `CLAUDE.md` session flow starts work without mandatory task claim or canonical sprint binding.
- `GOVERNANCE.md` places issue/milestone/project synchronization late in closure-oriented steps instead of intake.
- `issue-from-plan.yml` does not fully implement the writer contract implied by D-122 and D-123.
- `project-auto-add.yml` creates issues on Project V2 without initializing required canonical fields.
- `tools/project-validator.py` rejects blank `Status` while automation can create blank `Status`, so the system can generate its own invalid state.
- Repo appears to operate in dual-mode:
  - frozen model: backlog item != sprint task
  - live practice: `B-xxx` issues are treated as sprint tasks via `Sprint Target`
- State documents are not treated as one coherent source of truth; `current.md`, `open-items.md`, `STATE.md`, and `NEXT.md` can diverge without detection.

-----

## Decision

1. **Canonical operating model** is frozen as:
   - Backlog item != sprint task (per D-122)
   - Sprint membership must be explicit and machine-written
   - Intake binding happens before implementation starts
   - No task execution is valid before canonical issue/project/sprint state is established
2. **Intake becomes a hard gate**, not a closure-era cleanup step.
3. **Project V2 canonical fields** remain narrow:
   - `Status`
   - `Sprint`
   - `Priority`
   - `Task ID` required only for sprint tasks
   - `PR Link` derived, not canonical
4. **Session protocol must fail-closed** if canonical binding is missing or governed state docs conflict.
   - Session start reads:
     - `docs/ai/handoffs/current.md`
     - `docs/ai/state/open-items.md`
     - `docs/ai/STATE.md`
     - `docs/ai/NEXT.md`
   - Any sprint/phase/task mismatch across these files -> **STOP; do not proceed.**
   - No implementation work starts until mismatch is resolved and canonical binding exists.
5. **Validators and workflow automation must enforce the same model.** No workflow may create state that validator rejects by design.
6. **Governed state document set** is frozen as:
   - `docs/ai/handoffs/current.md`
   - `docs/ai/state/open-items.md`
   - `docs/ai/STATE.md`
   - `docs/ai/NEXT.md`

   These files must be consistency-checked before implementation and before closure.

-----

## Trade-off

| Accepted                                                    | Deferred                                    |
|-------------------------------------------------------------|---------------------------------------------|
| Removes model ambiguity                                     | --                                          |
| Prevents invalid board states at creation time              | --                                          |
| Reduces Claude Code drift and late-stage reconciliation     | --                                          |
| Aligns repo behavior with validator and governance          | --                                          |
| Adds intake friction                                        | Friction reduction via better tooling (S71) |
| Requires workflow/tooling changes across multiple files     | Phased across S69-S72                       |
| May force migration of existing live backlog/sprint handling| One-time reconciliation                     |

-----

## Impacted Files/Components

| File                                     | Sprint | Change                          |
|------------------------------------------|--------|---------------------------------|
| `docs/decisions/D-142-*.md`              | S69    | New decision record             |
| `docs/ai/DECISIONS.md`                   | S69    | Index update                    |
| `tools/state-sync.py`                    | S69    | Governed doc consistency check  |
| `tools/project-validator.py`             | S70    | Remove hardcoded CLOSED_SPRINTS |
| `tools/close-merged-issues.py`           | S70    | Merge evidence gate             |
| `tools/task-intake.py`                   | S71    | New intake gate tool            |
| `.github/workflows/issue-from-plan.yml`  | S71    | Full writer contract            |
| `.github/workflows/project-auto-add.yml` | S71    | Canonical field init            |
| `docs/ai/GOVERNANCE.md`                  | S71    | Intake gate in checklist        |
| `CLAUDE.md`                              | S72    | Session protocol patch          |
| `tools/pre-implementation-check.py`      | S72    | Pre-impl gate tool              |

-----

## Validation Method

1. Static review against D-122, D-123, D-125, current project contract, and validator rules
2. Pre/post workflow tests showing no issue is created with blank canonical fields
3. State consistency test covering `current.md` / `open-items.md` / `STATE.md` / `NEXT.md`
4. Session start test proving implementation is blocked when task claim/binding is missing
5. `tools/close-merged-issues.py` test proving issues are not closed without linked merged PR evidence
6. Closure evidence demonstrating no contract drift remains between workflow, validator, and docs

-----

## Rollback / Reversal Condition

Reverse only if the project intentionally abandons backlog != sprint-task separation and freezes a different canonical operating model in a superseding decision with corresponding validator and workflow rewrites.

-----

## References

- D-122: Backlog-to-Project-to-Sprint Contract
- D-123: Project Item Contract v1
- D-125: Closure State Sync Rule
- GPT Review: Claude Code Task Intake / Sprint Binding Review (2026-04-06)
