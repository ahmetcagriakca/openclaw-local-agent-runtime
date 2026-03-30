"""Dashboard API — Sprint 16: mission history, summary, KPIs.

Task 16.4: /api/v1/dashboard/missions, /summary endpoints.
Task 16.5: /api/v1/dashboard/live SSE endpoint.

48.3a: Uses MissionNormalizer.list_missions_enriched() for consolidated
data access (D-065 compliance). MissionStore fallback retained.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

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


def _load_missions() -> list[dict]:
    """Load enriched missions via normalizer (48.3a: D-065 consolidation).

    Adds dashboard-specific fields (budget_pct, anomaly_count, etc.)
    on top of normalizer's enriched data.
    """
    from api.server import normalizer
    if not normalizer:
        return []
    items = normalizer.list_missions_enriched()
    # Add dashboard-specific default fields
    for item in items:
        item.setdefault("budget_pct", 0)
        item.setdefault("anomaly_count", 0)
        item.setdefault("budget_events", 0)
        item.setdefault("stages_detail", [])
    return items


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "mission_store", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _get_missions_data() -> tuple[list[dict], dict]:
    """Get missions from MissionStore, fallback to file-based."""
    store = _get_store()
    if store.count > 0:
        items, _ = store.list(limit=10000)
        summary = store.summary()
        return items, summary

    # Fallback: file-based
    items = _load_missions()
    # Filter terminal states for summary
    terminal = [m for m in items if m["status"] in ("completed", "failed", "aborted", "timed_out")]
    completed = [m for m in terminal if m["status"] == "completed"]
    failed = [m for m in terminal if m["status"] in ("failed", "aborted", "timed_out")]
    total_tokens = sum(m.get("tokens", 0) for m in terminal)
    durations = [m.get("duration", 0) for m in terminal if m.get("duration")]

    summary = {
        "total_missions": len(items),
        "completed": len(completed),
        "failed": len(failed),
        "aborted": 0,
        "running": len([m for m in items if m["status"] in ("executing", "running", "planning")]),
        "total_tokens": total_tokens,
        "avg_duration": round(sum(durations) / len(durations), 1) if durations else 0,
        "avg_tokens": round(total_tokens / len(terminal)) if terminal else 0,
        "total_tool_calls": sum(m.get("tools", 0) for m in terminal),
        "total_blocked": 0,
        "total_budget_events": 0,
        "total_anomalies": 0,
        "bypass_detections": 0,
        "audit_integrity": "verified",
    }
    return items, summary


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

    if store.count > 0:
        status_list = status.split(",") if status else None
        complexity_list = complexity.split(",") if complexity else None
        missions, total = store.list(
            status=status_list, complexity=complexity_list,
            search=search, from_ts=from_ts, to_ts=to_ts,
            sort=sort, limit=limit, offset=offset,
        )
        return {"meta": _meta(), "total": total, "missions": missions}

    # Fallback: file-based
    items = _load_missions()

    # Filters
    if status:
        status_list = status.split(",")
        items = [m for m in items if m.get("status") in status_list]
    if complexity:
        complexity_list = complexity.split(",")
        items = [m for m in items if m.get("complexity") in complexity_list]
    if search:
        q = search.lower()
        items = [m for m in items if q in m.get("goal", "").lower() or q in m.get("id", "").lower()]

    total = len(items)

    # Sort
    sort_key, sort_rev = "ts", True
    if sort == "tokens_desc":
        sort_key, sort_rev = "tokens", True
    elif sort == "duration_desc":
        sort_key, sort_rev = "duration", True
    items.sort(key=lambda m: m.get(sort_key, 0), reverse=sort_rev)

    paginated = items[offset:offset + limit]
    return {"meta": _meta(), "total": total, "missions": paginated}


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
    _, summary = _get_missions_data()
    return {"meta": _meta(), **summary}


@router.get("/live")
async def dashboard_live(request: Request):
    """SSE endpoint for live mission updates."""
    sse_manager = getattr(request.app.state, "sse_manager", None)
    if sse_manager is None:
        raise HTTPException(status_code=503, detail="SSE not available")

    queue = sse_manager.subscribe()
    if queue is None:
        raise HTTPException(status_code=503, detail="Max SSE clients reached")

    async def event_stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_type = event.get("type", "message")
                    data = event.get("data", "{}")
                    yield f"event: {event_type}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield "event: heartbeat\ndata: {}\n\n"
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
