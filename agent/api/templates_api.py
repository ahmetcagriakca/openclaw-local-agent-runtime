"""Templates API — D-119.

CRUD for mission templates + run-from-template.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
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
async def run_template(template_id: str, body: RunTemplateRequest, _op=Depends(require_operator)):
    """Create and run a mission from template (operator only)."""
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

    return {
        "meta": _meta(),
        "data": {
            "template_id": template_id,
            "goal": goal,
            "specialist": tmpl.mission_config.specialist,
            "provider": tmpl.mission_config.provider,
            "status": "created",
        },
    }
