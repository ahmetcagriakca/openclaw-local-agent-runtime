"""Mission Mutation API — Sprint 11 Task 11.6 + Sprint 12 stage controls.

POST /api/v1/missions/{id}/cancel
POST /api/v1/missions/{id}/retry
POST /api/v1/missions/{id}/pause
POST /api/v1/missions/{id}/resume
POST /api/v1/missions/{id}/skip-stage

D-096 lifecycle: API writes signal artifact → returns lifecycleState=requested.
D-001: No direct service/method call. Atomic signal artifact only.
D-089: CSRF validated by middleware (Origin header).
D-090: Cancel is destructive — confirmation handled by frontend.
OD-10: Retry = new mission linked to failed original (controller handles).
"""
import json
import logging
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from auth.middleware import require_operator
from api.mutation_audit import log_mutation
from api.mutation_bridge import has_pending_signal, write_signal_artifact
from api.schemas import APIError, MutationResponse

logger = logging.getLogger("mcc.mutation.mission")

router = APIRouter(tags=["mission-mutations"])

MUTATION_TIMEOUT_S = 10

# Valid FSM states for each mutation
CANCEL_VALID_STATES = {"pending", "planning", "executing", "gate_check",
                       "rework", "approval_wait", "paused"}
RETRY_VALID_STATES = {"failed", "aborted", "timed_out"}
PAUSE_VALID_STATES = {"pending", "planning", "executing", "gate_check",
                      "rework", "approval_wait"}
RESUME_VALID_STATES = {"paused"}
SKIP_VALID_STATES = {"pending", "planning", "executing", "gate_check",
                     "rework", "approval_wait"}


def _get_dirs():
    """Get directory paths from server module."""
    from api.server import MISSIONS_DIR
    return MISSIONS_DIR


def _resolve_controller_id(missions_dir: Path, mission_id: str) -> str:
    """If mission_id is a dashboard placeholder, find the controller's real mission ID."""
    mission_path = missions_dir / f"{mission_id}.json"
    if not mission_path.exists():
        return mission_id
    try:
        data = json.loads(mission_path.read_text(encoding="utf-8"))
        # Direct link
        ctrl_id = data.get("controllerMissionId")
        if ctrl_id:
            return ctrl_id
        # Session-based link
        if data.get("createdFrom") == "dashboard":
            session_key = f"web-{mission_id}"
            for fpath in sorted(missions_dir.glob("mission-*.json"), reverse=True):
                base = fpath.name
                if "-state.json" in base or "-summary.json" in base:
                    continue
                if base == f"{mission_id}.json":
                    continue
                try:
                    d = json.loads(fpath.read_text(encoding="utf-8"))
                    if d.get("sessionId") == session_key:
                        return d.get("missionId", mission_id)
                except Exception:
                    continue
    except Exception:
        pass
    return mission_id


def _read_mission_data(missions_dir: Path, mission_id: str) -> dict | None:
    """Read the full mission JSON (not just state)."""
    real_id = _resolve_controller_id(missions_dir, mission_id)
    path = missions_dir / f"{real_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _run_retry_background(mission_id: str, failed_mission: dict,
                          missions_dir: Path):
    """Run retry mission via MissionController in background thread."""
    import os
    import sys

    try:
        agent_dir = str(Path(__file__).resolve().parent.parent)
        if agent_dir not in sys.path:
            sys.path.insert(0, agent_dir)
        os.chdir(agent_dir)

        from mission.controller import MissionController
        controller = MissionController()

        result = controller.execute_mission(
            goal=failed_mission.get("goal", ""),
            user_id="dashboard",
            session_id=f"web-retry-{mission_id}",
            retry_from_mission=failed_mission,
        )
        status = result.get("status", "unknown") if isinstance(result, dict) else "completed"
        logger.info("Retry mission for %s completed: status=%s", mission_id, status)
    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Retry mission for %s failed: %s\n%s", mission_id, e, tb)


