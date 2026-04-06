# D-144: Project Aggregate Contract

**ID:** D-144
**Status:** frozen
**Phase:** 10
**Date:** 2026-04-05
**Frozen:** 2026-04-05
**Version:** v5
**Prepared by:** Claude (Architect)
**Review chain:**
- Proposal v1 (AKCA) → Architect review HOLD (Claude)
- Meta-review PASS (AKCA, 4 patches) → D-144 v2
- Decision-package review HOLD (AKCA, 4 patches) → D-144 v3
- Freeze-readiness review HOLD (AKCA, 1 patch) → D-144 v4
- Freeze review HOLD (AKCA, 1 patch) → This revision (v5)

**Patches applied in v5:**
- P1: DELETE restricted to {draft, active, paused}. Completed/archived projects cannot be soft-deleted — archive is the sole end-of-life path for completed projects.

---

## Context

Vezir is mission-centric. Controller decomposition, per-mission budget enforcement, startup recovery, approval FSM, and replay are all designed around the mission as the execution unit. There is no first-class aggregate above mission for grouping related work, sharing context, enforcing cross-mission governance, or tracking collective progress.

This is not a bug — single missions work fine standalone. But for multi-mission work (e.g., "build feature X across 5 missions"), the platform lacks: shared workspace, artifact continuity, cross-mission budget envelope, collective rollup, and project-level governance defaults.

### What Project Is Not

| Anti-pattern | Why wrong |
|---|---|
| Mission folder | Only organizes, does not govern |
| Big mission | Conflates aggregate with execution unit; FSM becomes unmanageable |
| UI-only concept | Backend has no truth-source; runtime cannot enforce |
| Unrestricted shared workspace | Breaks WorkingSet discipline (D-037) |

### Prerequisites (must be met before implementation)

| Prerequisite | Source | Rationale |
|---|---|---|
| Phase 8 complete | S62-S68 | Mission core must be hardened first |
| D-139 frozen + implemented | S63 | Controller decomposition must land before project-aware logic touches controller surface |
| B-140 closed | S64 | Mission-level budget enforcement before project-level envelope |
| Phase 8 retrospective complete | — | Lessons learned must feed project design |

---

## Decision

### 1. Entity Definition

Project is an **optional, first-class aggregate** above Mission.

- Optional: `project_id = null` means standalone mission. All existing behavior preserved.
- First-class: Project has its own store, API, status FSM, events, and lifecycle. It is not a tag, label, or UI grouping.
- Aggregate: Project owns scope, defaults, and rollup. It does not own execution — that remains Mission's domain.

**Core separation:**

| Concern | Owner |
|---|---|
| Execution (FSM, stages, tools, retries, recovery) | Mission |
| Governance context (scope, defaults, rollup, continuity) | Project |

Project does NOT touch mission FSM. Mission state transitions remain project-agnostic. Project observes and derives.

### 2. Schema — Phase 1 (Minimum Viable)

```json
{
  "project_id": "proj_<uuid>",
  "name": "Phase 8 Governance Hardening",
  "description": "",
  "status": "draft",
  "owner": "operator",
  "created_at": "2026-04-05T10:00:00Z",
  "updated_at": "2026-04-05T10:00:00Z"
}
```

Mission side: `mission.json` gains optional field `"project_id": "proj_<uuid>"` (default: null).

Mission → Project relationship is a foreign key held by mission. Project does not maintain `mission_ids[]` in Phase 1. Project store queries missions by `project_id` on read.

**Rationale:** Foreign key on mission avoids dual-write consistency problems. Project rollup is derived, not stored (Phase 1).

### 3. Mission Terminal State Reference

The project status FSM references mission terminal states for transition constraints. These must align with the repo-canonical `MissionStatus` enum in `agent/mission/mission_state.py`.

**Repo-canonical MissionStatus enum (12 states):**

