"""TracingHandler — EventBus consumer that produces OTel spans.

Tasks 15.1–15.4: Maps all 28 event types to span operations.

Span hierarchy:
    mission
    ├── stage (per specialist)
    │   ├── context_assembly
    │   ├── tool_call
    │   │   └── approval_gate (if triggered)
    │   └── llm_call
    └── [span events: anomaly, bypass, budget_warning]
"""
from __future__ import annotations

import logging
import time
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import StatusCode, Span

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.otel.tracing")

# Map every EventType to a handler method name
_EVENT_METHOD_MAP: dict[str, str] = {
    # Mission lifecycle
    EventType.MISSION_STARTED: "_on_mission_started",
    EventType.MISSION_COMPLETED: "_on_mission_completed",
    EventType.MISSION_FAILED: "_on_mission_failed",
    EventType.MISSION_ABORTED: "_on_mission_aborted",
    # Stage lifecycle
    EventType.STAGE_ENTERING: "_on_stage_entering",
    EventType.STAGE_CONTEXT_READY: "_on_stage_context_ready",
    EventType.STAGE_COMPLETED: "_on_stage_completed",
    EventType.STAGE_FAILED: "_on_stage_failed",
    EventType.STAGE_REWORK: "_on_stage_rework",
    # Tool execution
    EventType.TOOL_REQUESTED: "_on_tool_requested",
    EventType.TOOL_CLEARED: "_on_tool_cleared",
    EventType.TOOL_EXECUTED: "_on_tool_executed",
    EventType.TOOL_BLOCKED: "_on_tool_blocked",
    EventType.TOOL_TRUNCATED: "_on_tool_truncated",
    # LLM execution
    EventType.LLM_REQUESTED: "_on_llm_requested",
    EventType.LLM_COMPLETED: "_on_llm_completed",
    EventType.LLM_FAILED: "_on_llm_failed",
    # Budget
    EventType.BUDGET_WARNING: "_on_budget_warning",
    EventType.BUDGET_EXCEEDED: "_on_budget_exceeded",
    EventType.BUDGET_TRUNCATED: "_on_budget_truncated",
    # Approval
    EventType.APPROVAL_REQUESTED: "_on_approval_requested",
    EventType.APPROVAL_GRANTED: "_on_approval_granted",
    EventType.APPROVAL_DENIED: "_on_approval_denied",
    EventType.APPROVAL_TIMEOUT: "_on_approval_timeout",
    # Quality gates
    EventType.GATE_CHECKED: "_on_gate_checked",
    EventType.GATE_PASSED: "_on_gate_passed",
    EventType.GATE_FAILED: "_on_gate_failed",
    EventType.GATE_REWORK: "_on_gate_rework",
}


