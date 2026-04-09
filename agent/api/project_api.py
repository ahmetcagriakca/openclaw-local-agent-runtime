"""Project API — D-144 §7, D-145 §5, D-151.

17 REST endpoints: create, list, detail, update, delete, link, unlink,
workspace enable, workspace get, artifact publish, artifact list,
artifact unpublish, rollup, github get, github bind, github sync, github comment.
Error responses: 409 (active missions, lifecycle), 422 (invalid FSM), 404, 403, 502.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth.keys import ApiKey
from auth.middleware import require_operator
from events.bus import Event
from events.catalog import EventType
from persistence.project_store import (
    ActiveMissionsError,
    InvalidTransitionError,
    ProjectLifecycleError,
    ProjectStore,
    ProjectStoreError,
)
from services.github_project_service import (
    GitHubProjectService,
    GitHubProjectServiceError,
)

logger = logging.getLogger("mcc.api.projects")

router = APIRouter(prefix="/projects", tags=["projects"])

_store: Optional[ProjectStore] = None


def _get_store() -> ProjectStore:
    global _store
    if _store is None:
        _store = ProjectStore()
    return _store


def set_store(store: ProjectStore) -> None:
    """Set project store instance (for testing / DI)."""
    global _store
    _store = store


# ── Request Models ───────────────────────────────────────────────


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    owner: str = "operator"
    local_path: Optional[str] = None


class BindGitHubRequest(BaseModel):
    repo_full_name: str
    issue_number: Optional[int] = None
    pr_number: Optional[int] = None


class PublishGitHubCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=65536)


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    local_path: Optional[str] = None


def _meta():
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dataQuality": "fresh",
    }


# ── GitHub actor helpers (D-151) ─────────────────────────────────


def _default_actor_identity() -> dict:
    return {
        "user_id": "ahmetcagriakca",
        "username": "ahmetcagriakca",
        "display_name": "Ahmet \u00c7a\u011fr\u0131 AKCA",
        "provider": "github",
    }


def _actor_identity(user: ApiKey | None) -> dict:
    if user is None:
        return _default_actor_identity()

    username = (user.user_id or user.name or "ahmetcagriakca").strip()
    if not username:
        username = "ahmetcagriakca"

    return {
        "user_id": (user.user_id or username).strip() or "ahmetcagriakca",
        "username": username,
        "display_name": "Ahmet \u00c7a\u011fr\u0131 AKCA",
        "provider": "github",
    }


def _emit_project_event(request: Request, event_type: str, data: dict) -> None:
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus is None:
        return
    event_bus.emit(Event(type=event_type, data=data, source="api.project_api"))


# ── Endpoints ────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_project(req: CreateProjectRequest, _operator=Depends(require_operator)):
    """Create a new project (starts in draft status)."""
    store = _get_store()
    project = store.create(
        name=req.name,
        description=req.description,
        owner=req.owner,
        local_path=req.local_path,
    )
    return {"meta": _meta(), "data": project}


@router.get("")
async def list_projects(
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "updated_at_desc",
    limit: int = 50,
    offset: int = 0,
):
    """List projects with optional filters."""
    store = _get_store()
    status_filter = [s.strip() for s in status.split(",")] if status else None
    projects, total = store.list(
        status=status_filter,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "meta": _meta(),
        "data": projects,
        "total": total,
    }


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get project detail with derived mission summary."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    mission_summary = store.get_mission_summary(project_id)
    github_state = store.get_github(project_id)
    return {
        "meta": _meta(),
        "data": {
            "project": project,
            "mission_summary": mission_summary,
            "github": github_state,
        },
    }


@router.patch("/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest, _operator=Depends(require_operator)):
    """Update project fields and/or transition status."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    # Handle status transition separately
    if req.status is not None:
        try:
            project = store.transition_status(project_id, req.status)
        except InvalidTransitionError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ActiveMissionsError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": str(e),
                    "active_mission_ids": e.mission_ids,
                },
            )

    # Handle other field updates
    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.description is not None:
        updates["description"] = req.description
    if req.local_path is not None:
        from pathlib import Path as PPath
        resolved = PPath(req.local_path).resolve()
        if not resolved.is_dir():
            raise HTTPException(status_code=422, detail=f"Path does not exist: {req.local_path}")
        updates["local_path"] = str(resolved)
        updates["workspace_root"] = str(resolved)

    if updates:
        try:
            project = store.update(project_id, **updates)
        except ProjectStoreError as e:
            raise HTTPException(status_code=404, detail=str(e))

    return {"meta": _meta(), "data": project}