| State | Outgoing transitions | Classification |
|---|---|---|
| `PENDING` | → PLANNING | Active |
| `PLANNING` | → READY, FAILED | Active |
| `READY` | → RUNNING | Active |
| `RUNNING` | → WAITING_APPROVAL, WAITING_REWORK, WAITING_TEST, WAITING_REVIEW, PAUSED, COMPLETED, FAILED, TIMED_OUT | Active |
| `WAITING_APPROVAL` | → RUNNING, FAILED | Active |
| `WAITING_REWORK` | → RUNNING | Active |
| `WAITING_TEST` | → RUNNING | Active |
| `WAITING_REVIEW` | → RUNNING | Active |
| `PAUSED` | → RUNNING, FAILED | Active |
| `COMPLETED` | ∅ (no outgoing) | **Quiescent — irrecoverable** |
| `FAILED` | → PLANNING, READY | **Quiescent — retryable** |
| `TIMED_OUT` | → PLANNING, READY | **Quiescent — retryable** |

**Definition for this decision:**

- **Active mission:** MissionStatus ∈ {PENDING, PLANNING, READY, RUNNING, WAITING_APPROVAL, WAITING_REWORK, WAITING_TEST, WAITING_REVIEW, PAUSED}. Mission may produce further work without operator intervention (except PAUSED, which requires resume but is not terminated).
- **Quiescent mission:** MissionStatus ∈ {COMPLETED, FAILED, TIMED_OUT}. Mission is not executing. FAILED and TIMED_OUT can be retried by operator action, but will not auto-execute.

Project transition constraints use "no active missions" (= all linked missions are quiescent), not "all missions completed."

**Note — API schema drift:** `agent/api/schemas.py` defines a separate `MissionState` enum with 10 states including `ABORTED` which does not exist in the internal FSM. `WAITING_REWORK`, `WAITING_TEST`, `WAITING_REVIEW` are collapsed into different names. This drift is pre-existing and out of scope for D-144, but must not be compounded — project code must reference the internal `MissionStatus` enum, not the API schema enum.

### 4. Project Status FSM

**States:** `draft`, `active`, `paused`, `completed`, `archived`, `cancelled`

Note: `at_risk` is excluded from Phase 1. It may be added in Phase 2+ as an observational or operator-confirmed status if evidence justifies a reliable detection rule.

**Transition matrix:**

| From | To | Trigger | Constraint |
|---|---|---|---|
| `draft` | `active` | operator start | — |
| `draft` | `cancelled` | operator cancel | — |
| `active` | `paused` | operator pause | — |
| `active` | `completed` | operator complete | no active missions (all linked missions quiescent) |
| `active` | `cancelled` | operator cancel | no active missions (all linked missions quiescent) |
| `paused` | `active` | operator resume | — |
| `paused` | `cancelled` | operator cancel | no active missions (all linked missions quiescent) |
| `completed` | `archived` | operator archive | — |
| `cancelled` | `archived` | operator archive | — |

**Enforcement:** Invalid transitions rejected by `project_store.py` with explicit error. No silent state coercion.

**Operator-only:** All transitions are operator-initiated in Phase 1. No auto-transitions.

**Active mission check:** Before `completed` or `cancelled` transition, project store queries `mission_store.list(project_id=X)` and verifies all returned missions have `status ∈ {COMPLETED, FAILED, TIMED_OUT}`. If any mission is active, transition is rejected with error listing the active mission IDs.

### 5. Delete / Archive / Link Lifecycle

#### Mission-Project Link Model

A mission's `project_id` field represents one of three states:

| project_id value | Meaning |
|---|---|
| `null` | Standalone mission. Never linked, or explicitly unlinked. |
| `proj_<uuid>` (project active) | Actively linked. Project governs context (Phase 2+). |
| `proj_<uuid>` (project inactive: completed/cancelled/archived) | **Historical link.** Mission retains reference for audit/lineage. Mission operates independently — project defaults/workspace do not apply at runtime. |

**Historical link** is the single consistent model for all project-end-of-life scenarios. There is no orphaning, no silent unlink, no "becomes standalone." The `project_id` stays; the project's operational influence stops.

#### Operations

