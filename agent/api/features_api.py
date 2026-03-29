"""Feature flags API — D-102 context isolation wire-up.

GET /api/v1/features — list all feature flag states.
"""
import logging

from fastapi import APIRouter

from config.feature_flags import get_all_flags

logger = logging.getLogger("mcc.api.features")

router = APIRouter(tags=["features"])


@router.get("/features")
async def list_features():
    """Return current feature flag states."""
    flags = get_all_flags()
    return {
        "flags": flags,
    }
