"""ApprovalGate handler — operator pause/resume/abort on approval events.

Listens to approval.requested. Halts the pipeline until operator
responds. The controller polls for approval status and emits
approval.granted or approval.denied to resume.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.approval_gate")


class ApprovalGateHandler:
    """Halts pipeline on approval.requested until operator decides."""

    def __init__(self):
        self.pending: dict[str, dict] = {}  # approval_id → event data
        self.decided: dict[str, str] = {}   # approval_id → "granted"|"denied"

    def __call__(self, event: Event) -> HandlerResult:
        if event.type == EventType.APPROVAL_REQUESTED:
            return self._handle_requested(event)
        elif event.type == EventType.APPROVAL_GRANTED:
            return self._handle_granted(event)
        elif event.type == EventType.APPROVAL_DENIED:
            return self._handle_denied(event)
        return HandlerResult.skip()

    def _handle_requested(self, event: Event) -> HandlerResult:
        approval_id = event.data.get("approval_id", event.correlation_id)
        self.pending[approval_id] = {
            "tool": event.data.get("tool", ""),
            "role": event.data.get("role", ""),
            "risk": event.data.get("risk", "unknown"),
            "correlation_id": event.correlation_id,
        }
        logger.info(
            "[APPROVAL] Requested: %s (tool=%s, role=%s, risk=%s)",
            approval_id, event.data.get("tool"),
            event.data.get("role"), event.data.get("risk"))

        return HandlerResult.block(
            f"Approval required: {approval_id}",
            approval_id=approval_id,
            action="pause")

    def _handle_granted(self, event: Event) -> HandlerResult:
        approval_id = event.data.get("approval_id", "")
        self.decided[approval_id] = "granted"
        self.pending.pop(approval_id, None)
        logger.info("[APPROVAL] Granted: %s", approval_id)
        return HandlerResult.proceed(approval_id=approval_id, decision="granted")

    def _handle_denied(self, event: Event) -> HandlerResult:
        approval_id = event.data.get("approval_id", "")
        self.decided[approval_id] = "denied"
        self.pending.pop(approval_id, None)
        logger.info("[APPROVAL] Denied: %s", approval_id)
        return HandlerResult.block(
            f"Approval denied: {approval_id}",
            approval_id=approval_id, decision="denied")

    def is_pending(self, approval_id: str) -> bool:
        return approval_id in self.pending

    def get_decision(self, approval_id: str) -> str | None:
        return self.decided.get(approval_id)