| Operation | Condition | Behavior |
|---|---|---|
| **Soft-delete** | Project status ∈ {`draft`, `active`, `paused`}, no active missions | Sets project status = `cancelled`, sets `deleted_at` timestamp. Linked missions retain `project_id` as historical link. |
| **Soft-delete** | Project status ∈ {`draft`, `active`, `paused`}, active missions linked | **REJECTED.** Operator must wait for missions to reach quiescent state, or unlink them first. |
| **Soft-delete** | Project status ∈ {`completed`, `archived`} | **REJECTED.** Completed projects proceed to archive — delete is not a valid end-of-life path for completed work. Archived projects are immutable. |
| **Soft-delete** | Project status = `cancelled` | **NO-OP.** Already cancelled. |
| **Archive** | Project status ∈ {`completed`, `cancelled`} | Sets status = `archived`. Project becomes read-only. No new missions can be linked. Existing historical links preserved. |
| **Archive** | Project status ∈ {`draft`, `active`, `paused`} | **REJECTED.** Must complete or cancel first. |
| **Link mission** | Project status ∈ {`draft`, `active`} | Sets `mission.project_id = project_id`. Emits `project_mission_linked` event. |
| **Link mission** | Project status ∈ {`paused`, `completed`, `cancelled`, `archived`} | **REJECTED.** Paused projects cannot accept new scope (resume first). Inactive/archived projects are closed to new links. |
| **Unlink mission** | Project status ∈ {`draft`, `active`, `paused`} | Sets `mission.project_id = null`. Emits `project_mission_unlinked` event. Mission becomes standalone. |
| **Unlink mission** | Project status ∈ {`completed`, `cancelled`, `archived`} | **REJECTED.** Inactive/archived projects are immutable — historical links preserved. |

**Lifecycle paths (exhaustive):**
- Draft work abandoned: `draft → cancelled → archived`
- Active work abandoned: `active → cancelled → archived`
- Paused work abandoned: `paused → cancelled → archived`
- Work completed: `active → completed → archived`
- Archive is the sole terminal state. Delete (soft) is cancel-semantic, not destruction.

#### Runtime Behavior for Historical Links

When a mission has `project_id` pointing to an inactive project:
- Mission execution proceeds normally (project has no runtime influence in Phase 1)
- Phase 2+: workspace injection, defaults inheritance skipped if project is inactive
- API response includes project status so UI can display "project inactive" indicator
- Historical link preserved for audit trail, replay, and lineage queries

### 6. Persistence

New file: `persistence/project_store.py`

Pattern follows existing stores (`mission_store.py`, `template_store.py`):
- Storage: `projects/{project_id}/project.json`
- Atomic write: `temp file → fsync → os.replace`
- CRUD: `create()`, `get()`, `list()`, `update()`, `delete()` (soft)
- Query: `list_by_status()`, `get_missions()` (queries mission_store by project_id)
- Validation: status transition enforcement on `update()`, active-mission check on complete/cancel/delete

No separate rollup store in Phase 1. Rollup is computed on read.

### 7. API Surface — Phase 1

```
POST   /api/projects                         → create (name, description)
GET    /api/projects                         → list (filter: status)
GET    /api/projects/{id}                    → detail + derived mission summary
PATCH  /api/projects/{id}                    → update (name, description, status transition)
DELETE /api/projects/{id}                    → soft-delete (reject if active missions or completed/archived)
POST   /api/projects/{id}/missions/{mid}     → link mission to project
DELETE /api/projects/{id}/missions/{mid}     → unlink mission from project
```

**Detail endpoint response includes:**

```json
{
  "project": { "...schema fields..." },
  "mission_summary": {
    "total": 5,
    "by_status": {
      "COMPLETED": 2,
      "RUNNING": 1,
      "PENDING": 2
    },
    "active_count": 3,
    "quiescent_count": 2,
    "last_activity": "2026-04-05T12:00:00Z"
  }
}
```

`mission_summary` is computed on each GET, not stored. Acceptable for Phase 1 scale (expected: <50 missions per project).