@router.delete("/{project_id}")
async def delete_project(project_id: str, _operator=Depends(require_operator)):
    """Soft-delete a project (sets status to cancelled).

    D-144 §5: Only draft/active/paused. Reject completed/archived.
    Reject if active missions linked.
    """
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        project = store.delete(project_id)
    except ActiveMissionsError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(e),
                "active_mission_ids": e.mission_ids,
            },
        )
    except ProjectLifecycleError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"meta": _meta(), "data": project}


@router.post("/{project_id}/missions/{mission_id}", status_code=200)
async def link_mission(project_id: str, mission_id: str, _operator=Depends(require_operator)):
    """Link a mission to a project.

    D-144 §5: Only draft/active projects accept links.
    """
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        store.link_mission(project_id, mission_id)
    except ProjectLifecycleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ProjectStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"meta": _meta(), "data": {"linked": True}}


@router.delete("/{project_id}/missions/{mission_id}")
async def unlink_mission(project_id: str, mission_id: str, _operator=Depends(require_operator)):
    """Unlink a mission from a project.

    D-144 §5: Only draft/active/paused. Historical links preserved.
    """
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        store.unlink_mission(project_id, mission_id)
    except ProjectLifecycleError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ProjectStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"meta": _meta(), "data": {"unlinked": True}}


# ── Workspace (D-145 §5) ──────────────────────────────────────────


@router.post("/{project_id}/workspace/enable", status_code=201)
async def enable_workspace(project_id: str, _operator=Depends(require_operator)):
    """Enable workspace for a project. Creates directory structure.

    D-145 §5: 409 if already enabled, 404 if not found,
    403 if project status not in {draft, active}.
    """
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        project = store.enable_workspace(project_id)
    except ProjectLifecycleError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ProjectStoreError as e:
        if "already enabled" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "meta": _meta(),
        "data": {
            "workspace_root": project.get("workspace_root"),
            "artifact_root": project.get("artifact_root"),
            "shared_root": project.get("shared_root"),
        },
    }


@router.get("/{project_id}/workspace")
async def get_workspace(project_id: str):
    """Get workspace metadata for a project."""
    store = _get_store()
    workspace = store.get_workspace(project_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"meta": _meta(), "data": workspace}


# ── Rollup (D-145 Faz 2B) ────────────────────────────────────────


@router.get("/{project_id}/rollup")
async def get_rollup(project_id: str):
    """Get rollup summary for a project (staleness-aware cache)."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        rollup = store.get_rollup(project_id)
    except ProjectStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"meta": _meta(), "data": rollup}


# ── Artifacts (D-145 §5) ──────────────────────────────────────────


class PublishArtifactRequest(BaseModel):
    mission_id: str
    artifact_id: str


@router.post("/{project_id}/artifacts", status_code=201)
async def publish_artifact(project_id: str, req: PublishArtifactRequest, _operator=Depends(require_operator)):
    """Publish a mission artifact to project space.

    D-145 §5: 404 if not found, 409 if workspace not enabled,
    422 if mission not linked, 403 if project inactive.
    """
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        entry = store.publish_artifact(
            project_id, req.mission_id, req.artifact_id)
    except ProjectLifecycleError as e:
        if "not linked" in str(e):
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ProjectStoreError as e:
        if "not enabled" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

    return {"meta": _meta(), "data": entry}


@router.get("/{project_id}/artifacts")
async def list_artifacts(
    project_id: str,
    mission_id: Optional[str] = None,
):
    """List published artifacts for a project."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        artifacts = store.list_artifacts(project_id, mission_id=mission_id)
    except ProjectStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"meta": _meta(), "data": artifacts}


@router.delete("/{project_id}/artifacts/{artifact_id}", status_code=204)
async def unpublish_artifact(project_id: str, artifact_id: str, _operator=Depends(require_operator)):
    """Unpublish (remove) an artifact from project space.

    D-145 §5: 404 if not found, 403 if project inactive.
    """
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        entry = store.unpublish_artifact(project_id, artifact_id)
    except ProjectLifecycleError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ProjectStoreError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if entry is None:
        raise HTTPException(status_code=404, detail="Artifact not found")


# ── GitHub surface (D-151) ───────────────────────────────────────


