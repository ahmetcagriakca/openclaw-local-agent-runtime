"""Schedule management API — D-120 / B-101.

CRUD endpoints for mission schedules.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from schedules.store import ScheduleStore

logger = logging.getLogger("mcc.schedules_api")
router = APIRouter(tags=["schedules"])

_store: ScheduleStore | None = None


def _get_store() -> ScheduleStore:
    global _store
    if _store is None:
        _store = ScheduleStore()
    return _store


# ── Request/Response Models ──────────────────────────────────────

class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    template_id: str = Field(..., min_length=1)
    cron: str = Field(..., min_length=9, max_length=100,
                      description="Cron expression: minute hour day month weekday")
    timezone: str = Field(default="Europe/Istanbul")
    parameters: dict = Field(default_factory=dict)
    enabled: bool = Field(default=True)
    max_concurrent: int = Field(default=1, ge=1, le=10)


class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = None
    cron: Optional[str] = None
    timezone: Optional[str] = None
    parameters: Optional[dict] = None
    enabled: Optional[bool] = None
    max_concurrent: Optional[int] = Field(default=None, ge=1, le=10)


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/schedules")
async def list_schedules(enabled_only: bool = False):
    """List all mission schedules."""
    store = _get_store()
    schedules = store.list(enabled_only=enabled_only)
    return {"schedules": schedules, "total": len(schedules)}


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str):
    """Get a specific schedule."""
    store = _get_store()
    sched = store.get(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return sched.to_dict()


@router.post("/schedules", status_code=201)
async def create_schedule(body: CreateScheduleRequest):
    """Create a new mission schedule."""
    from schedules.schema import parse_cron
    from templates.store import TemplateStore

    # Validate cron expression
    try:
        parse_cron(body.cron)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid cron expression: {e}")

    # Validate template exists
    tmpl_store = TemplateStore()
    template = tmpl_store.get(body.template_id)
    if not template:
        raise HTTPException(status_code=400, detail=f"Template {body.template_id} not found")

    # Validate parameters against template
    errors = template.validate_params(body.parameters)
    if errors:
        raise HTTPException(status_code=400, detail=f"Parameter validation failed: {errors}")

    store = _get_store()
    sched = store.create(body.model_dump())
    logger.info("Schedule created via API: %s", sched.id)
    return sched.to_dict()


@router.put("/schedules/{schedule_id}")
async def update_schedule(schedule_id: str, body: UpdateScheduleRequest):
    """Update an existing schedule."""
    from schedules.schema import parse_cron

    # Validate cron if provided
    if body.cron is not None:
        try:
            parse_cron(body.cron)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid cron expression: {e}")

    store = _get_store()
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    sched = store.update(schedule_id, data)
    if not sched:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return sched.to_dict()


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule."""
    store = _get_store()
    if not store.delete(schedule_id):
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return {"deleted": True, "id": schedule_id}


@router.post("/schedules/{schedule_id}/run")
async def run_schedule_now(schedule_id: str):
    """Manually trigger a scheduled mission immediately."""
    store = _get_store()
    sched = store.get(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    import os
    from pathlib import Path

    from schedules.scheduler import MissionScheduler

    oc_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    missions_dir = oc_root / "logs" / "missions"

    scheduler = MissionScheduler(store, missions_dir)
    scheduler._execute_scheduled_mission(schedule_id, sched.template_id, sched.parameters)

    return {"triggered": True, "schedule_id": schedule_id}


@router.post("/schedules/{schedule_id}/toggle")
async def toggle_schedule(schedule_id: str):
    """Toggle a schedule's enabled/disabled state."""
    store = _get_store()
    sched = store.get(schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    sched = store.update(schedule_id, {"enabled": not sched.enabled})
    return {"id": schedule_id, "enabled": sched.enabled}
