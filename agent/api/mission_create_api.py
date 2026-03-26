"""Mission Create API — create new missions from the dashboard.

POST /api/v1/missions — create a new mission with a goal.
Creates mission JSON in logs/missions/ so it appears in the UI via file watcher.
Optionally spawns the MissionController in a background thread for execution.
"""
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from api.schemas import ResponseMeta, DataQuality
from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.mission.create")

router = APIRouter(tags=["mission-create"])


class CreateMissionRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    complexity: str = Field(default="medium")


class CreateMissionResponse(BaseModel):
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    missionId: str
    state: str
    goal: str


def _get_dirs():
    from api.server import MISSIONS_DIR
    return MISSIONS_DIR


def _generate_mission_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"mission-{ts}-{short}"


def _run_mission_background(mission_id: str, goal: str, missions_dir: Path):
    """Attempt to run the mission in background via MissionController."""
    try:
        import sys
        agent_dir = str(Path(__file__).resolve().parent.parent)
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)

        from mission.controller import MissionController
        controller = MissionController()
        result = controller.execute_mission(
            goal=goal,
            user_id="dashboard",
            session_id=f"web-{mission_id}",
        )
        logger.info("Mission %s completed: %s", mission_id, result.get("status", "unknown"))
    except Exception as e:
        logger.error("Mission %s background execution failed: %s", mission_id, e)
        # Update mission state to failed
        try:
            mission_file = missions_dir / f"{mission_id}.json"
            if mission_file.exists():
                data = json.loads(mission_file.read_text(encoding="utf-8"))
                data["status"] = "failed"
                data["error"] = str(e)
                data["completedAt"] = datetime.now(timezone.utc).isoformat()
                atomic_write_json(mission_file, data)
        except Exception:
            pass


@router.post(
    "/missions",
    response_model=CreateMissionResponse,
    status_code=201,
)
async def create_mission(body: CreateMissionRequest, request: Request):
    """Create a new mission.

    Writes mission JSON to logs/missions/ so it appears immediately in the UI.
    Spawns MissionController in a background thread for execution.
    """
    missions_dir = _get_dirs()
    mission_id = _generate_mission_id()
    now = datetime.now(timezone.utc).isoformat()

    mission_data = {
        "missionId": mission_id,
        "status": "pending",
        "goal": body.goal,
        "complexity": body.complexity,
        "stages": [],
        "startedAt": now,
        "createdFrom": "dashboard",
    }

    mission_file = missions_dir / f"{mission_id}.json"
    atomic_write_json(mission_file, mission_data)
    logger.info("Mission created: %s goal=%s", mission_id, body.goal[:80])

    # Emit SSE event for immediate UI update
    try:
        sse_mgr = getattr(request.app.state, "sse_manager", None)
        if sse_mgr:
            await sse_mgr.broadcast("mission_list_changed", {
                "missionId": mission_id,
                "action": "created",
            })
    except Exception as e:
        logger.warning("Failed to emit mission_created SSE: %s", e)

    # Start mission execution in background thread
    thread = threading.Thread(
        target=_run_mission_background,
        args=(mission_id, body.goal, missions_dir),
        daemon=True,
        name=f"mission-{mission_id}",
    )
    thread.start()

    meta = ResponseMeta(dataQuality=DataQuality.FRESH)
    return CreateMissionResponse(
        meta=meta,
        missionId=mission_id,
        state="pending",
        goal=body.goal,
    )
