"""Alert API — Sprint 16: CRUD for alert rules + active/history.

Task 16.8: /api/v1/alerts/rules, /active, /history endpoints.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("mcc.api.alerts")

router = APIRouter(prefix="/alerts", tags=["alerts"])

# Lazy engine access
_alert_engine = None


def _get_engine():
    global _alert_engine
    if _alert_engine is None:
        from observability.alert_engine import AlertEngine
        _alert_engine = AlertEngine()
    return _alert_engine


def set_engine(engine) -> None:
    """Set alert engine instance (for testing or server startup)."""
    global _alert_engine
    _alert_engine = engine


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/rules")
async def list_rules():
    """List all alert rules."""
    engine = _get_engine()
    return {"meta": _meta(), "rules": engine.get_rules()}


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Get a single alert rule."""
    engine = _get_engine()
    rule = engine.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return {"meta": _meta(), "rule": rule}


class RuleUpdate(BaseModel):
    threshold: Optional[int] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    notify: Optional[list[str]] = None


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, body: RuleUpdate):
    """Update alert rule threshold, enable/disable."""
    engine = _get_engine()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = engine.update_rule(rule_id, updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return {"meta": _meta(), "rule": result}


class RuleCreate(BaseModel):
    id: str
    name: str
    event_types: list[str] = []
    condition: str = "any"
    threshold: int = 1
    severity: str = "info"
    notify: list[str] = ["log"]
    enabled: bool = True


@router.post("/rules")
async def create_rule(body: RuleCreate):
    """Add a custom alert rule."""
    engine = _get_engine()
    rule = engine.add_rule(body.model_dump())
    return {"meta": _meta(), "rule": rule}


@router.get("/active")
async def get_active_alerts():
    """Get currently firing (unacknowledged) alerts."""
    engine = _get_engine()
    return {"meta": _meta(), "alerts": engine.get_active()}


@router.get("/history")
async def get_alert_history(
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
):
    """Get past alerts."""
    engine = _get_engine()
    history = engine.get_history(from_ts=from_ts, to_ts=to_ts)
    return {"meta": _meta(), "total": len(history), "alerts": history}