**Error responses (reject cases):**
- `409 Conflict` — delete/complete/cancel with active missions. Body includes list of active mission IDs.
- `409 Conflict` — delete on completed/archived project. Body: "completed projects must be archived, not deleted."
- `409 Conflict` — link/unlink on inactive/archived project.
- `422 Unprocessable` — invalid status transition.

### 8. Rollup Ownership

| Principle | Rule |
|---|---|
| Source of truth | Mission is always source of truth for its own state |
| Rollup nature | Project rollup is **derived**, never canonical |
| Phase 1 computation | Lazy — computed on API read from mission_store query |
| Phase 2 computation | EventBus handler maintains cached rollup; API serves from cache, recomputes on cache miss or staleness |
| Conflict resolution | If cached rollup disagrees with live mission query, live query wins and cache is refreshed |
| Ownership | No separate rollup store in Phase 1. Phase 2 rollup cache is owned by `ProjectRollupHandler` (EventBus handler). API layer is consumer, not owner. |

### 9. EventBus Integration

New event types (Phase 1):

| Event | Payload | Handler |
|---|---|---|
| `project_created` | project_id, name, owner | Audit trail |
| `project_status_changed` | project_id, old_status, new_status, actor | Audit trail |
| `project_mission_linked` | project_id, mission_id | Audit trail |
| `project_mission_unlinked` | project_id, mission_id | Audit trail |
| `project_deleted` | project_id, deleted_at, actor | Audit trail |

Phase 1 handlers: audit trail logging only. No rollup handler, no SSE broadcast, no cross-mission governance handler.

Phase 2 adds: SSE broadcast handler, rollup cache handler.
Phase 3 adds: budget envelope handler, policy enforcement handler.

### 10. Mission Integration Points

**Mission create flow (project_id provided):**

1. Validate project exists and status ∈ {`draft`, `active`}
2. Set `mission.project_id = project_id`
3. Emit `project_mission_linked` event
4. Mission proceeds with normal creation flow

**Paused project rejection:** A paused project cannot accept new missions. Operator must resume the project first. Rationale: `paused` means "no new scope until resumed." Allowing new links during pause contradicts pause semantics.

**No inheritance in Phase 1.** Mission does not inherit project defaults. This is Phase 2 scope (D-145).

**Mission execution flow:**
- Phase 1: `project_id` is metadata only. No runtime influence.
- Phase 2+: if project is active and has workspace, WorkingSet injection applies. If project is inactive, no injection.

### 11. WorkingSet Interaction

**Phase 1: No WorkingSet changes.**

Project entity exists but has no workspace paths. No files to grant access to. WorkingSet enforcer is unaffected.

**Phase 2 (D-145 scope):** Specified separately. D-144 only establishes the entity.

### 12. Migration & Backward Compatibility

| Concern | Guarantee |
|---|---|
| Existing missions | Unaffected. `project_id = null` = standalone. All existing behavior preserved. |
| Existing tests | No test changes required. project_id=null path is default. |
| Existing API endpoints | No breaking changes. Mission CRUD unchanged. |
| CI | Existing CI passes without modification. New project tests added alongside. |
| Mission store | `project_id` field added as optional. Missing field on read defaults to null. No migration script needed — old mission JSON files work as-is. |

**Zero-disruption rule:** Any mission created before D-144 implementation must behave identically after. If a test fails due to project aggregate code, it is a regression, not a migration issue.

### 13. Operational Visibility (Phase 1)

No dedicated project UI in Phase 1. But project entities must be discoverable:

- `GET /api/projects` returns all projects with status filter
- `GET /api/projects/{id}` returns full detail including mission summary
- Existing admin/debug tooling can call these endpoints
- CLI: `curl http://localhost:8003/api/projects | python -m json.tool`

Dashboard UI deferred to Phase 2 (D-145 scope).

---

## Trade-off

