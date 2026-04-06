# D-145: Project Workspace and Artifact Boundary

**ID:** D-145
**Status:** frozen
**Phase:** 9 (Faz 2 — post D-144 implementation)
**Date:** 2026-04-05
**Version:** v4
**Frozen:** 2026-04-05
**Prepared by:** Claude (Architect)
**Prerequisite:** D-144 frozen + implemented

**Patches applied in v4:**
- P2: Publish request — `source_path` removed. Artifact location resolved from mission store by artifact_id.
- P3: Unpublish restricted to {draft, active} projects. Inactive projects' artifact sets are immutable.

---

## Context

D-144 establishes the project entity, CRUD, status FSM, and mission link. But Phase 1 projects have no workspace, no shared files, and no artifact publishing. Missions linked to a project still operate identically to standalone missions.

This decision adds the workspace layer: shared file space, artifact publish flow, WorkingSet enforcement interaction, derived rollup cache, SSE events, and dashboard UI.

**Explicit scope boundary:** This decision covers workspace and artifact boundary only. Policy inheritance, budget envelope, and locked defaults are Faz 3 scope (D-14X). D-145 does not grant project the ability to constrain or override mission behavior.

---

## Decision

### 1. Directory Structure

Workspace creation is **explicit** — operator enables it per project. Not all projects need file space.

When workspace is enabled:

```
projects/
  proj_<uuid>/
    project.json              ← D-144 entity
    workspace/                ← shared working files
    artifacts/                ← published mission artifacts
      mis_<uuid>/             ← per-mission artifact copies
    shared/                   ← project-level docs
      decisions/
      notes/
      briefs/
```

`project.json` gains optional fields (null until workspace is enabled):

```json
{
  "workspace_root": "projects/proj_<uuid>/workspace",
  "artifact_root": "projects/proj_<uuid>/artifacts",
  "shared_root": "projects/proj_<uuid>/shared"
}
```

If `workspace_root` is null, project has no file space. WorkingSet injection does not apply. Artifact publish is not available.

### 2. WorkingSet Injection

When a mission is linked to a project that has workspace paths **and** the project is active:

