# GitHub Project Field Schema — Vezir Platform

**Effective:** Sprint 20+

---

## Project Board

**Name:** Vezir Sprint Board
**Type:** GitHub Projects V2 (table + board views)

## Fields

| Field | Type | Values | Source |
|-------|------|--------|--------|
| Status | Single select | Todo, In Progress, In Review, Done | Auto-synced by workflow |
| Sprint | Number | 19, 20, 21... | Set by issue label |
| Task ID | Text | 20.1, 20.2, etc. | Extracted from issue title `[SN-N.M]` |
| Track | Single select | Track 1, Track 2, Track 3, Track 4 | From plan.yaml |
| Type | Single select | implementation, gate, process | From plan.yaml |
| PR Link | Text | PR URL or number | Updated by PR linkage workflow |

## Views

1. **Board View** — Kanban by Status (Todo → In Progress → In Review → Done)
2. **Sprint Table** — Grouped by Sprint, sorted by Task ID
3. **Track View** — Grouped by Track

## Automation Rules

| Trigger | Action |
|---------|--------|
| Issue created with `sprint` label | Auto-add to project |
| PR opened referencing issue | Status → In Progress |
| PR merged referencing issue | Status → Done |
| PR closed (not merged) | Status → Todo |

## Label Convention

| Label | Purpose |
|-------|---------|
| `sprint` | Sprint-scoped issue |
| `phase-6` | Current phase |
| `automation` | Automation-related |
| `tooling` | Developer tooling |
| `github-actions` | Workflow-related |
| `github` | GitHub infrastructure |
| `process` | Process documentation |
| `gate` | Review gate |
| `foundation` | Foundation/blocking work |
| `bug` | Bug report |
| `enhancement` | Feature request |
