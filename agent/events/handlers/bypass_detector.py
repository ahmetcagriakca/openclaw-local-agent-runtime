"""BypassDetector handler — detects MCP calls that skip the EventBus.

Registered as a global handler. Maintains a set of "cleared" tool calls
(those that went through tool.requested → tool.cleared → tool.executed).
If a tool.executed event arrives without a prior tool.cleared for the
same correlation+tool, it flags a bypass.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.bypass")


class BypassDetectorHandler:
    """Detects tool executions that bypassed the permission pipeline."""

    def __init__(self):
        # Set of (correlation_id, tool_name) that have been cleared
        self._cleared: set[tuple[str, str]] = set()
        self.bypass_count = 0
        self.bypass_log: list[dict] = []

    def __call__(self, event: Event) -> HandlerResult:
        if event.type == EventType.TOOL_CLEARED:
            tool = event.data.get("tool", "")
            self._cleared.add((event.correlation_id, tool))
            return HandlerResult.proceed()

        if event.type == EventType.TOOL_EXECUTED:
            tool = event.data.get("tool", "")
            key = (event.correlation_id, tool)

            if key not in self._cleared:
                self.bypass_count += 1
                self.bypass_log.append({
                    "tool": tool,
                    "correlation_id": event.correlation_id,
                    "source": event.source,
                    "ts": event.ts.isoformat(),
                })
                logger.warning(
                    "[BYPASS] Tool '%s' executed without clearing "
                    "(cid=%s, source=%s)",
                    tool, event.correlation_id, event.source)
                return HandlerResult.proceed(
                    bypass_detected=True, tool=tool)

            # Clean up after execution
            self._cleared.discard(key)
            return HandlerResult.proceed()

        return HandlerResult.skip()
