"""MetricsHandler — EventBus consumer that records OTel metrics.

Task 15.5: 17 metric instruments (counters + histograms).

Register with bus.on_all(handler, priority=3, name="MetricsHandler").
"""
from __future__ import annotations

import logging
import time

from opentelemetry import metrics

from events.bus import Event, HandlerResult
from events.catalog import EventType

logger = logging.getLogger("mcc.otel.metrics")

# Events that this handler records metrics for
_METRIC_EVENT_TYPES: set[str] = {
    EventType.MISSION_STARTED,
    EventType.MISSION_COMPLETED,
    EventType.MISSION_FAILED,
    EventType.MISSION_ABORTED,
    EventType.STAGE_ENTERING,
    EventType.STAGE_COMPLETED,
    EventType.STAGE_FAILED,
    EventType.TOOL_REQUESTED,
    EventType.TOOL_EXECUTED,
    EventType.TOOL_BLOCKED,
    EventType.LLM_REQUESTED,
    EventType.LLM_COMPLETED,
    EventType.LLM_FAILED,
    EventType.BUDGET_EXCEEDED,
    EventType.BUDGET_WARNING,
    EventType.APPROVAL_REQUESTED,
    EventType.APPROVAL_GRANTED,
    EventType.APPROVAL_DENIED,
    EventType.STAGE_REWORK,
}


