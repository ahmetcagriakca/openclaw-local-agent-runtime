"""ReportCollector — aggregates mission metrics for final report.

Listens to stage.completed, mission.completed events and builds
a per-mission report with stage breakdown.
"""
from __future__ import annotations

from events.bus import Event, HandlerResult
from events.catalog import EventType


class ReportCollectorHandler:
    """Collects per-stage and per-mission metrics. Never halts."""

    def __init__(self):
        self.stages: list[dict] = []
        self.mission_data: dict = {}

    def __call__(self, event: Event) -> HandlerResult:
        if event.type == EventType.STAGE_COMPLETED:
            self.stages.append({
                "stage": event.data.get("stage", "unknown"),
                "specialist": event.data.get("specialist", "unknown"),
                "artifact_tokens": event.data.get("artifact_tokens", 0),
                "tool_calls": event.data.get("tool_calls", 0),
                "duration_ms": event.data.get("duration_ms", 0),
                "policy_denies": event.data.get("policy_denies", 0),
            })
            return HandlerResult.proceed()

        if event.type == EventType.MISSION_COMPLETED:
            self.mission_data = {
                "mission_id": event.data.get("mission_id", ""),
                "goal": event.data.get("goal", ""),
                "total_stages": len(self.stages),
                "stages": self.stages,
            }
            return HandlerResult.proceed()

        return HandlerResult.skip()

    def get_report(self) -> dict:
        return dict(self.mission_data) if self.mission_data else {
            "stages": list(self.stages)}
