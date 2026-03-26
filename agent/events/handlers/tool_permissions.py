"""ToolPermissions handler — role-based tool access control.

Listens to tool.requested events. Checks if the tool is allowed
for the current role. Halts (blocks) if not permitted.
"""
from __future__ import annotations

import logging

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.tool_permissions")


class ToolPermissionsHandler:
    """Role-based tool permission enforcement. Halts on deny."""

    def __init__(self, get_allowed_tools=None):
        """
        Args:
            get_allowed_tools: callable(role: str) -> set[str] | None
                Returns allowed tool set for a role, or None for "all allowed".
                Default: uses mission.specialists.get_specialist_tools
        """
        self._get_allowed = get_allowed_tools

    def __call__(self, event: Event) -> HandlerResult:
        if event.type != EventType.TOOL_REQUESTED:
            return HandlerResult.skip()

        tool_name = event.data.get("tool", "")
        role = event.data.get("role", "")

        if not role:
            return HandlerResult.proceed()

        allowed = self._resolve_allowed(role)
        if allowed is None:
            # None means "all tools allowed" (e.g., remote-operator)
            return HandlerResult.proceed()

        if tool_name in allowed:
            return HandlerResult.proceed(tool=tool_name, role=role)

        logger.warning(
            "[TOOL DENIED] %s not in allowed set for role %s", tool_name, role)

        return HandlerResult.block(
            f"Tool '{tool_name}' not permitted for role '{role}'",
            tool=tool_name, role=role, policy="role_tool_access")

    def _resolve_allowed(self, role: str) -> set[str] | None:
        if self._get_allowed:
            result = self._get_allowed(role)
            return set(result) if result is not None else None

        # Default: use specialist tool policies
        try:
            from mission.specialists import get_specialist_tools
            tools = get_specialist_tools(role)
            return set(tools) if tools is not None else None
        except ImportError:
            return None