class MetricsHandler:
    """EventBus consumer that records 17 OTel metric instruments.

    Counters:
        vezir.mission.total           — missions by status
        vezir.tool_call.total         — tool calls by tool+decision
        vezir.budget.gate_triggered   — budget triggers by check_type
        vezir.rework.total            — reworks by stage+complexity
        vezir.bypass.detected         — bypass attempts by tool
        vezir.anomaly.detected        — anomalies by rule

    Histograms:
        vezir.mission.duration        — mission duration by complexity
        vezir.mission.tokens          — total tokens per mission
        vezir.stage.duration          — stage duration by stage+complexity
        vezir.stage.tokens.input      — input tokens per stage
        vezir.stage.tokens.output     — output tokens per stage
        vezir.tool_call.duration      — tool call duration by tool
        vezir.tool_call.response_tokens — response tokens by tool
        vezir.llm_call.duration       — LLM call duration by stage
        vezir.llm_call.input_tokens   — LLM input tokens by stage
        vezir.llm_call.output_tokens  — LLM output tokens by stage
        vezir.budget.approval.duration — approval wait time by decision
    """

    INSTRUMENT_COUNT = 17

    def __init__(self, meter: metrics.Meter | None = None):
        m = meter or metrics.get_meter("vezir-runtime")

        # ── Counters (6) ─────────────────────────────────────
        self.mission_total = m.create_counter(
            "vezir.mission.total", description="Missions by status")
        self.tool_call_total = m.create_counter(
            "vezir.tool_call.total", description="Tool calls by tool and decision")
        self.budget_gate_triggered = m.create_counter(
            "vezir.budget.gate_triggered", description="Budget triggers by check_type")
        self.rework_total = m.create_counter(
            "vezir.rework.total", description="Reworks by stage and complexity")
        self.bypass_detected = m.create_counter(
            "vezir.bypass.detected", description="Bypass attempts by tool")
        self.anomaly_detected = m.create_counter(
            "vezir.anomaly.detected", description="Anomalies by rule")

        # ── Histograms (11) ──────────────────────────────────
        self.mission_duration = m.create_histogram(
            "vezir.mission.duration", unit="ms", description="Mission duration by complexity")
        self.mission_tokens = m.create_histogram(
            "vezir.mission.tokens", description="Total tokens per mission")
        self.stage_duration = m.create_histogram(
            "vezir.stage.duration", unit="ms", description="Stage duration")
        self.stage_tokens_input = m.create_histogram(
            "vezir.stage.tokens.input", description="Input tokens per stage")
        self.stage_tokens_output = m.create_histogram(
            "vezir.stage.tokens.output", description="Output tokens per stage")
        self.tool_call_duration = m.create_histogram(
            "vezir.tool_call.duration", unit="ms", description="Tool call duration")
        self.tool_call_response_tokens = m.create_histogram(
            "vezir.tool_call.response_tokens", description="Response tokens per tool call")
        self.llm_call_duration = m.create_histogram(
            "vezir.llm_call.duration", unit="ms", description="LLM call duration")
        self.llm_call_input_tokens = m.create_histogram(
            "vezir.llm_call.input_tokens", description="LLM input tokens")
        self.llm_call_output_tokens = m.create_histogram(
            "vezir.llm_call.output_tokens", description="LLM output tokens")
        self.budget_approval_duration = m.create_histogram(
            "vezir.budget.approval.duration", unit="ms",
            description="Approval wait time by decision")

        # ── Timing state ─────────────────────────────────────
        self._mission_start: dict[str, float] = {}
        self._stage_start: dict[str, float] = {}
        self._tool_start: dict[str, float] = {}
        self._llm_start: dict[str, float] = {}
        self._approval_start: dict[str, float] = {}

    def __call__(self, event: Event) -> HandlerResult:
        """Record metrics for the event."""
        handler = self._dispatch.get(event.type)
        if handler:
            try:
                handler(self, event)
            except Exception as e:
                logger.error("MetricsHandler error on %s: %s", event.type, e)
        return HandlerResult.proceed()

    @classmethod
    def handled_event_types(cls) -> set[str]:
        """Return all event types this handler records metrics for."""
        return set(_METRIC_EVENT_TYPES)

    # ── Event handlers ────────────────────────────────────────

    def _on_mission_started(self, event: Event) -> None:
        self._mission_start[event.correlation_id] = time.monotonic()

    def _on_mission_completed(self, event: Event) -> None:
        cid = event.correlation_id
        self.mission_total.add(1, {"status": "completed"})
        self.mission_tokens.record(
            event.data.get("total_tokens", 0))
        start = self._mission_start.pop(cid, None)
        if start:
            self.mission_duration.record(
                int((time.monotonic() - start) * 1000),
                {"complexity": event.data.get("complexity", "")})

    def _on_mission_failed(self, event: Event) -> None:
        cid = event.correlation_id
        self.mission_total.add(1, {"status": "failed"})
        self._mission_start.pop(cid, None)

    def _on_mission_aborted(self, event: Event) -> None:
        cid = event.correlation_id
        self.mission_total.add(1, {"status": "aborted"})
        self._mission_start.pop(cid, None)

    def _on_stage_entering(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('stage', '')}"
        self._stage_start[key] = time.monotonic()

    def _on_stage_completed(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('stage', '')}"
        stage = event.data.get("stage", "")
        self.stage_tokens_input.record(
            event.data.get("input_tokens", 0), {"stage": stage})
        self.stage_tokens_output.record(
            event.data.get("artifact_tokens", event.data.get("output_tokens", 0)),
            {"stage": stage})
        start = self._stage_start.pop(key, None)
        if start:
            self.stage_duration.record(
                int((time.monotonic() - start) * 1000),
                {"stage": stage, "complexity": event.data.get("complexity", "")})

    def _on_stage_failed(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('stage', '')}"
        self._stage_start.pop(key, None)

    def _on_llm_requested(self, event: Event) -> None:
        stage = event.data.get("stage", "")
        key = f"{event.correlation_id}/{stage}/llm"
        self._llm_start[key] = time.monotonic()

    def _on_tool_requested(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('tool', '')}"
        self._tool_start[key] = time.monotonic()

    def _on_tool_executed(self, event: Event) -> None:
        tool = event.data.get("tool", "")
        key = f"{event.correlation_id}/{tool}"
        self.tool_call_total.add(1, {"tool": tool, "decision": "executed"})
        self.tool_call_response_tokens.record(
            event.data.get("response_tokens", 0), {"tool": tool})
        start = self._tool_start.pop(key, None)
        if start:
            self.tool_call_duration.record(
                int((time.monotonic() - start) * 1000), {"tool": tool})

    def _on_tool_blocked(self, event: Event) -> None:
        tool = event.data.get("tool", "")
        key = f"{event.correlation_id}/{tool}"
        self.tool_call_total.add(1, {"tool": tool, "decision": "blocked"})
        self._tool_start.pop(key, None)

    def _on_llm_completed(self, event: Event) -> None:
        stage = event.data.get("stage", "")
        key = f"{event.correlation_id}/{stage}/llm"
        self.llm_call_input_tokens.record(
            event.data.get("input_tokens", 0), {"stage": stage})
        self.llm_call_output_tokens.record(
            event.data.get("output_tokens", 0), {"stage": stage})
        start = self._llm_start.pop(key, None)
        if start:
            self.llm_call_duration.record(
                int((time.monotonic() - start) * 1000), {"stage": stage})

    def _on_llm_failed(self, event: Event) -> None:
        stage = event.data.get("stage", "")
        key = f"{event.correlation_id}/{stage}/llm"
        self._llm_start.pop(key, None)

    def _on_budget_exceeded(self, event: Event) -> None:
        self.budget_gate_triggered.add(1, {"check_type": "exceeded"})

    def _on_budget_warning(self, event: Event) -> None:
        self.budget_gate_triggered.add(1, {"check_type": "warning"})

    def _on_approval_requested(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('approval_id', '')}"
        self._approval_start[key] = time.monotonic()

    def _on_approval_granted(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('approval_id', '')}"
        start = self._approval_start.pop(key, None)
        if start:
            self.budget_approval_duration.record(
                int((time.monotonic() - start) * 1000), {"decision": "granted"})

    def _on_approval_denied(self, event: Event) -> None:
        key = f"{event.correlation_id}/{event.data.get('approval_id', '')}"
        start = self._approval_start.pop(key, None)
        if start:
            self.budget_approval_duration.record(
                int((time.monotonic() - start) * 1000), {"decision": "denied"})

    def _on_stage_rework(self, event: Event) -> None:
        self.rework_total.add(1, {
            "stage": event.data.get("stage", ""),
            "complexity": event.data.get("complexity", ""),
        })

    # Dispatch table
    _dispatch: dict[str, callable] = {
        EventType.MISSION_STARTED: _on_mission_started,
        EventType.MISSION_COMPLETED: _on_mission_completed,
        EventType.MISSION_FAILED: _on_mission_failed,
        EventType.MISSION_ABORTED: _on_mission_aborted,
        EventType.STAGE_ENTERING: _on_stage_entering,
        EventType.STAGE_COMPLETED: _on_stage_completed,
        EventType.STAGE_FAILED: _on_stage_failed,
        EventType.TOOL_REQUESTED: _on_tool_requested,
        EventType.TOOL_EXECUTED: _on_tool_executed,
        EventType.TOOL_BLOCKED: _on_tool_blocked,
        EventType.LLM_REQUESTED: _on_llm_requested,
        EventType.LLM_COMPLETED: _on_llm_completed,
        EventType.LLM_FAILED: _on_llm_failed,
        EventType.BUDGET_EXCEEDED: _on_budget_exceeded,
        EventType.BUDGET_WARNING: _on_budget_warning,
        EventType.APPROVAL_REQUESTED: _on_approval_requested,
        EventType.APPROVAL_GRANTED: _on_approval_granted,
        EventType.APPROVAL_DENIED: _on_approval_denied,
        EventType.STAGE_REWORK: _on_stage_rework,
    }

    # ── Public helpers for external anomaly/bypass recording ──

    def record_anomaly(self, rule: str) -> None:
        """Record anomaly detection (called by AnomalyDetector integration)."""
        self.anomaly_detected.add(1, {"rule": rule})

    def record_bypass(self, tool: str) -> None:
        """Record bypass detection (called by BypassDetector integration)."""
        self.bypass_detected.add(1, {"tool": tool})