@router.get("/{project_id}/github")
async def get_project_github(project_id: str):
    """Get GitHub binding, activity, and last sync time for a project."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"meta": _meta(), "data": store.get_github(project_id)}


@router.post("/{project_id}/github/bind", status_code=201)
async def bind_project_github(
    project_id: str,
    req: BindGitHubRequest,
    request: Request,
    operator: ApiKey | None = Depends(require_operator),
):
    """Bind a GitHub issue or PR thread to this project."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    actor = _actor_identity(operator)
    try:
        binding = store.bind_github(
            project_id,
            req.repo_full_name,
            issue_number=req.issue_number,
            pr_number=req.pr_number,
            bound_by=actor,
        )
    except ProjectStoreError as e:
        raise HTTPException(status_code=422, detail=str(e))

    _emit_project_event(
        request,
        EventType.PROJECT_GITHUB_BOUND,
        {
            "project_id": project_id,
            "repo_full_name": binding["repo_full_name"],
            "thread_number": binding["thread_number"],
            "issue_number": binding.get("issue_number"),
            "pr_number": binding.get("pr_number"),
            "actor": actor["username"],
            "display_name": actor["display_name"],
        },
    )
    return {"meta": _meta(), "data": binding}


@router.post("/{project_id}/github/sync")
async def sync_project_github(
    project_id: str,
    request: Request,
    operator: ApiKey | None = Depends(require_operator),
):
    """Sync GitHub thread activity into this project."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    github_state = store.get_github(project_id)
    binding = github_state.get("binding")
    if not binding:
        raise HTTPException(status_code=409, detail="Project has no GitHub binding")

    service = GitHubProjectService()
    try:
        sync_result = service.sync_binding(binding)
        snapshot = store.sync_github_activity(project_id, sync_result)
    except GitHubProjectServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ProjectStoreError as e:
        raise HTTPException(status_code=400, detail=str(e))

    actor = _actor_identity(operator)
    _emit_project_event(
        request,
        EventType.PROJECT_GITHUB_SYNCED,
        {
            "project_id": project_id,
            "repo_full_name": binding["repo_full_name"],
            "thread_number": binding["thread_number"],
            "activity_count": len(snapshot["activity"]),
            "fetched_at": snapshot["last_sync_at"],
            "actor": actor["username"],
            "display_name": actor["display_name"],
        },
    )
    return {"meta": _meta(), "data": snapshot}


@router.post("/{project_id}/github/comment", status_code=201)
async def publish_project_github_comment(
    project_id: str,
    req: PublishGitHubCommentRequest,
    request: Request,
    operator: ApiKey | None = Depends(require_operator),
):
    """Publish a comment to the bound GitHub thread."""
    store = _get_store()
    project = store.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    github_state = store.get_github(project_id)
    binding = github_state.get("binding")
    if not binding:
        raise HTTPException(status_code=409, detail="Project has no GitHub binding")

    thread_number = binding.get("issue_number") or binding.get("pr_number")
    if thread_number is None:
        raise HTTPException(status_code=409, detail="GitHub binding has no thread number")

    service = GitHubProjectService()
    actor = _actor_identity(operator)

    try:
        remote_comment = service.post_issue_comment(
            binding["repo_full_name"],
            int(thread_number),
            req.body,
        )
    except GitHubProjectServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    activity_entry = {
        "activity_id": f"issue_comment:{remote_comment['id']}",
        "kind": "issue_comment",
        "direction": "outbound",
        "repo_full_name": binding["repo_full_name"],
        "thread_number": int(thread_number),
        "author": actor["username"],
        "display_name": actor["display_name"],
        "body": remote_comment.get("body") or req.body.strip(),
        "created_at": remote_comment.get("created_at"),
        "updated_at": remote_comment.get("updated_at"),
        "html_url": remote_comment.get("html_url"),
        "comment_id": remote_comment.get("id"),
    }
    store.append_github_activity(project_id, activity_entry)

    _emit_project_event(
        request,
        EventType.PROJECT_GITHUB_COMMENT_PUBLISHED,
        {
            "project_id": project_id,
            "repo_full_name": binding["repo_full_name"],
            "thread_number": int(thread_number),
            "comment_id": remote_comment.get("id"),
            "actor": actor["username"],
            "display_name": actor["display_name"],
            "html_url": remote_comment.get("html_url"),
        },
    )
    return {"meta": _meta(), "data": activity_entry}