| Accepted | Deferred |
|---|---|
| Optional aggregate (project_id=null path preserved) | Mandatory project requirement |
| Thin Phase 1 (entity + CRUD + link + events) | Workspace, artifacts, rollup cache, UI |
| Operator-only status transitions | Auto-transitions (at_risk, auto-complete) |
| Lazy rollup computation | EventBus-driven rollup cache |
| Foreign key on mission (no mission_ids[] on project) | Bidirectional index |
| Soft-delete only for draft/active/paused (completed → archive only) | Hard delete, delete-from-any-state |
| Historical link model (project_id retained on inactive project) | Auto-unlink on project end-of-life |
| No WorkingSet changes in Phase 1 | Project workspace injection (D-145) |
| No inheritance in Phase 1 | Policy/budget inheritance (Phase 3) |

---

## Impacted Files (Phase 1 Implementation)

| File | Change |
|---|---|
| `persistence/project_store.py` | **NEW** — project CRUD with atomic write, FSM enforcement, active-mission check |
| `persistence/mission_store.py` | **MODIFY** — add optional project_id field handling, list-by-project query |
| `api/project_routes.py` | **NEW** — 7 endpoints |
| `api/app.py` | **MODIFY** — register project router |
| `events/event_types.py` | **MODIFY** — add 5 project event types |
| `events/handlers/project_handler.py` | **NEW** — audit trail handler |
| `mission/mission_state.py` | No change — project_id is on mission JSON, not on MissionState dataclass |
| `tests/test_project_store.py` | **NEW** |
| `tests/test_project_api.py` | **NEW** |
| `tests/test_project_fsm.py` | **NEW** |
| `tests/test_project_events.py` | **NEW** |
| `tests/test_project_historical_link.py` | **NEW** — verify historical link behavior |
| `tests/test_backward_compat.py` | **NEW** — verify project_id=null preserves all behavior |

---

## Validation

| Check | Method |
|---|---|
| Project CRUD works | test_project_store.py + test_project_api.py |
| Status FSM enforces valid transitions | test_project_fsm.py — invalid transitions rejected with 422 |
| Status FSM rejects complete/cancel with active missions | test_project_fsm.py — 409 with active mission IDs |
| Mission link/unlink works | test_project_api.py — link, unlink, re-link |
| Link rejected on inactive/archived project | test_project_api.py — 409 |
| Link rejected on paused project | test_project_api.py — 409, must resume first |
| Unlink rejected on inactive/archived project | test_project_api.py — 409 |
| Soft-delete rejected with active missions | test_project_api.py — 409 |
| Soft-delete rejected on completed/archived project | test_project_api.py — 409 |
| Historical link preserved after project inactive | test_project_historical_link.py |
| Mission with historical link operates normally | test_project_historical_link.py |
| EventBus events emitted | test_project_events.py — 5 event types verified |
| Existing mission tests pass unchanged | CI — 0 regressions |
| project_id=null missions behave identically | test_backward_compat.py |
| Rollup computation correct | test_project_api.py — detail endpoint mission_summary |
| Active/quiescent classification matches MissionStatus enum | test_project_fsm.py — explicit enum check |

---

## Rollback / Reversal Condition

If project aggregate introduces unexpected complexity or regression:
1. Remove project_routes.py from app router registration
2. project_id field on mission becomes inert (ignored by all code paths)
3. No mission data loss — project_id=null is the natural default
4. Project store files can be archived

Reversal is low-risk because project is additive — it adds a new entity without modifying existing execution paths.

---

## Phase Roadmap (Reference Only — Not Frozen)

| Phase | Scope | Decision | Prerequisite |
|---|---|---|---|
| **Faz 1** | Entity + CRUD + link + events + FSM | **D-144 (this)** | Phase 8 complete, D-139 implemented |
| **Faz 2** | Workspace + artifact publish + rollup cache + SSE + dashboard UI | D-145 (separate) | D-144 implemented |
| **Faz 3** | Budget envelope + policy inheritance + cross-mission dependency + replay | D-14X (future) | B-140 closed, D-145 implemented |

Faz 2-3 decisions opened when their prerequisites are met. Not before.
