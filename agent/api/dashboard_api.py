"""Dashboard API — Sprint 16: mission history, summary, KPIs.

Task 16.4: /api/v1/dashboard/missions, /summary endpoints.
Task 16.5: /api/v1/dashboard/live SSE endpoint.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from api.schemas import ResponseMeta, DataQuality

logger = logging.getLogger("mcc.api.dashboard")

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Lazy store access — initialized on first use
_mission_store = None


def _get_store():
    global _mission_store
    if _mission_store is None:
        from persistence.mission_store import MissionStore
        _mission_store = MissionStore()
    return _mission_store


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "mission_store", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/missions")
async def list_dashboard_missions(
    status: Optional[str] = None,
    complexity: Optional[str] = None,
    search: Optional[str] = None,
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    limit: int = 20,
    offset: int = 0,
    sort: str = "ts_desc",
):
    """List missions with filters and pagination."""
    store = _get_store()
    status_list = status.split(",") if status else None
    complexity_list = complexity.split(",") if complexity else None

    missions, total = store.list(
        status=status_list, complexity=complexity_list,
        search=search, from_ts=from_ts, to_ts=to_ts,
        sort=sort, limit=limit, offset=offset,
    )
    return {"meta": _meta(), "total": total, "missions": missions}


@router.get("/missions/{mission_id}")
async def get_dashboard_mission(mission_id: str):
    """Get full mission detail."""
    store = _get_store()
    mission = store.get(mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return {"meta": _meta(), "mission": mission}


@router.get("/summary")
async def get_dashboard_summary():
    """Get aggregate KPI summary."""
    store = _get_store()
    summary = store.summary()
    return {"meta": _meta(), **summary}


@router.get("/live")
async def dashboard_live(request: Request):
    """SSE endpoint for live mission updates.

    Streams real-time events from SSE manager.
    """
    sse_manager = getattr(request.app.state, "sse_manager", None)
    if sse_manager is None:
        raise HTTPException(status_code=503, detail="SSE not available")

    queue = sse_manager.subscribe()
    if queue is None:
        raise HTTPException(status_code=503, detail="Max SSE clients reached")

    async def event_stream():
        try:
            # Send connected event
            yield f"event: connected\ndata: {{}}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_type = event.get("type", "message")
                    data = event.get("data", "{}")
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: heartbeat\ndata: {{}}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            sse_manager.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