def _read_mission_state(missions_dir: Path, mission_id: str) -> dict | None:
    """Read mission state file. Resolves dashboard placeholders to controller files."""
    # Resolve to controller's mission ID if this is a dashboard placeholder
    real_id = _resolve_controller_id(missions_dir, mission_id)

    # Flat format: logs/missions/{id}-state.json (controller default)
    flat_path = missions_dir / f"{real_id}-state.json"
    if flat_path.exists():
        try:
            return json.loads(flat_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    # Directory format: logs/missions/{id}/state.json (signal artifact layout)
    dir_path = missions_dir / real_id / "state.json"
    if dir_path.exists():
        try:
            return json.loads(dir_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    # Fallback: read from main mission file (use real_id first, then original)
    for mid in [real_id, mission_id]:
        mission_path = missions_dir / f"{mid}.json"
        if mission_path.exists():
            try:
                data = json.loads(mission_path.read_text(encoding="utf-8"))
                return {"state": data.get("status", "unknown")}
            except Exception:
                pass
    return None


def _extract_operator_info(request: Request) -> tuple[str, str]:
    """Extract tab ID and session ID from request headers."""
    tab_id = request.headers.get("x-tab-id", "")
    session_id = request.headers.get("x-session-id", "")
    return tab_id, session_id


async def _emit_mutation_requested(request: Request, request_id: str,
                                   target_id: str, mutation_type: str):
    """Best-effort SSE emit for mutation_requested."""
    try:
        sse_mgr = getattr(request.app.state, "sse_manager", None)
        if sse_mgr:
            await sse_mgr.broadcast("mutation_requested", {
                "requestId": request_id,
                "targetId": target_id,
                "type": mutation_type,
            })
    except Exception as e:
        logger.warning("Failed to emit mutation_requested SSE: %s", e)


@router.post(
    "/missions/{mission_id}/cancel",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def cancel_mission(mission_id: str, request: Request, _operator=Depends(require_operator)):
    """Cancel a running/active mission (D-090: destructive — requires confirmation).

    Valid states: pending, planning, executing, gate_check, rework, approval_wait.
    Completed/failed/aborted/timed_out → 409.
    """
    missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate mission state
    state_data = _read_mission_state(missions_dir, mission_id)
    if state_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")

    current_state = state_data.get("state") or state_data.get("status", "unknown")
    if current_state not in CANCEL_VALID_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Bu mission iptal edilemez — mevcut durum: '{current_state}'. "
                   f"Sadece aktif mission'lar iptal edilebilir ({', '.join(sorted(CANCEL_VALID_STATES))}).",
        )

    # 2. Check for pending duplicate
    existing = has_pending_signal(
        missions_dir, mission_id, "cancel", mission_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu mission icin zaten bekleyen bir iptal istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez. "
                   "Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
        )

    # 3. Write atomic signal artifact
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="cancel",
        target_id=mission_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="cancel",
        target_id=mission_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit
    await _emit_mutation_requested(request, request_id, mission_id, "cancel")

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=mission_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )


@router.post(
    "/missions/{mission_id}/retry",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def retry_mission(mission_id: str, request: Request, _operator=Depends(require_operator)):
    """Retry a failed/aborted mission (OD-10: creates new mission via controller).

    Valid states: failed, aborted, timed_out.
    Running/pending/completed → 409.
    """
    missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate mission state
    state_data = _read_mission_state(missions_dir, mission_id)
    if state_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")

    current_state = state_data.get("state") or state_data.get("status", "unknown")
    if current_state not in RETRY_VALID_STATES:
        state_label = {
            "completed": "basariyla tamamlanmis",
            "pending": "henuz baslatilmamis",
            "planning": "planlama asamasinda",
            "executing": "calisiyor",
        }.get(current_state, current_state)
        raise HTTPException(
            status_code=409,
            detail=f"Bu mission tekrar denenemez — mevcut durum: '{current_state}' ({state_label}). "
                   f"Sadece basarisiz mission'lar tekrar denenebilir ({', '.join(sorted(RETRY_VALID_STATES))}).",
        )

    # 2. Check for pending duplicate
    existing = has_pending_signal(
        missions_dir, mission_id, "retry", mission_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu mission icin zaten bekleyen bir retry istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez. "
                   "Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
        )

    # 3. Write atomic signal artifact
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="retry",
        target_id=mission_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="retry",
        target_id=mission_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit
    await _emit_mutation_requested(request, request_id, mission_id, "retry")

    # 5b. Spawn background thread to execute retry from checkpoint
    real_id = _resolve_controller_id(missions_dir, mission_id)
    failed_mission = _read_mission_data(missions_dir, real_id)
    if failed_mission:
        thread = threading.Thread(
            target=_run_retry_background,
            args=(mission_id, failed_mission, missions_dir),
            daemon=True,
            name=f"retry-{mission_id}",
        )
        thread.start()

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=mission_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )


@router.post(
    "/missions/{mission_id}/pause",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def pause_mission(mission_id: str, request: Request, _operator=Depends(require_operator)):
    """Pause a running mission — pauses after current stage completes.

    Valid states: pending, planning, executing, gate_check, rework, approval_wait.
    Already paused / completed / failed → 409.
    """
    missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate mission state
    state_data = _read_mission_state(missions_dir, mission_id)
    if state_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")

    current_state = state_data.get("state") or state_data.get("status", "unknown")
    if current_state not in PAUSE_VALID_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Bu mission duraklatılamaz — mevcut durum: '{current_state}'. "
                   f"Sadece aktif mission'lar duraklatılabilir ({', '.join(sorted(PAUSE_VALID_STATES))}).",
        )

    # 2. Check for pending duplicate
    existing = has_pending_signal(
        missions_dir, mission_id, "pause", mission_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu mission icin zaten bekleyen bir duraklat istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez. "
                   "Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
        )

    # 3. Write atomic signal artifact
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="pause",
        target_id=mission_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="pause",
        target_id=mission_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit
    await _emit_mutation_requested(request, request_id, mission_id, "pause")

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=mission_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )


