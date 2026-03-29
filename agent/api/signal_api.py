"""Signal Artifact API — view and delete pending signal artifacts."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas import APIError
from auth.middleware import require_operator

logger = logging.getLogger("mcc.signal")

router = APIRouter(tags=["signals"])


def _get_missions_dir():
    from api.server import MISSIONS_DIR
    return MISSIONS_DIR


@router.delete(
    "/signals/{request_id}",
    responses={404: {"model": APIError}},
)
async def delete_signal(request_id: str, _operator=Depends(require_operator)):
    """Delete a pending signal artifact by requestId."""
    missions_dir = _get_missions_dir()

    # Search across all mission directories
    for mission_dir in missions_dir.iterdir():
        if not mission_dir.is_dir():
            continue
        for fpath in mission_dir.glob(f"*-request-{request_id}.json"):
            try:
                fpath.unlink()
                logger.info("Signal artifact deleted: %s", fpath)
                return {"deleted": True, "requestId": request_id}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=404, detail=f"Signal {request_id} not found")
