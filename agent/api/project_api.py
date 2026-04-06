"""Project API — D-144 §7, D-145 §5.

13 REST endpoints: create, list, detail, update, delete, link, unlink,
workspace enable, workspace get, artifact publish, artifact list,
artifact unpublish.
Error responses: 409 (active missions, lifecycle), 422 (invalid FSM), 404, 403.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from persistence.project_store import (
    ActiveMissionsError,
    InvalidTransitionError,
    ProjectLifecycleError,
    ProjectStore,
    ProjectStoreError,
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


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


def _meta():
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dataQuality": "fresh",
    }


# ── Endpoints ────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_project(req: CreateProjectRequest):
    """Create a new project (starts in draft status)."""
    store = _get_store()
    project = store.create(
        name=req.name,
        description=req.description,
        owner=req.owner,
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
    return {
        "meta": _meta(),
        "data": {
            "project": project,
            "mission_summary": mission_summary,
        },
    }


@router.patch("/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest):
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

    if updates:
        try:
            project = store.update(project_id, **updates)
        except ProjectStoreError as e:
            raise HTTPException(status_code=404, detail=str(e))

    return {"meta": _meta(), "data": project}


@router.delete("/{project_id}")
async def delete_project(project_id: str):
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
async def link_mission(project_id: str, mission_id: str):
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
async def unlink_mission(project_id: str, mission_id: str):
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
async def enable_workspace(project_id: str):
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
async def publish_artifact(project_id: str, req: PublishArtifactRequest):
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
async def unpublish_artifact(project_id: str, artifact_id: str):
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
