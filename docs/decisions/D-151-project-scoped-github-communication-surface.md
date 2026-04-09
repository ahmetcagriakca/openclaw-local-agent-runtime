# D-151 — Project-Scoped GitHub Communication Surface

- **ID:** D-151
- **Title:** Project-Scoped GitHub Communication Surface
- **Status:** frozen
- **Phase:** Phase 10
- **Date:** 2026-04-09
- **Owner:** AKCA

---

## Context

- Vezir already uses GitHub for backlog, sprint, milestone, and Project V2 automation (D-122, D-123, D-142), but that automation lives outside the project aggregate.
- D-144 introduced Project as a first-class aggregate above Mission.
- D-145 introduced workspace/artifact boundaries and SSE/event handling for Project.
- Operator workflow now needs project-bound GitHub communication without file handoff drift.
- The current Mission Control API is localhost-bound and fail-closed. Direct inbound GitHub webhook exposure is not part of the current transport boundary.

---

## Decision

1. GitHub becomes a **project-scoped communication surface**, not a controller or execution owner.
2. V1 scope is **outbound-only**:
   - operator binds a Project to a GitHub repo/thread
   - Vezir pulls issue/PR thread activity on demand
   - Vezir publishes top-level comments on demand
3. Binding metadata lives inside the Project aggregate under `project.github`.
4. Imported GitHub thread activity lives inside the Project aggregate under `project.github_activity`.
5. GitHub activity is observational/audit context only. It does **not** mutate mission FSM, approval FSM, or controller execution state.
6. EventBus emits project-scoped GitHub events:
   - `project.github_bound`
   - `project.github_synced`
   - `project.github_comment_published`
7. Inbound webhook transport is **explicitly deferred**. No public callback surface is introduced in this decision.

---

## Trade-off

| Accepted | Rejected / Deferred |
|----------|---------------------|
| Preserves localhost fail-closed API boundary | Public inbound webhook endpoint |
| Reuses D-144 aggregate + D-145 SSE/EventBus path | GitHub-driven mission state mutation |
| Removes file-shuttle dependency for operator communication | Bidirectional automation in v1 |
| Keeps GitHub as context/audit, not execution authority | Treating GitHub as canonical runtime state |

---

## Impacted Files / Components

- `agent/persistence/project_store.py`
- `agent/api/project_api.py`
- `agent/events/catalog.py`
- `agent/events/handlers/project_handler.py`
- `agent/services/github_project_service.py`

---

## Validation Method

1. Project can store and return GitHub binding metadata.
2. Project can import normalized GitHub thread activity into aggregate state.
3. Project can publish a top-level GitHub comment using operator-only API.
4. GitHub actions emit project-scoped EventBus events and SSE broadcasts.
5. Missing token or GitHub API failure returns explicit API error, not silent success.

---

## Rollback / Reversal Condition

Reverse only if Vezir freezes a new transport boundary that explicitly allows public inbound GitHub callbacks or replaces project-scoped GitHub communication with a different canonical integration model.
