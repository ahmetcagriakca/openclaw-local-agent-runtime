"""MetricsExporter — real-time metrics dict for monitoring.

Maintains a live metrics dict that can be queried by health endpoints
or monitoring tools.
"""
from __future__ import annotations

from events.bus import Event, HandlerResult
from events.catalog import EventType


class MetricsExporterHandler:
    """Exports real-time metrics. Never halts."""

    def __init__(self):
        self.metrics = {
            "events_total": 0,
            "tools_executed": 0,
            "tools_blocked": 0,
            "tools_truncated": 0,
            "stages_completed": 0,
            "stages_failed": 0,
            "gates_passed": 0,
            "gates_failed": 0,
            "missions_completed": 0,
            "missions_failed": 0,
            "approvals_requested": 0,
            "approvals_granted": 0,
            "approvals_denied": 0,
        }

    def __call__(self, event: Event) -> HandlerResult:
        self.metrics["events_total"] += 1

        counters = {
            EventType.TOOL_EXECUTED: "tools_executed",
            EventType.TOOL_BLOCKED: "tools_blocked",
            EventType.TOOL_TRUNCATED: "tools_truncated",
            EventType.STAGE_COMPLETED: "stages_completed",
            EventType.STAGE_FAILED: "stages_failed",
            EventType.GATE_PASSED: "gates_passed",
            EventType.GATE_FAILED: "gates_failed",
            EventType.MISSION_COMPLETED: "missions_completed",
            EventType.MISSION_FAILED: "missions_failed",
            EventType.APPROVAL_REQUESTED: "approvals_requested",
            EventType.APPROVAL_GRANTED: "approvals_granted",
            EventType.APPROVAL_DENIED: "approvals_denied",
        }

        key = counters.get(event.type)
        if key:
            self.metrics[key] += 1

        return HandlerResult.proceed()

    def get_metrics(self) -> dict:
        return dict(self.metrics)
