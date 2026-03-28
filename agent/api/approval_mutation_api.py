"""Approval Mutation API — Sprint 11 Task 11.5.

POST /api/v1/approvals/{id}/approve
POST /api/v1/approvals/{id}/reject

D-096 lifecycle: API writes signal artifact → returns lifecycleState=requested.
D-001: No direct service/method call. Atomic signal artifact only.
D-089: CSRF validated by middleware (Origin header).
D-090: Destructive action (reject) — confirmation handled by frontend.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from auth.middleware import require_operator
from api.mutation_audit import log_mutation
from api.mutation_bridge import has_pending_signal, write_signal_artifact
from api.schemas import APIError, MutationResponse

logger = logging.getLogger("mcc.mutation.approval")

router = APIRouter(tags=["approval-mutations"])

# D-096: Timeout window for mutation lifecycle
MUTATION_TIMEOUT_S = 10


def _get_dirs():
    """Get directory paths from server module."""
    from api.server import APPROVALS_DIR, MISSIONS_DIR
    return APPROVALS_DIR, MISSIONS_DIR


def _read_approval(approvals_dir: Path, apv_id: str) -> dict | None:
    """Read an approval JSON file. Returns None if not found."""
    fpath = approvals_dir / f"{apv_id}.json"
    if not fpath.exists():
        return None
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return None


def _validate_approval_for_mutation(
    approval_data: dict, apv_id: str, operation: str,
) -> None:
    """Validate approval is in correct FSM state for mutation.

    Raises HTTPException(409) if state is invalid.
    """
    status = approval_data.get("status", "unknown")
    if status != "pending":
        op_label = {"approve": "onaylanamaz", "reject": "reddedilemez"}.get(operation, operation)
        status_label = {"approved": "zaten onaylanmis", "denied": "zaten reddedilmis",
                        "timeout": "zaman asimina ugramis"}.get(status, status)
        raise HTTPException(
            status_code=409,
            detail=f"Bu approval {op_label} — mevcut durum: '{status}' ({status_label}). "
                   f"Sadece 'pending' durumundaki approval'lar islem gorebilir.",
        )


def _extract_operator_info(request: Request) -> tuple[str, str]:
    """Extract tab ID and session ID from request headers."""
    tab_id = request.headers.get("x-tab-id", "")
    session_id = request.headers.get("x-session-id", "")
    return tab_id, session_id


async def _emit_mutation_requested(request: Request, request_id: str,
                                   target_id: str, mutation_type: str):
    """Best-effort SSE emit for mutation_requested (D-096 ordering rule)."""
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
    "/approvals/{apv_id}/approve",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def approve_approval(apv_id: str, request: Request, _operator=Depends(require_operator)):
    """Approve a pending approval.

    Signal flow: validate → check duplicate → write artifact → SSE → respond.
    """
    approvals_dir, missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate approval
    approval_data = _read_approval(approvals_dir, apv_id)
    if approval_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Approval {apv_id} not found")

    _validate_approval_for_mutation(approval_data, apv_id, "approve")

    mission_id = approval_data.get("missionId", "unknown")

    # 2. Check for pending duplicate (Test 5: 409)
    existing = has_pending_signal(missions_dir, mission_id, "approve", apv_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu approval icin zaten bekleyen bir onay istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez.",
        )

    # 3. Write atomic signal artifact (D-001: no direct service call)
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="approve",
        target_id=apv_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="approve",
        target_id=apv_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit (D-096 ordering: artifact → SSE → response)
    await _emit_mutation_requested(request, request_id, apv_id, "approve")

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=apv_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )


@router.post(
    "/approvals/{apv_id}/reject",
    response_model=MutationResponse,
    responses={404: {"model": APIError}, 409: {"model": APIError}},
)
async def reject_approval(apv_id: str, request: Request, _operator=Depends(require_operator)):
    """Reject a pending approval (D-090: destructive — requires confirmation).

    Signal flow: validate → check duplicate → write artifact → SSE → respond.
    """
    approvals_dir, missions_dir = _get_dirs()
    tab_id, session_id = _extract_operator_info(request)

    # 1. Read and validate approval
    approval_data = _read_approval(approvals_dir, apv_id)
    if approval_data is None:
        raise HTTPException(status_code=404,
                            detail=f"Approval {apv_id} not found")

    _validate_approval_for_mutation(approval_data, apv_id, "reject")

    mission_id = approval_data.get("missionId", "unknown")

    # 2. Check for pending duplicate
    existing = has_pending_signal(missions_dir, mission_id, "reject", apv_id)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Bu approval icin zaten bekleyen bir red istegi var. "
                   "Onceki istek islenmeden yeni istek gonderilemez.",
        )

    # 3. Write atomic signal artifact
    request_id, requested_at, artifact_path = write_signal_artifact(
        missions_dir=missions_dir,
        mutation_type="reject",
        target_id=apv_id,
        mission_id=mission_id,
        tab_id=tab_id,
        session_id=session_id,
    )

    # 4. Audit log
    log_mutation(
        request_id=request_id,
        operation="reject",
        target_id=apv_id,
        outcome="requested",
        tab_id=tab_id,
        session_id=session_id,
    )

    # 5. SSE best-effort emit
    await _emit_mutation_requested(request, request_id, apv_id, "reject")

    # 6. Return D-096 lifecycle response
    timeout_at = (
        datetime.fromisoformat(requested_at)
        + timedelta(seconds=MUTATION_TIMEOUT_S)
    ).isoformat()

    return MutationResponse(
        requestId=request_id,
        lifecycleState="requested",
        targetId=apv_id,
        requestedAt=requested_at,
        timeoutAt=timeout_at,
    )
