"""Mission Mutation API — Sprint 11 Task 11.6.

POST /api/v1/missions/{id}/cancel
POST /api/v1/missions/{id}/retry

D-096 lifecycle: API writes signal artifact → returns lifecycleState=requested.
D-001: No direct service/method call. Atomic signal artifact only.
D-089: CSRF validated by middleware (Origin header).
D-090: Cancel is destructive — confirmation handled by frontend.
OD-10: Retry = new mission linked to failed original (controller handles).
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from api.mutation_audit import log_mutation
from api.mutation_bridge import has_pending_signal, write_signal_artifact
from api.schemas import APIError, MutationResponse

logger = logging.getLogger("mcc.mutation.mission")

router = APIRouter(tags=["mission-mutations"])

MUTATION_TIMEOUT_S = 10

# Valid FSM states for each mutation
CANCEL_VALID_STATES = {"pending", "planning", "executing", "gate_check",
                       "rework", "approval_wait"}
RETRY_VALID_STATES = {"failed", "aborted", "timed_out"}


def _get_dirs():
    """Get directory paths from server module."""
    from api.server import MISSIONS_DIR
    return MISSIONS_DIR


def _read_mission_state(missions_dir: Path, mission_id: str) -> dict | None:
    """Read mission state file. Returns None if not found.

    Checks both flat format ({id}-state.json) and directory format ({id}/state.json).
    """
    # Flat format: logs/missions/{mission_id}-state.json (controller default)
    flat_path = missions_dir / f"{mission_id}-state.json"
    if flat_path.exists():
        try:
            return json.loads(flat_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    # Directory format: logs/missions/{mission_id}/state.json (signal artifact layout)
    dir_path = missions_dir / mission_id / "state.json"
    if dir_path.exists():
        try:
            return json.loads(dir_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    # Fallback: read from main mission file
    mission_path = missions_dir / f"{mission_id}.json"
    if mission_path.exists():
        try:
            data = json.loads(mission_path.read_text(encoding="utf-8"))
            return {"state": data.get("status", "unknown")}
        except Exception:
            return None
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
async def cancel_mission(mission_id: str, request: Request):
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
            detail=f"Bu mission icin zaten bekleyen bir iptal istegi var. "
                   f"Onceki istek islenmeden yeni istek gonderilemez. "
                   f"Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
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
async def retry_mission(mission_id: str, request: Request):
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
            detail=f"Bu mission icin zaten bekleyen bir retry istegi var. "
                   f"Onceki istek islenmeden yeni istek gonderilemez. "
                   f"Mission detay sayfasindan bekleyen sinyali silebilirsiniz.",
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
