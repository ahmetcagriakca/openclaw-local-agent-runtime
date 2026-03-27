"""StructuredLogHandler — EventBus consumer that emits JSON logs with trace context.

Task 15.6: Every log line carries trace_id + span_id from OTel context.
This enables log-trace correlation: given a trace_id, grep returns all
mission logs.

Register with bus.on_all(handler, priority=4, name="StructuredLogHandler").
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import timezone
from typing import IO

from opentelemetry import trace

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.otel.logging")


class StructuredLogHandler:
    """Emits structured JSON logs for every EventBus event.

    Each log line includes:
        - ts: ISO8601 timestamp
        - level: INFO/WARN/ERROR
        - event: event type string
        - trace_id: OTel trace ID (32-char hex)
        - span_id: OTel span ID (16-char hex)
        - mission_id: application-level mission ID
        - correlation_id: event bus correlation ID
        - + event-specific fields

    Output goes to a writable stream (default: stderr).
    """

    def __init__(
        self,
        output: IO | None = None,
        tracing_handler=None,
    ):
        self._output = output or sys.stderr
        self._tracing_handler = tracing_handler
        self._entries: list[dict] = []  # In-memory buffer for testing

    def __call__(self, event: Event) -> HandlerResult:
        """Emit structured JSON log for the event."""
        try:
            entry = self._build_entry(event)
            self._entries.append(entry)
            line = json.dumps(entry, ensure_ascii=False, default=str)
            self._output.write(line + "\n")
            self._output.flush()
        except Exception as e:
            logger.error("StructuredLogHandler error on %s: %s", event.type, e)
        return HandlerResult.proceed()

    @classmethod
    def handled_event_types(cls) -> set[str]:
        """This handler processes ALL event types."""
        return set(EventType.all_types())

    def _build_entry(self, event: Event) -> dict:
        """Build structured log entry with OTel trace context."""
        # Get current OTel span context
        span = trace.get_current_span()
        span_ctx = span.get_span_context() if span else None

        trace_id = ""
        span_id = ""
        if span_ctx and span_ctx.is_valid:
            trace_id = format(span_ctx.trace_id, "032x")
            span_id = format(span_ctx.span_id, "016x")

        # If we have a tracing handler, try to get trace IDs from active spans
        if not trace_id and self._tracing_handler:
            trace_id, span_id = self._get_ids_from_tracing(event)

        level = self._level_for(event.type)

        entry = {
            "ts": event.ts.astimezone(timezone.utc).isoformat(),
            "level": level,
            "event": event.type,
            "trace_id": trace_id,
            "span_id": span_id,
            "mission_id": event.data.get("mission_id", ""),
            "correlation_id": event.correlation_id,
        }

        # Add event-specific fields
        extras = self._extras_for(event)
        entry.update(extras)

        return entry

    def _get_ids_from_tracing(self, event: Event) -> tuple[str, str]:
        """Extract trace/span IDs from TracingHandler's active spans."""
        th = self._tracing_handler
        cid = event.correlation_id

        # Try mission span first
        mission_span = th._mission_spans.get(cid)
        if mission_span:
            ctx = mission_span.get_span_context()
            if ctx and ctx.is_valid:
                return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")

        # Try stage span
        stage_key = f"{cid}/{event.data.get('stage', 'unknown')}"
        stage_span = th._stage_spans.get(stage_key)
        if stage_span:
            ctx = stage_span.get_span_context()
            if ctx and ctx.is_valid:
                return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")

        return "", ""

    def _level_for(self, event_type: str) -> str:
        """Determine log level from event type."""
        if event_type in (
            EventType.MISSION_FAILED,
            EventType.MISSION_ABORTED,
            EventType.STAGE_FAILED,
            EventType.TOOL_BLOCKED,
            EventType.LLM_FAILED,
            EventType.BUDGET_EXCEEDED,
            EventType.APPROVAL_DENIED,
            EventType.APPROVAL_TIMEOUT,
            EventType.GATE_FAILED,
        ):
            return "ERROR"
        if event_type in (
            EventType.BUDGET_WARNING,
            EventType.BUDGET_TRUNCATED,
            EventType.TOOL_TRUNCATED,
            EventType.STAGE_REWORK,
            EventType.GATE_REWORK,
        ):
            return "WARN"
        return "INFO"

    def _extras_for(self, event: Event) -> dict:
        """Extract event-specific fields for the log entry."""
        data = event.data
        et = event.type

        if et in (EventType.TOOL_REQUESTED, EventType.TOOL_CLEARED,
                  EventType.TOOL_EXECUTED, EventType.TOOL_BLOCKED,
                  EventType.TOOL_TRUNCATED):
            return {
                "tool": data.get("tool", ""),
                "stage": data.get("stage", ""),
                "role": data.get("role", ""),
                "response_tokens": data.get("response_tokens", 0),
            }

        if et in (EventType.LLM_REQUESTED, EventType.LLM_COMPLETED,
                  EventType.LLM_FAILED):
            return {
                "stage": data.get("stage", ""),
                "model": data.get("model", ""),
                "input_tokens": data.get("input_tokens", 0),
                "output_tokens": data.get("output_tokens", 0),
            }

        if et in (EventType.STAGE_ENTERING, EventType.STAGE_CONTEXT_READY,
                  EventType.STAGE_COMPLETED, EventType.STAGE_FAILED,
                  EventType.STAGE_REWORK):
            return {
                "stage": data.get("stage", ""),
                "specialist": data.get("specialist", data.get("role", "")),
            }

        if et in (EventType.APPROVAL_REQUESTED, EventType.APPROVAL_GRANTED,
                  EventType.APPROVAL_DENIED, EventType.APPROVAL_TIMEOUT):
            return {
                "approval_id": data.get("approval_id", ""),
                "decision": data.get("decision", ""),
            }

        if et in (EventType.BUDGET_WARNING, EventType.BUDGET_EXCEEDED,
                  EventType.BUDGET_TRUNCATED):
            return {
                "budget_total": data.get("total", data.get("current", 0)),
                "budget_limit": data.get("limit", 0),
            }

        return {}

    # ── Query interface ───────────────────────────────────────

    @property
    def entries(self) -> list[dict]:
        """Return all recorded log entries (for testing)."""
        return list(self._entries)

    def entries_for_trace(self, trace_id: str) -> list[dict]:
        """Return all log entries with the given trace_id."""
        return [e for e in self._entries if e.get("trace_id") == trace_id]

    def entries_for_correlation(self, correlation_id: str) -> list[dict]:
        """Return all log entries with the given correlation_id."""
        return [e for e in self._entries if e.get("correlation_id") == correlation_id]
