"""Approval API — read-only (D-059). GPT Fix 3: wrapper responses."""
from fastapi import APIRouter, HTTPException

from api.schemas import ApprovalListResponse, ApprovalEntry, APIError

router = APIRouter(tags=["approvals"])


@router.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals():
    from api.server import normalizer
    approvals, meta = normalizer.list_approvals()
    return ApprovalListResponse(meta=meta, approvals=approvals)


@router.get("/approvals/{apv_id}", response_model=ApprovalEntry,
            responses={404: {"model": APIError}})
async def get_approval(apv_id: str):
    from api.server import normalizer
    result = normalizer.get_approval(apv_id)
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"Approval {apv_id} not found")
    entry, _ = result
    return entry
