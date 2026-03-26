"""ToolExecutor handler — gated MCP tool execution.

Only way to execute MCP tools. Listens to tool.cleared events
(after permissions + budget pass). Calls the actual MCP client
and emits tool.executed with result.
"""
from __future__ import annotations

import logging
from typing import Callable

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.tool_executor")


class ToolExecutorHandler:
    """Executes MCP tool calls. Only runs on tool.cleared events."""

    def __init__(self, execute_fn: Callable | None = None):
        """
        Args:
            execute_fn: callable(tool_name, params) -> dict
                The actual MCP execution function.
                If None, returns a stub result (for testing).
        """
        self._execute = execute_fn
        self.executions: list[dict] = []

    def __call__(self, event: Event) -> HandlerResult:
        if event.type != EventType.TOOL_CLEARED:
            return HandlerResult.skip()

        tool = event.data.get("tool", "")
        params = event.data.get("params", {})
        stage = event.data.get("stage", "unknown")

        logger.info("[TOOL EXEC] %s (stage=%s)", tool, stage)

        if self._execute:
            try:
                result = self._execute(tool, params)
                success = result.get("success", True)
                output = result.get("output", "")
            except Exception as e:
                success = False
                output = str(e)
        else:
            # Stub for testing
            success = True
            output = f"[stub] {tool} executed"

        execution = {
            "tool": tool,
            "stage": stage,
            "success": success,
            "output_length": len(str(output)),
            "correlation_id": event.correlation_id,
        }
        self.executions.append(execution)

        return HandlerResult.proceed(
            tool=tool, success=success,
            output=output, stage=stage)
