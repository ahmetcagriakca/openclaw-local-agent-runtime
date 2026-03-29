"""Templates API — D-119.

CRUD for mission templates + run-from-template.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth.middleware import require_operator
from templates.store import TemplateStore

logger = logging.getLogger("mcc.api.templates")

router = APIRouter(prefix="/templates", tags=["templates"])

_store: Optional[TemplateStore] = None


def _get_store() -> TemplateStore:
    global _store
    if _store is None:
        _store = TemplateStore()
    return _store


class CreateTemplateRequest(BaseModel):
    name: str
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    parameters: list[dict] = []
    mission_config: dict = {}


class UpdateTemplateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None


class RunTemplateRequest(BaseModel):
    parameters: dict = {}


def _meta():
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "dataQuality": "fresh",
    }


@router.get("")
async def list_templates():
    """List all templates."""
    store = _get_store()
    return {"meta": _meta(), "data": store.list()}


@router.get("/presets")
async def list_presets():
    """List built-in mission presets for quick-run.

    B-103: Presets are published templates marked for quick access.
    Returns templates with status=published, sorted by name.
    """
    store = _get_store()
    all_templates = store.list()
    presets = [t for t in all_templates if t.get("status") == "published"]
    presets.sort(key=lambda t: t.get("name", ""))
    return {"meta": _meta(), "presets": presets, "total": len(presets)}


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get template by ID."""
    store = _get_store()
    tmpl = store.get(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return {"meta": _meta(), "data": tmpl.to_dict()}


@router.post("", status_code=201)
async def create_template(body: CreateTemplateRequest, _op=Depends(require_operator)):
    """Create a new template (operator only)."""
    store = _get_store()
    tmpl = store.create(body.model_dump())
    return {"meta": _meta(), "data": tmpl.to_dict()}


@router.put("/{template_id}")
async def update_template(template_id: str, body: UpdateTemplateRequest, _op=Depends(require_operator)):
    """Update template (operator only)."""
    store = _get_store()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    tmpl = store.update(template_id, updates)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return {"meta": _meta(), "data": tmpl.to_dict()}


@router.delete("/{template_id}")
async def delete_template(template_id: str, _op=Depends(require_operator)):
    """Delete template (operator only)."""
    store = _get_store()
    if not store.delete(template_id):
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    return {"meta": _meta(), "deleted": True}


@router.post("/{template_id}/run", status_code=201)
async def run_template(template_id: str, body: RunTemplateRequest, request: Request,
                       _op=Depends(require_operator)):
    """Create and run a mission from template (operator only).

    B-103: Quick-run — renders goal from template parameters and
    spawns a real mission via the mission create pipeline.
    """
    store = _get_store()
    tmpl = store.get(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    if tmpl.status != "published":
        raise HTTPException(status_code=400, detail=f"Template is {tmpl.status}, must be published to run")

    errors = tmpl.validate_params(body.parameters)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    goal = tmpl.render_goal(body.parameters)

    # B-103: Actually create and execute the mission
    from api.mission_create_api import _get_dirs, _generate_mission_id, _run_mission_background
    from utils.atomic_write import atomic_write_json
    import threading

    missions_dir = _get_dirs()
    mission_id = _generate_mission_id()
    now = datetime.now(timezone.utc).isoformat()

    mission_data = {
        "missionId": mission_id,
        "status": "pending",
        "goal": goal,
        "complexity": tmpl.mission_config.specialist,
        "stages": [],
        "startedAt": now,
        "createdFrom": f"template:{template_id}",
    }

    mission_file = missions_dir / f"{mission_id}.json"
    atomic_write_json(mission_file, mission_data)
    logger.info("Quick-run mission created: %s template=%s", mission_id, template_id)

    # Emit SSE
    try:
        sse_mgr = getattr(request.app.state, "sse_manager", None)
        if sse_mgr:
            await sse_mgr.broadcast("mission_list_changed", {
                "missionId": mission_id,
                "action": "created",
                "source": f"template:{template_id}",
            })
    except Exception:
        pass

    # Start execution
    thread = threading.Thread(
        target=_run_mission_background,
        args=(mission_id, goal, missions_dir),
        daemon=True,
        name=f"tmpl-mission-{mission_id}",
    )
    thread.start()

    return {
        "meta": _meta(),
        "data": {
            "missionId": mission_id,
            "template_id": template_id,
            "goal": goal,
            "specialist": tmpl.mission_config.specialist,
            "provider": tmpl.mission_config.provider,
            "status": "pending",
        },
    }