@router.post(
    "/missions/{mission_id}/resume",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def resume_mission(mission_id: str, request: Request, _operator=Depends(require_operator)):
    """Resume a paused mission.

    Valid states: paused.
    Running / completed / failed → 409.
    """
    missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate mission state
    state_data = _read_mission_state(missions_dir, mission_id)
    if state_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")

    current_state = state_data.get("state") or state_data.get("status", "unknown")
    if current_state not in RESUME_VALID_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Bu mission devam ettirilemez — mevcut durum: '{current_state}'. "
                   f"Sadece duraklatılmış mission'lar devam ettirilebilir.",
        )

    # 2. Check for pending duplicate
    existing = has_pending_signal(
        missions_dir, mission_id, "resume", mission_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu mission icin zaten bekleyen bir devam istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez. "
                   "Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
        )

    # 3. Write atomic signal artifact
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="resume",
        target_id=mission_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="resume",
        target_id=mission_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit
    await _emit_mutation_requested(request, request_id, mission_id, "resume")

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=mission_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )


@router.post(
    "/missions/{mission_id}/skip-stage",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def skip_stage(mission_id: str, request: Request, _operator=Depends(require_operator)):
    """Skip the current stage in a running mission.

    Valid states: pending, planning, executing, gate_check, rework, approval_wait.
    Paused / completed / failed → 409.
    """
    missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate mission state
    state_data = _read_mission_state(missions_dir, mission_id)
    if state_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")

    current_state = state_data.get("state") or state_data.get("status", "unknown")
    if current_state not in SKIP_VALID_STATES:
        raise HTTPException(
            status_code=409,
            detail=f"Bu mission'da aşama atlanamaz — mevcut durum: '{current_state}'. "
                   f"Sadece aktif mission'larda aşama atlanabilir ({', '.join(sorted(SKIP_VALID_STATES))}).",
        )

    # 2. Check for pending duplicate
    existing = has_pending_signal(
        missions_dir, mission_id, "skip-stage", mission_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu mission icin zaten bekleyen bir aşama atlama istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez. "
                   "Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
        )

    # 3. Write atomic signal artifact
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="skip-stage",
        target_id=mission_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="skip-stage",
        target_id=mission_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit
    await _emit_mutation_requested(request, request_id, mission_id, "skip-stage")

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=mission_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )
