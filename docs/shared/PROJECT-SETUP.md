# Project V2 Setup Guide

**Effective:** Sprint 31+ (updated Sprint 33 — D-123/D-124/D-125)
**Owner:** AKCA

---

## Project: Vezir Sprint Board

**URL:** https://github.com/users/ahmetcagriakca/projects/4
**ID:** PVT_kwHOABqWNs4BTA1T

## Field Contract (D-123)

### Canonical Fields (validator enforces)

| Field | Type | Writer | Scope | Enforcement |
|-------|------|--------|-------|-------------|
| **Status** | Single Select | `status-sync.yml` | All items | Blank = FAIL |
| **Sprint** | Number | `issue-from-plan.yml` | Sprint tasks | Non-null integer; blank = FAIL |
| **Priority** | Label (`priority:P1/P2/P3`) | `backlog-import.py` / `issue-from-plan.yml` | Backlog (mandatory), sprint (optional) | Missing = FAIL (backlog) |
| **Task ID** | Title pattern `[SN-N.M]` | `issue-from-plan.yml` | Sprint tasks (S31+) | Missing = FAIL (S31+), WARN (legacy) |
| **Issue State** | GitHub open/closed | Operator / automation | All items | Mismatch with Status = FAIL |
| **Milestone** | GitHub milestone | `issue-from-plan.yml` | Sprint tasks | Missing = WARN (v1) |

### Non-canonical Fields (kept, not enforced)

| Field | Type | Rationale |
|-------|------|-----------|
| Type | Single Select | API cannot add options; labels serve type role |
| Track | Single Select | 2/57 populated; future swimlane |
| Task ID (project field) | Text | Redundant with title pattern |
| PR Link | Text | Derived from closing refs |

### Write Authority Rule

Every canonical truth must have an identified automation writer. No automation writer = not canonical.

## Writer Matrix

| Truth | Writer | Trigger | Notes |
|-------|--------|---------|-------|
| Project Status | `status-sync.yml` | PR events (open, close, merge) | Sets Todo/In Progress/Done |
| Sprint field | `issue-from-plan.yml` | Issue creation from plan.yaml | Number value |
| Priority label | `backlog-import.py` | Backlog import from spec | `priority:P1/P2/P3` |
| Task ID | `issue-from-plan.yml` | Issue title generation | `[SN-N.M]` pattern |
| Milestone | `issue-from-plan.yml` | Issue creation | Sprint N milestone |
| Issue state | Operator / `status-sync.yml` | Manual or PR merge | open/closed |
| Board membership | `project-auto-add.yml` | Issue label event | Auto-add on `sprint` label |

## Item Classification (D-124)

| Class | Detection | Validator |
|-------|-----------|-----------|
| Backlog | `backlog` label | Status, Priority, Issue State |
| Sprint task (S31+) | `sprint` label + Sprint >= 31 | Full contract |
| Legacy sprint (pre-S31) | `sprint` label + Sprint < 31 | Status, Sprint, Issue State; WARN on Task ID |
| Unclassified | None of above | **FAIL** — manual review required |

## Closure State Sync (D-125)

Triple consistency rule — ALL must be true for sprint tasks in closed sprints:
1. Issue state = CLOSED
2. Project Status = Done
3. Sprint = correct number

Backlog closure requires: all linked tasks done, merged PR, CI green, operator approval.

## Validator

```bash
python tools/project-validator.py           # human-readable
python tools/project-validator.py --json    # machine-readable
```

Integrated into `tools/sprint-closure-check.sh` — FAIL blocks closure.

## Views

### Backlog View (create in UI)
- Filter: `label:backlog`
- Group by: Priority or Status
- Sort: Priority (P1 first)

### Active Sprint View (create in UI)
- Filter: current sprint milestone OR `label:sprint`
- Group by: Status
- Sort: Track

## Notes

- GitHub Project V2 API doesn't support adding field options via GraphQL
- New field options must be added via UI: Project Settings > Fields
- Backlog issues use label-based priority (not field-based) for API compatibility
- Sprint field is number type (not text) — discovered during S33 normalization
