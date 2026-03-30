# D-125: Closure State Sync — Triple Consistency + Backlog Evidence Rule

**ID:** D-125
**Status:** Frozen
**Phase:** 7 / Sprint 33
**Date:** 2026-03-28

---

## Context

Sprint 32 delivered B-005 (#154) and B-012 (#153) but backlog issues remain open. #100 is resolved but open. Pattern: sprint closure does not propagate to issue/board state.

## Decision

### Triple Consistency Rule

For every sprint task in a closed sprint, ALL THREE must be true simultaneously:

1. **Issue state** = closed
2. **Project Status** = Done
3. **Sprint identity** = correct sprint number (field or milestone)

Any single mismatch = validator FAIL. No exceptions.

### Backlog Closure Rule

A backlog issue may be closed when ALL of:

1. All linked sprint tasks are Done + closed
2. At least one merged PR references the backlog issue (evidence of code delivery)
3. Relevant tests pass (CI green on merge commit)
4. Operator confirms acceptance (explicit comment or sprint closure sign-off covers linked items)

If conditions 1-3 are met but operator has not reviewed, backlog issue stays open with status note. Validator flags as WARN ("eligible for closure, pending operator review").

Backlog issues are NEVER auto-closed by automation. Operator or delegated operator (GPT) makes the close decision.

### Forbidden States

| State | Rule |
|-------|------|
| Resolved but open | FAIL — close the issue or revert resolution |
| Done on board but open as issue | FAIL — close issue or revert Status |
| Closed issue but not Done on board | FAIL — set Status to Done or reopen issue |
| Sprint task in closed sprint but issue open | FAIL — close issue |
| Backlog issue closed without merged PR evidence | FAIL — reopen or provide evidence |

### Enforcement

- `project-validator.py` checks all consistency rules
- Validator runs at: sprint closure (mandatory gate), next sprint kickoff (belt-and-suspenders)
- Backlog closure check: validator lists "eligible for closure" items at sprint end

## Trade-off

| Accepted | Deferred |
|----------|----------|
| Triple consistency is hard gate | Automated backlog closure |
| Backlog closure requires operator judgment | Full cross-sprint dependency tracking |
| Evidence = merged PR + CI green | Acceptance testing framework |

## Impacted Files

- `tools/project-validator.py` — Triple consistency + backlog closure checks
- `tools/sprint-closure-check.sh` — Call project-validator as sub-check

## Validation

- Run validator on S32: expect #153 and #154 flagged (done but open)
- Fix: close both, verify Done status
- Re-run: expect PASS
- Run on #100: expect flagged (resolved but open)

## Rollback

Process rule — no code to roll back. If triple consistency proves too strict, relax individual checks to WARN with explicit waiver doc.
