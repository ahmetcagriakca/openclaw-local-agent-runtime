"""Mission Create API — create new missions from the dashboard.

POST /api/v1/missions — create a new mission with a goal.
Creates mission JSON in logs/missions/ so it appears in the UI via file watcher.
Spawns the MissionController in a background thread for execution.
"""
import json
import logging
import os
import threading
import traceback
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
    """Run mission via MissionController in background thread.

    The controller creates its own mission files with its own ID.
    We update the dashboard-created placeholder file to track progress.
    """
    placeholder_file = missions_dir / f"{mission_id}.json"

    try:
        import sys
        # __file__ = agent/api/mission_create_api.py → parent.parent = agent/
        agent_dir = str(Path(__file__).resolve().parent.parent)
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        os.chdir(agent_dir)
        logger.info("Mission %s bg thread: cwd=%s agent_dir=%s", mission_id, os.getcwd(), agent_dir)

        # Update placeholder to "planning"
        _update_placeholder(placeholder_file, "planning", None)

        from mission.controller import MissionController
        controller = MissionController()

        # Controller generates ID as mission-{timestamp}-{pid}
        # We can predict it by looking at newly created files after execute starts
        # But simpler: scan for files matching session after a brief delay
        result = controller.execute_mission(
            goal=goal,
            user_id="dashboard",
            session_id=f"web-{mission_id}",
        )

        # Update placeholder with result and link to controller's real mission
        if isinstance(result, dict):
            status = result.get("status", "unknown")
            error = result.get("error")
            ctrl_id = result.get("missionId", "")
        else:
            status = "completed"
            error = None
            ctrl_id = ""
        _update_placeholder(placeholder_file, status, error,
                            finished=True,
                            controller_id=ctrl_id)

        logger.info("Mission %s completed: status=%s", mission_id, status)

    except Exception as e:
        tb = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {e}"
        logger.error("Mission %s failed: %s\n%s", mission_id, error_msg, tb)
        _update_placeholder(placeholder_file, "failed", error_msg, finished=True)


def _update_placeholder(path: Path, status: str, error: str | None,
                        finished: bool = False, controller_id: str | None = None):
    """Update the dashboard-created placeholder mission file."""
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {}
        data["status"] = status
        if error:
            data["error"] = error
        if finished:
            data["finishedAt"] = datetime.now(timezone.utc).isoformat()
        if controller_id:
            data["controllerMissionId"] = controller_id
        atomic_write_json(path, data)
    except Exception as e:
        logger.warning("Failed to update placeholder %s: %s", path, e)


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
