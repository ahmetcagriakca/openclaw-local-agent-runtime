"""AnomalyDetector — flags unusual patterns in event stream.

Checks for: high rework count, budget warnings, bypass attempts.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.anomaly")


class AnomalyDetectorHandler:
    """Detects anomalous patterns. Never halts — advisory only."""

    def __init__(self, rework_threshold: int = 3,
                 deny_threshold: int = 10):
        self.rework_threshold = rework_threshold
        self.deny_threshold = deny_threshold
        self.rework_count = 0
        self.deny_count = 0
        self.anomalies: list[dict] = []

    def __call__(self, event: Event) -> HandlerResult:
        if event.type == EventType.STAGE_REWORK:
            self.rework_count += 1
            if self.rework_count >= self.rework_threshold:
                self._flag("high_rework",
                           f"Rework count {self.rework_count} >= threshold "
                           f"{self.rework_threshold}",
                           event)

        elif event.type == EventType.TOOL_BLOCKED:
            self.deny_count += 1
            if self.deny_count >= self.deny_threshold:
                self._flag("excessive_denies",
                           f"Deny count {self.deny_count} >= threshold "
                           f"{self.deny_threshold}",
                           event)

        elif event.type == EventType.BUDGET_EXCEEDED:
            self._flag("budget_exceeded",
                       f"Budget exceeded: {event.data}",
                       event)

        return HandlerResult.proceed()

    def _flag(self, anomaly_type: str, detail: str, event: Event):
        entry = {
            "type": anomaly_type,
            "detail": detail,
            "correlation_id": event.correlation_id,
            "ts": event.ts.isoformat(),
        }
        self.anomalies.append(entry)
        logger.warning("[ANOMALY] %s: %s (cid=%s)",
                       anomaly_type, detail, event.correlation_id)
