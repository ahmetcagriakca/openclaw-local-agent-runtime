"""ConsoleTimeline handler — real-time operator-facing event display.

Registered as global handler. Formats events into a readable timeline
on stdout for operator monitoring during mission execution.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from events.bus import Event, HandlerResult
from events.catalog import EventType

# Event type → (icon, color_code)
_DISPLAY = {
    EventType.MISSION_STARTED:    ("▶", "\033[92m"),   # green
    EventType.MISSION_COMPLETED:  ("✓", "\033[92m"),
    EventType.MISSION_FAILED:     ("✗", "\033[91m"),   # red
    EventType.MISSION_ABORTED:    ("⊘", "\033[91m"),
    EventType.STAGE_ENTERING:     ("→", "\033[96m"),   # cyan
    EventType.STAGE_COMPLETED:    ("●", "\033[96m"),
    EventType.STAGE_FAILED:       ("○", "\033[91m"),
    EventType.STAGE_REWORK:       ("↺", "\033[93m"),   # yellow
    EventType.TOOL_REQUESTED:     ("⚙", "\033[37m"),   # white
    EventType.TOOL_CLEARED:       ("✓", "\033[37m"),
    EventType.TOOL_EXECUTED:      ("⚡", "\033[37m"),
    EventType.TOOL_BLOCKED:       ("⛔", "\033[91m"),
    EventType.TOOL_TRUNCATED:     ("✂", "\033[93m"),
    EventType.BUDGET_WARNING:     ("⚠", "\033[93m"),
    EventType.BUDGET_EXCEEDED:    ("💰", "\033[91m"),
    EventType.APPROVAL_REQUESTED: ("?", "\033[93m"),
    EventType.APPROVAL_GRANTED:   ("✓", "\033[92m"),
    EventType.APPROVAL_DENIED:    ("✗", "\033[91m"),
    EventType.GATE_PASSED:        ("◆", "\033[92m"),
    EventType.GATE_FAILED:        ("◇", "\033[91m"),
}

RESET = "\033[0m"


class ConsoleTimelineHandler:
    """Prints real-time event timeline to console. Never halts."""

    def __init__(self, output=None, color: bool = True):
        self._out = output or sys.stderr
        self._color = color
        self._start_time: datetime | None = None
        self.lines: list[str] = []  # for testing

    def __call__(self, event: Event) -> HandlerResult:
        if self._start_time is None:
            self._start_time = event.ts

        elapsed = (event.ts - self._start_time).total_seconds()
        icon, color = _DISPLAY.get(event.type, ("·", "\033[90m"))

        detail = self._format_detail(event)
        if self._color:
            line = f"  {color}{icon}{RESET} {elapsed:6.1f}s  {event.type:<25} {detail}"
        else:
            line = f"  {icon} {elapsed:6.1f}s  {event.type:<25} {detail}"

        self.lines.append(line)
        try:
            print(line, file=self._out, flush=True)
        except Exception:
            pass

        return HandlerResult.proceed()

    @staticmethod
    def _format_detail(event: Event) -> str:
        d = event.data
        t = event.type

        if t in (EventType.STAGE_ENTERING, EventType.STAGE_COMPLETED):
            return f"{d.get('specialist', '')} ({d.get('stage', '')})"
        elif t in (EventType.TOOL_REQUESTED, EventType.TOOL_EXECUTED,
                   EventType.TOOL_BLOCKED):
            tok = d.get('response_tokens', '')
            tok_str = f" {tok}tok" if tok else ""
            return f"{d.get('tool', '')}{tok_str}"
        elif t == EventType.TOOL_TRUNCATED:
            return f"{d.get('tool', '')} {d.get('original_tokens', 0)}→{d.get('truncated_to', 0)}tok"
        elif t == EventType.APPROVAL_REQUESTED:
            return f"{d.get('tool', '')} risk={d.get('risk', '?')}"
        elif t == EventType.BUDGET_EXCEEDED:
            return f"total={d.get('total', d.get('mission_total', '?'))}tok"
        elif t == EventType.GATE_PASSED or t == EventType.GATE_FAILED:
            return f"{d.get('gate', '')}"
        elif t == EventType.MISSION_STARTED:
            goal = d.get('goal', '')
            return goal[:60] + "..." if len(goal) > 60 else goal
        elif t == EventType.MISSION_COMPLETED:
            return f"stages={d.get('total_stages', '?')}"
        elif t == EventType.MISSION_FAILED:
            return d.get('error', '')[:60]
        return ""
