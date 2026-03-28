# D-123: Project V2 Item Contract — Canonical Truth Definition

**ID:** D-123
**Status:** Frozen
**Phase:** 7 / Sprint 33
**Date:** 2026-03-28

---

## Context

Project V2 board has 57 items across 6 custom fields. Field completeness: Status 100%, Sprint 72%, Type/Track/Task ID/PR Link 4% each. Only Status has a reliable automation writer (status-sync.yml). GPT sustainability review identified 7 blocking findings; Claude review added 3 more. Both reviewers agree: the field contract is too broad and unenforceable.

## Decision

### Canonical Item Contract (validator enforces)

| Truth | Source | Writer | Scope | Enforcement |
|-------|--------|--------|-------|-------------|
| **Project Status** | Project V2 field | `status-sync.yml` (PR events) | All items | Blank = FAIL |
| **Sprint identity** | Project V2 `Sprint` text field | `issue-from-plan.yml` sets at creation; validator checks format | Sprint tasks | Regex `^\d+$`; blank on sprint-labeled item = FAIL |
| **Priority** | GitHub label (`priority:P1/P2/P3`) | `backlog-import.py` for backlog; `issue-from-plan.yml` for sprint tasks | Backlog items (mandatory), sprint tasks (optional) | Backlog item without priority label = FAIL |
| **Task ID** | Issue title pattern `[SN-N.M]` | `issue-from-plan.yml` generates title | Sprint tasks only | Sprint-labeled item without `[SN-N.M]` title = FAIL (S31+), WARN (legacy) |
| **Issue State** | GitHub issue open/closed | Operator or automation at closure | All items | Done + open = FAIL; closed sprint + open issue = FAIL |
| **Milestone** | GitHub milestone | `issue-from-plan.yml` assigns | Sprint tasks | Sprint task without milestone = WARN (v1), FAIL (v2) |

### Non-canonical (not enforced, not closure truth)

| Field | Disposition | Rationale |
|-------|------------|-----------|
| **Type** (project field) | Keep as-is, non-canonical | API cannot reliably add options; labels serve type role |
| **Track** | Keep as-is, optional | 2/57 populated; useful for future swimlane but not proven |
| **PR Link** | Keep as-is, display only | Derived from GitHub closing refs; manual field is not closure truth |

### Write Authority Rule

Every canonical truth must have an identified automation writer. A truth with no automation writer cannot be in the canonical contract. If a new field is proposed, the proposal must name the writer before the field enters the contract.

### Sprint Identity — Two-Phase Approach

- **v1 (Sprint 33):** Sprint text field stays. Validator enforces `^\d+$` regex. `issue-from-plan.yml` sets value at creation. Milestone also assigned as belt-and-suspenders.
- **v2 (future, requires separate decision):** If milestone-based filtering proves equivalent, Sprint text field may be retired. Requires evidence from at least 2 sprints of dual-mode operation.

### Sprint 0 / Backlog Model

`Sprint 0` convention stays for backlog items. Backlog items have Sprint = 0 (or blank, validator accepts both). Sprint/backlog separation: `backlog` label = backlog item, `sprint` label = sprint task.

## Trade-off

| Accepted | Deferred |
|----------|----------|
| Enforceable contract with 5 canonical truths | Full field normalization across all 57 items |
| Type/Track/PR Link kept but non-canonical | Type field cleanup |
| Sprint text field retained (regex-validated) | Milestone-only transition (future evidence-gated) |

## Impacted Files

- `tools/project-validator.py` — New, enforces this contract
- `tools/sprint-closure-check.sh` — Patch, call project-validator
- `docs/shared/PROJECT-SETUP.md` — Update canonical vs non-canonical fields

## Validation

- project-validator.py runs on all 57 items
- All canonical truths checked per scope rules
- 0 false positives on S32 items (fully compliant)
- Known failures on legacy items handled by D-124

## Rollback

If regex validation on Sprint field causes friction, relax to WARN for 1 sprint, then re-evaluate. Non-canonical fields can be promoted with a new decision if proven valuable.
