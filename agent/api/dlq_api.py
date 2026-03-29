"""DLQ API — Dead Letter Queue endpoints.

B-106: List, inspect, retry, and purge failed missions from DLQ.
"""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from persistence.dlq_store import DLQStore

logger = logging.getLogger("mcc.api.dlq")
router = APIRouter(tags=["dlq"])

_dlq_store: DLQStore | None = None


def get_dlq_store() -> DLQStore:
    global _dlq_store
    if _dlq_store is None:
        _dlq_store = DLQStore()
    return _dlq_store


class DLQRetryResponse(BaseModel):
    dlq_id: str
    mission_id: str
    status: str
    message: str


@router.get("/dlq")
def list_dlq(status: str | None = None, limit: int = 50, offset: int = 0):
    """List DLQ entries."""
    store = get_dlq_store()
    entries, total = store.list(status=status, limit=limit, offset=offset)
    return {"entries": entries, "total": total}


@router.get("/dlq/summary")
def dlq_summary():
    """DLQ summary statistics."""
    return get_dlq_store().summary()


@router.get("/dlq/{dlq_id}")
def get_dlq_entry(dlq_id: str):
    """Get a single DLQ entry."""
    entry = get_dlq_store().get(dlq_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")
    return entry


@router.post("/dlq/{dlq_id}/retry")
def retry_dlq_entry(dlq_id: str) -> DLQRetryResponse:
    """Retry a failed mission from DLQ.

    Marks entry as retrying and re-submits the mission using the
    stored snapshot (retry_from_mission).
    """
    store = get_dlq_store()
    entry = store.get(dlq_id)
    if not entry:
        raise HTTPException(status_code=404, detail="DLQ entry not found")

    if entry.get("status") == "retrying":
        raise HTTPException(status_code=409, detail="Already retrying")

    if not store.mark_retrying(dlq_id):
        raise HTTPException(status_code=500, detail="Failed to mark retrying")

    # Re-submit mission via controller in background
    mission_snapshot = entry.get("mission_snapshot", {})
    mission_id = entry.get("mission_id", "")

    try:
        import threading

        from mission.controller import MissionController

        def _run_retry():
            try:
                controller = MissionController()
                # B-106 P4: Suppress DLQ enqueue during retry to prevent
                # orphan entries. Lineage stays on the original DLQ entry.
                controller._dlq_suppress = True
                result = controller.execute_mission(
                    goal=mission_snapshot.get("goal", ""),
                    user_id=mission_snapshot.get("userId", "dlq-retry"),
                    session_id=f"dlq-retry-{dlq_id}",
                    retry_from_mission=mission_snapshot,
                )
                if result.get("status") == "completed":
                    store.mark_resolved(dlq_id)
                    logger.info("DLQ retry succeeded: %s", dlq_id)
                else:
                    store.mark_pending(dlq_id)
                    logger.warning("DLQ retry failed again: %s", dlq_id)
            except Exception as e:
                store.mark_pending(dlq_id)
                logger.error("DLQ retry error: %s — %s", dlq_id, e)

        thread = threading.Thread(
            target=_run_retry, daemon=True,
            name=f"dlq-retry-{dlq_id[:20]}")
        thread.start()

    except Exception as e:
        store.mark_pending(dlq_id)
        raise HTTPException(status_code=500, detail=str(e))

    return DLQRetryResponse(
        dlq_id=dlq_id,
        mission_id=mission_id,
        status="retrying",
        message="Mission retry started in background",
    )


@router.delete("/dlq/{dlq_id}")
def purge_dlq_entry(dlq_id: str):
    """Purge a single DLQ entry."""
    if not get_dlq_store().purge(dlq_id):
        raise HTTPException(status_code=404, detail="DLQ entry not found")
    return {"status": "purged", "dlq_id": dlq_id}


@router.post("/dlq/purge-resolved")
def purge_resolved():
    """Purge all resolved DLQ entries."""
    count = get_dlq_store().purge_resolved()
    return {"purged": count}