class TracingHandler:
    """EventBus consumer that creates OTel spans for all 28 event types.

    Register with bus.on_all(handler, priority=2, name="TracingHandler")
    so it runs after audit trail but before governance handlers.
    """

    def __init__(self, tracer: trace.Tracer | None = None):
        self._tracer = tracer or trace.get_tracer("vezir-runtime")

        # Active spans keyed by correlation_id or composite key
        self._mission_spans: dict[str, Span] = {}
        self._stage_spans: dict[str, Span] = {}
        self._context_spans: dict[str, Span] = {}
        self._tool_spans: dict[str, Span] = {}
        self._llm_spans: dict[str, Span] = {}
        self._approval_spans: dict[str, Span] = {}
        self._gate_spans: dict[str, Span] = {}

        # Timing trackers
        self._stage_start_times: dict[str, float] = {}
        self._tool_start_times: dict[str, float] = {}
        self._llm_start_times: dict[str, float] = {}
        self._approval_start_times: dict[str, float] = {}

    def __call__(self, event: Event) -> HandlerResult:
        """Dispatch event to the appropriate span handler."""
        method_name = _EVENT_METHOD_MAP.get(event.type)
        if method_name is None:
            return HandlerResult.skip()

        method = getattr(self, method_name)
        try:
            method(event)
        except Exception as e:
            logger.error("TracingHandler error on %s: %s", event.type, e)
        return HandlerResult.proceed()

    # ── Registered event types (for coverage test T1) ────────
    @classmethod
    def handled_event_types(cls) -> set[str]:
        """Return all event types this handler processes."""
        return set(_EVENT_METHOD_MAP.keys())

    # ── Mission lifecycle ─────────────────────────────────────

    def _on_mission_started(self, event: Event) -> None:
        cid = event.correlation_id
        span = self._tracer.start_span(
            "mission",
            attributes={
                "mission.id": event.data.get("mission_id", cid),
                "mission.goal": str(event.data.get("goal", ""))[:200],
                "mission.complexity": event.data.get("complexity", ""),
                "mission.stage_count": event.data.get("stage_count", 0),
                "vezir.correlation_id": cid,
            },
        )
        self._mission_spans[cid] = span

    def _on_mission_completed(self, event: Event) -> None:
        cid = event.correlation_id
        span = self._mission_spans.pop(cid, None)
        if span:
            span.set_attribute("mission.total_tokens", event.data.get("total_tokens", 0))
            span.set_attribute("mission.stages_completed", event.data.get("stages_completed", 0))
            span.set_status(StatusCode.OK)
            span.end()

    def _on_mission_failed(self, event: Event) -> None:
        cid = event.correlation_id
        span = self._mission_spans.pop(cid, None)
        if span:
            span.set_attribute("mission.error", str(event.data.get("error", "unknown")))
            span.set_status(StatusCode.ERROR, str(event.data.get("error", "")))
            span.end()

    def _on_mission_aborted(self, event: Event) -> None:
        cid = event.correlation_id
        span = self._mission_spans.pop(cid, None)
        if span:
            span.set_attribute("mission.abort_reason", str(event.data.get("reason", "")))
            span.set_status(StatusCode.ERROR, "mission aborted")
            span.end()

    # ── Stage lifecycle ───────────────────────────────────────

    def _stage_key(self, event: Event) -> str:
        return f"{event.correlation_id}/{event.data.get('stage', 'unknown')}"

    def _on_stage_entering(self, event: Event) -> None:
        key = self._stage_key(event)
        cid = event.correlation_id
        mission_span = self._mission_spans.get(cid)
        ctx = trace.set_span_in_context(mission_span) if mission_span else None

        span = self._tracer.start_span(
            f"stage:{event.data.get('stage', 'unknown')}",
            context=ctx,
            attributes={
                "stage.name": event.data.get("stage", ""),
                "stage.role": event.data.get("specialist", event.data.get("role", "")),
                "stage.input_tokens": event.data.get("input_tokens", 0),
                "vezir.correlation_id": cid,
            },
        )
        self._stage_spans[key] = span
        self._stage_start_times[key] = time.monotonic()

    def _on_stage_context_ready(self, event: Event) -> None:
        key = self._stage_key(event)
        stage_span = self._stage_spans.get(key)
        ctx = trace.set_span_in_context(stage_span) if stage_span else None

        context_span = self._tracer.start_span(
            "context_assembly",
            context=ctx,
            attributes={
                "context.total_tokens": event.data.get("total_tokens", 0),
                "context.tier_breakdown": str(event.data.get("tier_breakdown", {})),
                "vezir.correlation_id": event.correlation_id,
            },
        )
        # Context assembly is instant — close immediately
        context_span.end()
        self._context_spans[key] = context_span

        # Also set attribute on stage span
        if stage_span:
            stage_span.set_attribute(
                "stage.context_tokens", event.data.get("total_tokens", 0)
            )

    def _on_stage_completed(self, event: Event) -> None:
        key = self._stage_key(event)
        span = self._stage_spans.pop(key, None)
        if span:
            span.set_attribute("stage.artifact_tokens", event.data.get("artifact_tokens", 0))
            span.set_attribute("stage.total_consumed", event.data.get("total_consumed", 0))
            span.set_attribute("stage.tool_calls", event.data.get("tool_calls", 0))
            start = self._stage_start_times.pop(key, None)
            if start:
                span.set_attribute("stage.duration_ms", int((time.monotonic() - start) * 1000))
            span.set_status(StatusCode.OK)
            span.end()

    def _on_stage_failed(self, event: Event) -> None:
        key = self._stage_key(event)
        span = self._stage_spans.pop(key, None)
        if span:
            span.set_attribute("stage.error", str(event.data.get("error", "")))
            span.set_status(StatusCode.ERROR, str(event.data.get("error", "")))
            span.end()
        self._stage_start_times.pop(key, None)

    def _on_stage_rework(self, event: Event) -> None:
        key = self._stage_key(event)
        stage_span = self._stage_spans.get(key)
        if stage_span:
            stage_span.add_event("stage_rework", attributes={
                "rework.reason": str(event.data.get("reason", "")),
                "rework.attempt": event.data.get("attempt", 0),
            })

    # ── Tool execution ────────────────────────────────────────

    def _tool_key(self, event: Event) -> str:
        return f"{event.correlation_id}/{event.data.get('stage', '')}/{event.data.get('tool', '')}"

    def _on_tool_requested(self, event: Event) -> None:
        key = self._tool_key(event)
        stage_key = self._stage_key(event)
        stage_span = self._stage_spans.get(stage_key)
        ctx = trace.set_span_in_context(stage_span) if stage_span else None

        span = self._tracer.start_span(
            f"tool:{event.data.get('tool', 'unknown')}",
            context=ctx,
            attributes={
                "tool.name": event.data.get("tool", ""),
                "tool.role": event.data.get("role", ""),
                "vezir.correlation_id": event.correlation_id,
            },
        )
        self._tool_spans[key] = span
        self._tool_start_times[key] = time.monotonic()

    def _on_tool_cleared(self, event: Event) -> None:
        key = self._tool_key(event)
        span = self._tool_spans.get(key)
        if span:
            span.set_attribute("tool.permitted", True)
            span.set_attribute("tool.cleared", True)

    def _on_tool_executed(self, event: Event) -> None:
        key = self._tool_key(event)
        span = self._tool_spans.pop(key, None)
        if span:
            span.set_attribute("tool.response_tokens", event.data.get("response_tokens", 0))
            start = self._tool_start_times.pop(key, None)
            if start:
                latency = int((time.monotonic() - start) * 1000)
                span.set_attribute("tool.latency_ms", latency)
            span.set_attribute(
                "tool.budget_decision", event.data.get("budget_decision", "pass")
            )
            span.set_status(StatusCode.OK)
            span.end()

    def _on_tool_blocked(self, event: Event) -> None:
        key = self._tool_key(event)
        span = self._tool_spans.pop(key, None)
        if span:
            span.set_attribute("tool.blocked_reason", str(event.data.get("reason", "")))
            span.set_status(StatusCode.ERROR, str(event.data.get("reason", "")))
            span.end()
        self._tool_start_times.pop(key, None)

    def _on_tool_truncated(self, event: Event) -> None:
        key = self._tool_key(event)
        span = self._tool_spans.get(key)
        if span:
            span.set_attribute("tool.truncated", True)
            span.set_attribute("tool.original_tokens", event.data.get("original_tokens", 0))
            span.set_attribute("tool.truncated_to", event.data.get("truncated_to", 0))

    # ── LLM execution ─────────────────────────────────────────

    def _llm_key(self, event: Event) -> str:
        return f"{event.correlation_id}/{event.data.get('stage', '')}/llm"

    def _on_llm_requested(self, event: Event) -> None:
        key = self._llm_key(event)
        stage_key = self._stage_key(event)
        stage_span = self._stage_spans.get(stage_key)
        ctx = trace.set_span_in_context(stage_span) if stage_span else None

        span = self._tracer.start_span(
            "llm_call",
            context=ctx,
            attributes={
                "llm.input_tokens": event.data.get("input_tokens", 0),
                "llm.model": event.data.get("model", ""),
                "llm.stage": event.data.get("stage", ""),
                "vezir.correlation_id": event.correlation_id,
            },
        )
        self._llm_spans[key] = span
        self._llm_start_times[key] = time.monotonic()

    def _on_llm_completed(self, event: Event) -> None:
        key = self._llm_key(event)
        span = self._llm_spans.pop(key, None)
        if span:
            span.set_attribute("llm.output_tokens", event.data.get("output_tokens", 0))
            span.set_attribute("llm.cleared", True)
            start = self._llm_start_times.pop(key, None)
            if start:
                span.set_attribute("llm.latency_ms", int((time.monotonic() - start) * 1000))
            span.set_status(StatusCode.OK)
            span.end()

    def _on_llm_failed(self, event: Event) -> None:
        key = self._llm_key(event)
        span = self._llm_spans.pop(key, None)
        if span:
            span.set_attribute("llm.error", str(event.data.get("error", "")))
            span.set_status(StatusCode.ERROR, str(event.data.get("error", "")))
            span.end()
        self._llm_start_times.pop(key, None)

    # ── Budget ────────────────────────────────────────────────

    def _on_budget_warning(self, event: Event) -> None:
        cid = event.correlation_id
        mission_span = self._mission_spans.get(cid)
        if mission_span:
            mission_span.add_event("budget_warning", attributes={
                "budget.usage_pct": str(event.data.get("usage_pct", "")),
                "budget.current": event.data.get("current", 0),
                "budget.limit": event.data.get("limit", 0),
            })

    def _on_budget_exceeded(self, event: Event) -> None:
        cid = event.correlation_id
        mission_span = self._mission_spans.get(cid)
        if mission_span:
            mission_span.set_attribute("budget.exceeded", True)
            mission_span.add_event("budget_exceeded", attributes={
                "budget.total": event.data.get("total", 0),
                "budget.limit": event.data.get("limit", 0),
            })
            mission_span.set_status(StatusCode.ERROR, "budget_exceeded")
            # Don't end mission span here — mission.failed/aborted will end it

    def _on_budget_truncated(self, event: Event) -> None:
        cid = event.correlation_id
        # Add as attribute on the relevant tool span or mission span
        stage_key = self._stage_key(event)
        stage_span = self._stage_spans.get(stage_key)
        target = stage_span or self._mission_spans.get(cid)
        if target:
            target.set_attribute("budget.check", "truncated")
            target.add_event("budget_truncated", attributes={
                "budget.original_tokens": event.data.get("original_tokens", 0),
                "budget.truncated_to": event.data.get("truncated_to", 0),
            })

    # ── Approval ──────────────────────────────────────────────

    def _approval_key(self, event: Event) -> str:
        return f"{event.correlation_id}/{event.data.get('approval_id', '')}"

    def _on_approval_requested(self, event: Event) -> None:
        key = self._approval_key(event)
        # Approval is child of the tool span that triggered it
        tool_key = self._tool_key(event)
        tool_span = self._tool_spans.get(tool_key)
        ctx = trace.set_span_in_context(tool_span) if tool_span else None

        span = self._tracer.start_span(
            "approval_gate",
            context=ctx,
            attributes={
                "gate.approval_id": event.data.get("approval_id", ""),
                "gate.tool": event.data.get("tool", ""),
                "gate.risk": event.data.get("risk", ""),
                "vezir.correlation_id": event.correlation_id,
            },
        )
        self._approval_spans[key] = span
        self._approval_start_times[key] = time.monotonic()

    def _on_approval_granted(self, event: Event) -> None:
        key = self._approval_key(event)
        span = self._approval_spans.pop(key, None)
        if span:
            span.set_attribute("gate.decision", "granted")
            start = self._approval_start_times.pop(key, None)
            if start:
                span.set_attribute(
                    "gate.operator_wait_seconds",
                    round(time.monotonic() - start, 2),
                )
            span.set_status(StatusCode.OK)
            span.end()

    def _on_approval_denied(self, event: Event) -> None:
        key = self._approval_key(event)
        span = self._approval_spans.pop(key, None)
        if span:
            span.set_attribute("gate.decision", "denied")
            span.set_attribute("gate.reason", str(event.data.get("reason", "")))
            start = self._approval_start_times.pop(key, None)
            if start:
                span.set_attribute(
                    "gate.operator_wait_seconds",
                    round(time.monotonic() - start, 2),
                )
            span.set_status(StatusCode.ERROR, "approval denied")
            span.end()

    def _on_approval_timeout(self, event: Event) -> None:
        key = self._approval_key(event)
        span = self._approval_spans.pop(key, None)
        if span:
            span.set_attribute("gate.decision", "timeout")
            start = self._approval_start_times.pop(key, None)
            if start:
                span.set_attribute(
                    "gate.operator_wait_seconds",
                    round(time.monotonic() - start, 2),
                )
            span.set_status(StatusCode.ERROR, "approval timeout")
            span.end()

    # ── Quality gates ─────────────────────────────────────────

    def _gate_key(self, event: Event) -> str:
        return f"{event.correlation_id}/{event.data.get('gate', event.data.get('stage', ''))}/gate"

    def _on_gate_checked(self, event: Event) -> None:
        key = self._gate_key(event)
        stage_key = self._stage_key(event)
        stage_span = self._stage_spans.get(stage_key)
        ctx = trace.set_span_in_context(stage_span) if stage_span else None

        span = self._tracer.start_span(
            f"gate:{event.data.get('gate', 'unknown')}",
            context=ctx,
            attributes={
                "gate.name": event.data.get("gate", ""),
                "gate.stage": event.data.get("stage", ""),
                "vezir.correlation_id": event.correlation_id,
            },
        )
        self._gate_spans[key] = span

    def _on_gate_passed(self, event: Event) -> None:
        key = self._gate_key(event)
        span = self._gate_spans.pop(key, None)
        if span:
            span.set_attribute("gate.result", "passed")
            span.set_attribute("gate.score", event.data.get("score", 0))
            span.set_status(StatusCode.OK)
            span.end()

    def _on_gate_failed(self, event: Event) -> None:
        key = self._gate_key(event)
        span = self._gate_spans.pop(key, None)
        if span:
            span.set_attribute("gate.result", "failed")
            span.set_attribute("gate.reason", str(event.data.get("reason", "")))
            span.set_status(StatusCode.ERROR, "gate failed")
            span.end()

    def _on_gate_rework(self, event: Event) -> None:
        key = self._gate_key(event)
        span = self._gate_spans.pop(key, None)
        if span:
            span.set_attribute("gate.result", "rework")
            span.set_attribute("gate.feedback", str(event.data.get("feedback", "")))
            span.set_status(StatusCode.ERROR, "gate rework required")
            span.end()

    # ── Span event helpers (Task 15.4) ────────────────────────

    def record_anomaly(self, correlation_id: str, attributes: dict[str, Any]) -> None:
        """Add anomaly event to mission span. Called by AnomalyDetector integration."""
        mission_span = self._mission_spans.get(correlation_id)
        if mission_span:
            mission_span.add_event("anomaly_detected", attributes={
                k: str(v) for k, v in attributes.items()
            })

    def record_bypass(self, correlation_id: str, attributes: dict[str, Any]) -> None:
        """Add bypass event to mission span. Called by BypassDetector integration."""
        mission_span = self._mission_spans.get(correlation_id)
        if mission_span:
            mission_span.add_event("bypass_detected", attributes={
                k: str(v) for k, v in attributes.items()
            })
            mission_span.set_status(StatusCode.ERROR, "bypass_detected")

    # ── Introspection ─────────────────────────────────────────

    @property
    def active_spans(self) -> dict[str, int]:
        """Return count of active spans by type. For diagnostics."""
        return {
            "mission": len(self._mission_spans),
            "stage": len(self._stage_spans),
            "tool": len(self._tool_spans),
            "llm": len(self._llm_spans),
            "approval": len(self._approval_spans),
            "gate": len(self._gate_spans),
        }