- `_build_default_working_set()` adds project paths to mission WorkingSet:
  - `shared/` → added to `directory_list` and `read_only`
  - `artifacts/` → added to `read_only` (mission can read other missions' published artifacts)
  - `workspace/` → added to `read_only`

**Write access:** Project directories are NOT added to `generated_outputs`, `read_write`, or `creatable`. Writing to project space requires the explicit artifact publish API (§3). This prevents uncontrolled writes to shared space.

**Inactive project:** If mission's `project_id` points to an inactive project (completed/cancelled/archived), no WorkingSet injection occurs. Mission operates with its standalone working set.

**Enforcement:** WorkingSet Enforcer handles project paths identically to any other path. No special bypass. Budget consumption applies normally (D-046).

**No override or constraint:** D-145 does not grant project the ability to restrict mission WorkingSet or override mission-level file access. That is Faz 3 scope.

### 3. Artifact Publish Flow

Mission artifacts remain in their local mission space during execution. Publishing to project is a separate, explicit step.

**Flow:**
1. Operator calls publish endpoint with `mission_id` and `artifact_id`
2. Validate mission is linked to an active project with workspace enabled
3. Resolve artifact source path from mission store/artifact registry by `artifact_id` — caller does not supply path
4. Validate artifact exists at resolved path
5. Copy artifact file to `projects/{project_id}/artifacts/{mission_id}/`
6. Update artifact header (D-047) with `project_id` and `published_to_project: true`
7. Emit `project_artifact_published` event

**No auto-publish.** Every publish is an explicit operator or API consumer action. Mission completion does not trigger publish. No completion hooks, no event-driven auto-publish. If a future decision introduces auto-publish, it must be a separate frozen decision with its own safety analysis.

**No caller-supplied paths.** The publish endpoint does not accept file paths from the caller. Artifact location is resolved server-side from the mission's artifact registry. This prevents boundary bypass where a caller could point to arbitrary files.

**Unpublish:** Operator can remove a published artifact via delete endpoint, subject to project status constraints (see §5.1). This removes the copy from project artifact root. Original in mission space is unaffected.

### 4. Rollup Cache

Phase 2 adds EventBus-driven rollup cache to replace Phase 1 lazy computation.

**Handler:** `ProjectRollupHandler` subscribes to mission state change events (`mission_state_transition`, `mission_completed`, `mission_failed`).

**Cache location:** `projects/{project_id}/rollup.json` — atomic write (temp → fsync → os.replace, matching existing persistence pattern).

**Cache content:**
```json
{
  "total": 5,
  "by_status": { "COMPLETED": 2, "RUNNING": 1, "PENDING": 2 },
  "active_count": 3,
  "quiescent_count": 2,
  "total_tokens": 125000,
  "last_activity": "2026-04-05T12:00:00Z",
  "computed_at": "2026-04-05T12:01:00Z"
}
```

**Staleness policy:** Configurable via `config/project.yaml`:
```yaml
rollup:
  staleness_threshold_seconds: 300  # default, adjustable based on operational observation
```

API checks `computed_at` age against threshold. If stale, recomputes from live mission_store query and refreshes cache.

**Conflict resolution:** If cached rollup disagrees with live mission query, live query wins and cache is refreshed. This is a derived cache, never canonical.

**Ownership:** `ProjectRollupHandler` owns the cache write path. API layer is read-only consumer.

### 5. API Surface — Phase 2 Additions

New endpoints added to `api/project_routes.py`:

```
POST   /api/projects/{id}/workspace/enable   → enable workspace (creates directories)
GET    /api/projects/{id}/workspace           → workspace metadata (paths, enabled status)

POST   /api/projects/{id}/artifacts           → publish artifact
GET    /api/projects/{id}/artifacts           → list published artifacts (filter: mission_id)
DELETE /api/projects/{id}/artifacts/{aid}     → unpublish artifact (remove project copy)

GET    /api/projects/{id}/rollup              → get rollup (cached or recomputed)
```

**Endpoint contracts:**

**POST /api/projects/{id}/workspace/enable**
- Request: `{}` (no body needed)
- Response: `201 Created` with workspace paths
- Error: `409` if already enabled, `404` if project not found, `403` if project status ∉ {`draft`, `active`}
- Rationale: workspace enable is a setup action. Paused projects should resume before structural changes. Completed/cancelled/archived projects are immutable — no new workspace creation.

**POST /api/projects/{id}/artifacts**
- Request: `{ "mission_id": "...", "artifact_id": "..." }`
- Response: `201 Created` with published artifact metadata (includes resolved path)
- Error: `404` if project/mission/artifact not found, `409` if workspace not enabled, `422` if mission not linked to project, `403` if project status ∉ {`draft`, `active`}
- Note: artifact source path resolved server-side from mission artifact registry. No caller-supplied path accepted.

**GET /api/projects/{id}/artifacts**
- Query params: `?mission_id=...` (optional filter)
- Response: `200` with array of published artifact metadata

**DELETE /api/projects/{id}/artifacts/{aid}**
- Response: `204 No Content`
- Error: `404` if not found, `403` if project status ∉ {`draft`, `active`}
- Rationale: inactive projects (paused/completed/cancelled/archived) have immutable artifact sets. Historical published artifacts are part of the audit/lineage record and must not be removed.

**GET /api/projects/{id}/rollup**
- Response: `200` with rollup JSON (cached or freshly computed)
- Includes `computed_at` and `stale` boolean for transparency

### 6. SSE Events — Phase 2 Additions

| Event | Payload | Trigger |
|---|---|---|
| `project_status_changed` | `{ project_id, old_status, new_status }` | Already in D-144, now broadcast via SSE |
| `project_rollup_updated` | `{ project_id, active_count, quiescent_count, total }` | Rollup cache refreshed by handler |
| `project_artifact_published` | `{ project_id, mission_id, artifact_id, path }` | Artifact published to project |
| `project_artifact_unpublished` | `{ project_id, artifact_id }` | Artifact removed from project |

**Consumer model:** SSE clients subscribe to existing SSE endpoint. Project events are broadcast alongside mission events. Client-side filtering by event type. No separate SSE channel for project events.

### 7. Dashboard UI — Phase 2 (Minimum Viable)

**Project list view:**
- Columns: name, status, mission count (active/quiescent), last activity
- Filter: status
- Sort: last activity, name

**Project detail view:**
- Header: name, status, owner, created/updated timestamps
- Mission list: linked missions with status badges
- Published artifacts: list with mission source, publish date
- Rollup summary: active/quiescent counts, total tokens

**Not in Phase 2:** dependency graph, objective mapping, timeline/replay, cross-mission blocked state. Those are Faz 3.

---

## What Is NOT In D-145

The following are explicitly deferred to Faz 3 (D-14X):

| Item | Rationale |
|---|---|
| Project defaults inheritance | Requires policy engine integration |
| Locked/unlocked defaults | Requires override constraint mechanism |
| Approval policy override rejection | Requires approval FSM awareness |
| Project budget envelope | Requires B-140 (mission budget enforcement) first |
| Cross-mission dependency graph | Requires objective model |
| Project replay / timeline | Requires cross-mission event correlation |

D-145 adds workspace and artifacts. It does not add governance constraints. Project cannot restrict or override mission behavior through D-145.

---

## Trade-off

| Accepted | Deferred |
|---|---|
| Explicit workspace enable (only on draft/active projects) | Auto-workspace on project create |
| Read-only project paths in WorkingSet | Write-through to project workspace |
| Explicit artifact publish (operator/API only, no hooks) | Auto-publish on mission complete |
| Configurable rollup staleness | Real-time rollup streaming |
| SSE on existing channel (client-side filter) | Dedicated project SSE channel |
| Minimal dashboard (list + detail) | Full project management UI |
| No policy inheritance | Faz 3: locked defaults, budget envelope |

---

## Impacted Files

| File | Change |
|---|---|
| `persistence/project_store.py` | **MODIFY** — workspace fields, enable_workspace() |
| `mission/controller.py` | **MODIFY** — `_build_default_working_set()` project-aware path injection |
| `api/project_routes.py` | **MODIFY** — 6 new endpoints |
| `events/event_types.py` | **MODIFY** — 3 new event types (artifact published, artifact unpublished, rollup updated) |
| `events/handlers/project_rollup_handler.py` | **NEW** — rollup cache handler |
| `api/sse_manager.py` | **MODIFY** — broadcast project events |
| `config/project.yaml` | **NEW** — rollup staleness config |
| Frontend: project views | **NEW** — list, detail, artifact browser |
| `tests/test_project_workspace.py` | **NEW** |
| `tests/test_artifact_publish.py` | **NEW** |
| `tests/test_project_rollup.py` | **NEW** |
| `tests/test_working_set_project.py` | **NEW** — project paths enforcement |
| `tests/test_project_sse.py` | **NEW** — SSE event emission + payload |

---

## Validation

| Check | Method |
|---|---|
| Workspace enable creates directories | test_project_workspace.py |
| Workspace enable idempotent (409 on re-enable) | test_project_workspace.py |
| Workspace enable rejected for paused/completed/cancelled/archived | test_project_workspace.py — 403 |
| WorkingSet includes project read_only paths for active project | test_working_set_project.py |
| WorkingSet does NOT include project write paths | test_working_set_project.py |
| WorkingSet injection skipped for inactive project | test_working_set_project.py |
| Artifact publish copies to correct location | test_artifact_publish.py |
| Artifact publish resolves path from mission store, not caller input | test_artifact_publish.py |
| Artifact publish rejected if workspace not enabled | test_artifact_publish.py |
| Artifact publish rejected if mission not linked | test_artifact_publish.py |
| Artifact publish rejected on inactive project (403) | test_artifact_publish.py |
| Artifact header gains project_id after publish | test_artifact_publish.py |
| Unpublish removes project copy, mission copy intact | test_artifact_publish.py |
| Unpublish rejected on paused/completed/cancelled/archived project (403) | test_artifact_publish.py |
| Rollup cache refreshed on mission state change | test_project_rollup.py |
| Stale rollup recomputed from live data | test_project_rollup.py |
| Rollup staleness threshold configurable | test_project_rollup.py |
| SSE events broadcast with correct payload (including rollup_updated) | test_project_sse.py |
| SSE project events coexist with mission events | test_project_sse.py |

---

## Rollback

Remove workspace fields from project.json. Revert `_build_default_working_set()` to pre-D-145. Delete rollup cache files. Remove project routes additions. Published artifact copies remain on disk but are no longer discoverable via API. No mission data affected.
