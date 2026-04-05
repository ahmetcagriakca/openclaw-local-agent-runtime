"""Secret rotation API — B-007.

Endpoints for rotation status, schedule, and policy management.
Rotation trigger requires operator confirmation (escalation pattern).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.middleware import require_operator
from services.secret_rotation import (
    SecretRotationError,
    SecretRotationService,
)

logger = logging.getLogger("mcc.api.secret_rotation")
router = APIRouter(tags=["secret-rotation"])

# Singleton service instance
_rotation_service = SecretRotationService()


class PolicyUpdateRequest(BaseModel):
    max_age_days: Optional[int] = None
    warning_threshold_days: Optional[int] = None
    auto_rotate: Optional[bool] = None


@router.get("/secrets/rotation/status")
def get_rotation_status():
    """Get current secret rotation status."""
    try:
        return _rotation_service.status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secrets/rotation/schedule")
def get_rotation_schedule():
    """Get rotation schedule and policy."""
    try:
        return _rotation_service.get_schedule()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secrets/rotation/check")
def check_rotation_due():
    """Check if rotation is due."""
    try:
        due = _rotation_service.check_due()
        return {"rotation_due": due, "status": _rotation_service.status()["status"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/secrets/rotation/policy")
def update_rotation_policy(req: PolicyUpdateRequest, _operator=Depends(require_operator)):
    """Update rotation policy parameters."""
    try:
        policy = _rotation_service.update_policy(
            max_age_days=req.max_age_days,
            warning_threshold_days=req.warning_threshold_days,
            auto_rotate=req.auto_rotate,
        )
        return {
            "max_age_days": policy.max_age_days,
            "warning_threshold_days": policy.warning_threshold_days,
            "auto_rotate": policy.auto_rotate,
        }
    except SecretRotationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
