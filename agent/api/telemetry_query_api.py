"""Telemetry Query API — Sprint 16: traces, metrics, logs endpoints.

Task 16.1-16.3: /api/v1/telemetry/traces, /metrics, /logs endpoints.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger("mcc.api.telemetry_query")

router = APIRouter(prefix="/telemetry", tags=["telemetry-query"])

# Lazy store access
_trace_store = None
_metric_store = None


def _get_trace_store():
    global _trace_store
    if _trace_store is None:
        from persistence.trace_store import TraceStore
        _trace_store = TraceStore()
    return _trace_store


def _get_metric_store():
    global _metric_store
    if _metric_store is None:
        from persistence.metric_store import MetricStore
        _metric_store = MetricStore()
    return _metric_store


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/traces/{mission_id}")
async def get_trace(mission_id: str):
    """Get OTel trace span tree for a mission."""
    store = _get_trace_store()
    trace = store.get_trace(mission_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"Trace for {mission_id} not found")
    return {"meta": _meta(), "trace": trace}


@router.get("/traces")
async def list_traces(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    limit: int = 20,
):
    """List available traces (metadata only)."""
    store = _get_trace_store()
    traces = store.list_traces(from_ts=from_ts, to_ts=to_ts, limit=limit)
    return {"meta": _meta(), "total": len(traces), "traces": traces}


@router.get("/metrics/current")
async def get_current_metrics():
    """Get latest metric snapshot."""
    store = _get_metric_store()
    current = store.get_current()
    return {"meta": _meta(), "metrics": current}


@router.get("/metrics/history")
async def get_metric_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    limit: int = 100,
):
    """Get historical metric snapshots."""
    store = _get_metric_store()
    history = store.get_history(from_ts=from_ts, to_ts=to_ts, limit=limit)
    return {"meta": _meta(), "total": len(history), "snapshots": history}


@router.get("/logs")
async def query_logs(
    mission_id: Optional[str] = None,
    level: Optional[str] = None,
    event: Optional[str] = None,
    stage: Optional[str] = None,
    search: Optional[str] = None,
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    limit: int = 100,
    offset: int = 0,
):
    """Query structured logs with filters and pagination.

    Reads from the structured log JSONL file.
    """
    root = Path(__file__).resolve().parent.parent.parent
    log_path = root / "logs" / "structured-events.jsonl"

    if not log_path.exists():
        return {"meta": _meta(), "total": 0, "logs": []}

    entries = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Apply filters
                if mission_id and entry.get("mission_id") != mission_id \
                        and entry.get("correlation_id") != mission_id:
                    continue
                if level:
                    levels = level.upper().split(",")
                    if entry.get("level", "").upper() not in levels:
                        continue
                if event and entry.get("event") != event:
                    continue
                if stage and entry.get("stage") != stage:
                    continue
                if from_ts and entry.get("ts", "") < from_ts:
                    continue
                if to_ts and entry.get("ts", "") > to_ts:
                    continue
                if search and search.lower() not in json.dumps(entry).lower():
                    continue

                entries.append(entry)
    except Exception as e:
        logger.error("Failed to read structured logs: %s", e)

    total = len(entries)
    entries = entries[offset:offset + limit]

    return {"meta": _meta(), "total": total, "logs": entries}
