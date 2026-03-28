# Project V2 Setup Guide

**Effective:** Sprint 31+
**Owner:** AKCA

---

## Project: Vezir Sprint Board

**URL:** https://github.com/users/ahmetcagriakca/projects/4
**ID:** PVT_kwHOABqWNs4BTA1T

## Current Fields

| Field | Type | Values |
|-------|------|--------|
| Status | Single Select | Todo, In Progress, Done |
| Type | Single Select | implementation, gate, process |
| Track | Single Select | Track 1-4 |
| Sprint | Text | Sprint number |
| Task ID | Text | Task identifier |

## Recommended Additional Setup (UI)

Add these field options via Project Settings UI:

1. **Status** — add options: `Backlog`, `Planned`, `Review`, `Blocked`
2. **Type** — add option: `Backlog`
3. **Priority** — create new Single Select field: `P1`, `P2`, `P3`

## Views

### Backlog View (create in UI)
- Filter: `label:backlog`
- Group by: Priority or Status
- Sort: Priority (P1 first)

### Active Sprint View (create in UI)
- Filter: current sprint milestone OR `label:sprint`
- Group by: Status
- Sort: Track

## Automation

- `project-auto-add.yml`: auto-adds issues with `sprint` label
- `status-sync.yml`: updates Status on PR events
- Priority managed via labels (`priority:P1`, `priority:P2`, `priority:P3`)

## Notes

- GitHub Project V2 API doesn't support adding field options via GraphQL
- New field options must be added via UI: Project Settings > Fields
- Backlog issues use label-based priority (not field-based) for API compatibility
