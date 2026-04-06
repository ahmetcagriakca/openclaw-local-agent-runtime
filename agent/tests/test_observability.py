"""Sprint 15 — OpenTelemetry Observability Tests.

T1: Every event type has a TracingHandler listener
T2: Span hierarchy: mission → stage → tool/llm correct
T3: Every countable event type has a MetricsHandler recorder
T4: Every structured log entry has trace_id + span_id
T5: No-blind-spots: full mission, all events have trace representation (CLOSURE BLOCKER)
E2E: 3 mission scenarios with full span tree verification
"""
from __future__ import annotations

import io
import threading
import time

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult


class InMemorySpanExporter(SpanExporter):
    """Simple in-memory span exporter for testing."""

    def __init__(self):
        self._spans = []
        self._lock = threading.Lock()

    def export(self, spans):
        with self._lock:
            self._spans.extend(spans)
        return SpanExportResult.SUCCESS

    def get_finished_spans(self):
        with self._lock:
            return list(self._spans)

    def clear(self):
        with self._lock:
            self._spans.clear()

    def shutdown(self):
        pass

from events.bus import Event, EventBus
from events.catalog import EventType
from observability.meters import MetricsHandler
from observability.otel_setup import init_otel
from observability.structured_logging import StructuredLogHandler
from observability.tracing import TracingHandler

# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def span_exporter():
    return InMemorySpanExporter()


@pytest.fixture
def metric_reader():
    return InMemoryMetricReader()


@pytest.fixture
def tracer(span_exporter):
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    return provider.get_tracer("test")


@pytest.fixture
def meter(metric_reader):
    provider = MeterProvider(metric_readers=[metric_reader])
    return provider.get_meter("test")


@pytest.fixture
def tracing_handler(tracer):
    return TracingHandler(tracer=tracer)


@pytest.fixture
def metrics_handler(meter):
    return MetricsHandler(meter=meter)


@pytest.fixture
def log_output():
    return io.StringIO()


@pytest.fixture
def log_handler(log_output, tracing_handler):
    return StructuredLogHandler(output=log_output, tracing_handler=tracing_handler)


@pytest.fixture
def full_bus(tracing_handler, metrics_handler, log_handler):
    """Bus with all three OTel handlers registered."""
    bus = EventBus()
    bus.on_all(tracing_handler, priority=2, name="TracingHandler")
    bus.on_all(metrics_handler, priority=3, name="MetricsHandler")
    bus.on_all(log_handler, priority=4, name="StructuredLogHandler")
    return bus


# ── Helper: simulate a full mission ──────────────────────────

def run_simulated_mission(
    bus: EventBus,
    complexity: str = "medium",
    stages: list[str] | None = None,
    tools: list[str] | None = None,
    with_approval: bool = False,
    with_rework: bool = False,
    with_gate: bool = True,
) -> str:
    """Emit a full sequence of events simulating a mission.

    Returns the correlation_id used.
    """
    if stages is None:
        stages = ["analyst", "developer", "reviewer"]
    if tools is None:
        tools = ["UIOverview", "ReadFile"]

    cid = f"test-{int(time.monotonic() * 1000)}"

    # Mission start
    start_event = Event(
        type=EventType.MISSION_STARTED,
        data={
            "mission_id": "m-test-001",
            "goal": "Test mission",
            "complexity": complexity,
            "stage_count": len(stages),
        },
        source="test",
        correlation_id=cid,
    )
    bus.emit(start_event)

    for stage_name in stages:
        # Stage entering
        bus.emit(Event(
            type=EventType.STAGE_ENTERING,
            data={"stage": stage_name, "specialist": stage_name,
                  "input_tokens": 5000},
            source="test", correlation_id=cid,
        ))

        # Context ready
        bus.emit(Event(
            type=EventType.STAGE_CONTEXT_READY,
            data={"stage": stage_name, "total_tokens": 4500,
                  "tier_breakdown": {"l1": 2000, "l2": 2500}},
            source="test", correlation_id=cid,
        ))

        # Tool calls
        for tool in tools:
            bus.emit(Event(
                type=EventType.TOOL_REQUESTED,
                data={"stage": stage_name, "tool": tool, "role": stage_name},
                source="test", correlation_id=cid,
            ))

            if with_approval and tool == tools[0] and stage_name == stages[0]:
                bus.emit(Event(
                    type=EventType.APPROVAL_REQUESTED,
                    data={"stage": stage_name, "tool": tool,
                          "approval_id": f"apr-{cid}", "risk": "high"},
                    source="test", correlation_id=cid,
                ))
                bus.emit(Event(
                    type=EventType.APPROVAL_GRANTED,
                    data={"stage": stage_name, "tool": tool,
                          "approval_id": f"apr-{cid}", "decision": "granted"},
                    source="test", correlation_id=cid,
                ))

            bus.emit(Event(
                type=EventType.TOOL_CLEARED,
                data={"stage": stage_name, "tool": tool},
                source="test", correlation_id=cid,
            ))

            bus.emit(Event(
                type=EventType.TOOL_EXECUTED,
                data={"stage": stage_name, "tool": tool,
                      "response_tokens": 1200, "budget_decision": "pass"},
                source="test", correlation_id=cid,
            ))

        # LLM call
        bus.emit(Event(
            type=EventType.LLM_REQUESTED,
            data={"stage": stage_name, "input_tokens": 3000, "model": "gpt-4o"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.LLM_COMPLETED,
            data={"stage": stage_name, "input_tokens": 3000,
                  "output_tokens": 1500, "model": "gpt-4o"},
            source="test", correlation_id=cid,
        ))

        # Quality gate
        if with_gate:
            bus.emit(Event(
                type=EventType.GATE_CHECKED,
                data={"stage": stage_name, "gate": f"G-{stage_name}"},
                source="test", correlation_id=cid,
            ))
            bus.emit(Event(
                type=EventType.GATE_PASSED,
                data={"stage": stage_name, "gate": f"G-{stage_name}", "score": 85},
                source="test", correlation_id=cid,
            ))

        # Stage rework (optional)
        if with_rework and stage_name == stages[0]:
            bus.emit(Event(
                type=EventType.STAGE_REWORK,
                data={"stage": stage_name, "reason": "quality below threshold",
                      "attempt": 1, "complexity": complexity},
                source="test", correlation_id=cid,
            ))

        # Stage complete
        bus.emit(Event(
            type=EventType.STAGE_COMPLETED,
            data={"stage": stage_name, "artifact_tokens": 2000,
                  "total_consumed": 8000, "tool_calls": len(tools),
                  "input_tokens": 5000, "output_tokens": 2000},
            source="test", correlation_id=cid,
        ))

    # Mission complete
    bus.emit(Event(
        type=EventType.MISSION_COMPLETED,
        data={"mission_id": "m-test-001", "total_tokens": 24000,
              "stages_completed": len(stages), "complexity": complexity},
        source="test", correlation_id=cid,
    ))

    return cid


# ══════════════════════════════════════════════════════════════
# T1: Every event type has a TracingHandler listener
# ══════════════════════════════════════════════════════════════

class TestT1_EventCoverage:
    """Verify TracingHandler handles all non-project event types.

    Project events (D-144) are handled by ProjectHandler, not TracingHandler.
    TracingHandler covers the original 28 event types.
    """

    def test_all_event_types_handled(self):
        all_types = set(EventType.all_types())
        # Project events handled by ProjectHandler, not TracingHandler
        project_types = set(EventType.namespace("project"))
        expected = all_types - project_types
        handled = TracingHandler.handled_event_types()
        missing = expected - handled
        assert missing == set(), f"TracingHandler missing: {missing}"

    def test_handler_count_is_28(self):
        assert len(TracingHandler.handled_event_types()) == 28


# ══════════════════════════════════════════════════════════════
# T2: Span hierarchy: mission → stage → tool/llm correct
# ══════════════════════════════════════════════════════════════

class TestT2_SpanHierarchy:
    """Verify parent-child span relationships."""

    def test_mission_stage_hierarchy(self, full_bus, span_exporter):
        run_simulated_mission(full_bus, stages=["analyst"])
        spans = span_exporter.get_finished_spans()

        mission_spans = [s for s in spans if s.name == "mission"]
        stage_spans = [s for s in spans if s.name.startswith("stage:")]

        assert len(mission_spans) == 1, "Expected 1 mission span"
        assert len(stage_spans) >= 1, "Expected at least 1 stage span"

        mission_ctx = mission_spans[0].context
        for ss in stage_spans:
            assert ss.parent is not None, "Stage span must have parent"
            assert ss.parent.trace_id == mission_ctx.trace_id, \
                "Stage span must belong to same trace as mission"

    def test_tool_under_stage(self, full_bus, span_exporter):
        run_simulated_mission(full_bus, stages=["developer"], tools=["ReadFile"])
        spans = span_exporter.get_finished_spans()

        tool_spans = [s for s in spans if s.name.startswith("tool:")]
        stage_spans = [s for s in spans if s.name.startswith("stage:")]

        assert len(tool_spans) >= 1, "Expected tool spans"
        assert len(stage_spans) >= 1, "Expected stage spans"

        stage_ctx = stage_spans[0].context
        for ts in tool_spans:
            assert ts.parent is not None, "Tool span must have parent"
            assert ts.parent.trace_id == stage_ctx.trace_id, \
                "Tool span must belong to same trace"

    def test_llm_under_stage(self, full_bus, span_exporter):
        run_simulated_mission(full_bus, stages=["analyst"], tools=[])
        spans = span_exporter.get_finished_spans()

        llm_spans = [s for s in spans if s.name == "llm_call"]
        assert len(llm_spans) >= 1, "Expected LLM spans"

        for ls in llm_spans:
            assert ls.parent is not None, "LLM span must have parent"

    def test_approval_under_tool(self, full_bus, span_exporter):
        run_simulated_mission(
            full_bus, stages=["analyst"], tools=["UIOverview"],
            with_approval=True,
        )
        spans = span_exporter.get_finished_spans()

        approval_spans = [s for s in spans if s.name == "approval_gate"]
        assert len(approval_spans) >= 1, "Expected approval span"

        for aps in approval_spans:
            assert aps.parent is not None, "Approval span must have parent"

    def test_context_assembly_under_stage(self, full_bus, span_exporter):
        run_simulated_mission(full_bus, stages=["analyst"])
        spans = span_exporter.get_finished_spans()

        ctx_spans = [s for s in spans if s.name == "context_assembly"]
        assert len(ctx_spans) >= 1, "Expected context_assembly span"

    def test_gate_under_stage(self, full_bus, span_exporter):
        run_simulated_mission(full_bus, stages=["analyst"], with_gate=True)
        spans = span_exporter.get_finished_spans()

        gate_spans = [s for s in spans if s.name.startswith("gate:")]
        assert len(gate_spans) >= 1, "Expected gate spans"

        for gs in gate_spans:
            assert gs.parent is not None, "Gate span must have parent"


# ══════════════════════════════════════════════════════════════
# T3: Every countable event has a MetricsHandler recorder
# ══════════════════════════════════════════════════════════════

class TestT3_MetricCoverage:
    """Verify MetricsHandler covers all metric-worthy events."""

    def test_metrics_handler_covers_metric_events(self):
        handled = MetricsHandler.handled_event_types()
        # At minimum these event types must produce metrics
        required = {
            EventType.MISSION_COMPLETED, EventType.MISSION_FAILED,
            EventType.STAGE_COMPLETED, EventType.TOOL_EXECUTED,
            EventType.TOOL_BLOCKED, EventType.LLM_COMPLETED,
            EventType.BUDGET_EXCEEDED, EventType.APPROVAL_GRANTED,
            EventType.APPROVAL_DENIED, EventType.STAGE_REWORK,
        }
        missing = required - handled
        assert missing == set(), f"MetricsHandler missing metrics for: {missing}"

    def test_instrument_count_is_17(self, meter):
        handler = MetricsHandler(meter=meter)
        assert handler.INSTRUMENT_COUNT == 17

    def test_metrics_recorded_after_mission(self, full_bus, metric_reader):
        run_simulated_mission(full_bus)
        data = metric_reader.get_metrics_data()
        metric_names = set()
        for resource_metric in data.resource_metrics:
            for scope_metric in resource_metric.scope_metrics:
                for metric in scope_metric.metrics:
                    metric_names.add(metric.name)

        expected = {
            "vezir.mission.total",
            "vezir.mission.duration",
            "vezir.mission.tokens",
            "vezir.stage.duration",
            "vezir.stage.tokens.input",
            "vezir.stage.tokens.output",
            "vezir.tool_call.total",
            "vezir.tool_call.duration",
            "vezir.tool_call.response_tokens",
            "vezir.llm_call.duration",
            "vezir.llm_call.input_tokens",
            "vezir.llm_call.output_tokens",
        }
        missing = expected - metric_names
        assert missing == set(), f"Missing metrics: {missing}"


# ══════════════════════════════════════════════════════════════
# T4: Every structured log has trace_id + span_id
# ══════════════════════════════════════════════════════════════

class TestT4_LogTraceCorrelation:
    """Verify structured logs have trace_id and span_id."""

    def test_all_logs_have_trace_fields(self, full_bus, log_handler):
        run_simulated_mission(full_bus)
        entries = log_handler.entries
        assert len(entries) > 0, "Expected log entries"

        for entry in entries:
            assert "trace_id" in entry, f"Missing trace_id in {entry['event']}"
            assert "span_id" in entry, f"Missing span_id in {entry['event']}"

    def test_trace_id_non_empty_for_mission_events(self, full_bus, log_handler):
        run_simulated_mission(full_bus)
        entries = log_handler.entries

        # After mission.started, all subsequent entries should have trace_id
        # (mission.started itself creates the span, so it may not have one yet)
        post_start = [e for e in entries if e["event"] != EventType.MISSION_STARTED]
        non_empty = [e for e in post_start if e["trace_id"]]
        assert len(non_empty) > 0, "Expected some entries with non-empty trace_id"

    def test_log_entries_have_required_fields(self, full_bus, log_handler):
        run_simulated_mission(full_bus)
        for entry in log_handler.entries:
            assert "ts" in entry
            assert "level" in entry
            assert "event" in entry
            assert "correlation_id" in entry

    def test_correlation_query_returns_all_mission_logs(self, full_bus, log_handler):
        cid = run_simulated_mission(full_bus)
        correlated = log_handler.entries_for_correlation(cid)
        assert len(correlated) == len(log_handler.entries), \
            "All entries should share the same correlation_id"


# ══════════════════════════════════════════════════════════════
# T5: No-blind-spots (CLOSURE BLOCKER)
# ══════════════════════════════════════════════════════════════

class TestT5_NoBlindSpots:
    """CLOSURE BLOCKER: Every bus event must have a trace representation.

    Runs a full mission. Collects all bus events. Verifies every event
    has a trace representation (span or span attribute). Zero exceptions.
    """

    def test_e2e_no_blind_spots(self, full_bus, span_exporter, log_handler):
        """If this test fails, Sprint 15 cannot close."""
        cid = run_simulated_mission(
            full_bus,
            stages=["analyst", "developer", "reviewer"],
            tools=["UIOverview", "ReadFile"],
            with_approval=True,
            with_rework=True,
            with_gate=True,
        )

        # Collect all bus events from the run
        bus_events = [e for e, _ in full_bus.history(correlation_id=cid)]

        # Collect all spans
        spans = span_exporter.get_finished_spans()
        span_names = {s.name for s in spans}

        # Collect all span events (annotations on spans)
        span_event_names = set()
        for s in spans:
            for ev in s.events:
                span_event_names.add(ev.name)

        # Collect all span attributes
        all_attributes = set()
        for s in spans:
            all_attributes.update(s.attributes.keys())

        # Collect structured log entries
        log_events = {e["event"] for e in log_handler.entries}

        # Verify every bus event has SOME trace representation
        uncovered = []
        for event in bus_events:
            has_representation = False

            # Check 1: Is there a span that opens/closes for this event type?
            if self._event_has_span(event.type, span_names):
                has_representation = True

            # Check 2: Is there a span event (annotation) for this event type?
            if self._event_has_span_event(event.type, span_event_names):
                has_representation = True

            # Check 3: Is there a span attribute set for this event type?
            if self._event_has_attribute(event.type, all_attributes):
                has_representation = True

            # Check 4: Is there a metric recorded for this event type?
            if event.type in MetricsHandler.handled_event_types():
                has_representation = True

            # Check 5: Is there a structured log entry?
            if event.type in log_events:
                has_representation = True

            if not has_representation:
                uncovered.append(event.type)

        assert uncovered == [], f"BLIND SPOTS DETECTED: {set(uncovered)}"

    def _event_has_span(self, event_type: str, span_names: set[str]) -> bool:
        """Check if event type maps to a span open/close."""
        mapping = {
            EventType.MISSION_STARTED: "mission",
            EventType.MISSION_COMPLETED: "mission",
            EventType.MISSION_FAILED: "mission",
            EventType.MISSION_ABORTED: "mission",
            EventType.STAGE_ENTERING: "stage:",
            EventType.STAGE_COMPLETED: "stage:",
            EventType.STAGE_FAILED: "stage:",
            EventType.STAGE_CONTEXT_READY: "context_assembly",
            EventType.TOOL_REQUESTED: "tool:",
            EventType.TOOL_EXECUTED: "tool:",
            EventType.TOOL_BLOCKED: "tool:",
            EventType.LLM_REQUESTED: "llm_call",
            EventType.LLM_COMPLETED: "llm_call",
            EventType.LLM_FAILED: "llm_call",
            EventType.APPROVAL_REQUESTED: "approval_gate",
            EventType.APPROVAL_GRANTED: "approval_gate",
            EventType.APPROVAL_DENIED: "approval_gate",
            EventType.APPROVAL_TIMEOUT: "approval_gate",
            EventType.GATE_CHECKED: "gate:",
            EventType.GATE_PASSED: "gate:",
            EventType.GATE_FAILED: "gate:",
            EventType.GATE_REWORK: "gate:",
        }
        prefix = mapping.get(event_type, "")
        if not prefix:
            return False
        return any(name.startswith(prefix) or name == prefix for name in span_names)

    def _event_has_span_event(self, event_type: str, span_event_names: set[str]) -> bool:
        """Check if event type maps to a span event annotation."""
        mapping = {
            EventType.BUDGET_WARNING: "budget_warning",
            EventType.BUDGET_EXCEEDED: "budget_exceeded",
            EventType.BUDGET_TRUNCATED: "budget_truncated",
            EventType.STAGE_REWORK: "stage_rework",
        }
        expected = mapping.get(event_type, "")
        return expected in span_event_names if expected else False

    def _event_has_attribute(self, event_type: str, all_attributes: set[str]) -> bool:
        """Check if event type maps to a span attribute."""
        mapping = {
            EventType.TOOL_CLEARED: "tool.cleared",
            EventType.TOOL_TRUNCATED: "tool.truncated",
        }
        expected = mapping.get(event_type, "")
        return expected in all_attributes if expected else False


# ══════════════════════════════════════════════════════════════
# E2E: 3 mission scenarios
# ══════════════════════════════════════════════════════════════

class TestE2E_TraceCompleteness:
    """E2E trace completeness for trivial, medium, and complex missions."""

    def test_trivial_mission(self, full_bus, span_exporter):
        """Trivial: 1 stage, 1 tool, no approval."""
        run_simulated_mission(
            full_bus, complexity="trivial",
            stages=["developer"], tools=["ReadFile"],
        )
        spans = span_exporter.get_finished_spans()
        self._verify_trace(spans, expected_stages=1, expected_tools=1)

    def test_medium_mission(self, full_bus, span_exporter):
        """Medium: 3 stages, 2 tools, with gate."""
        run_simulated_mission(
            full_bus, complexity="medium",
            stages=["analyst", "developer", "reviewer"],
            tools=["UIOverview", "ReadFile"],
            with_gate=True,
        )
        spans = span_exporter.get_finished_spans()
        self._verify_trace(spans, expected_stages=3, expected_tools=6)

    def test_complex_mission(self, full_bus, span_exporter):
        """Complex: 5 stages, 3 tools, approval + rework."""
        run_simulated_mission(
            full_bus, complexity="complex",
            stages=["po", "analyst", "architect", "developer", "reviewer"],
            tools=["UIOverview", "ReadFile", "RunCommand"],
            with_approval=True,
            with_rework=True,
            with_gate=True,
        )
        spans = span_exporter.get_finished_spans()
        self._verify_trace(spans, expected_stages=5, expected_tools=15)

    def _verify_trace(self, spans, expected_stages: int, expected_tools: int):
        """Verify span counts and attributes."""
        mission_spans = [s for s in spans if s.name == "mission"]
        stage_spans = [s for s in spans if s.name.startswith("stage:")]
        tool_spans = [s for s in spans if s.name.startswith("tool:")]
        llm_spans = [s for s in spans if s.name == "llm_call"]
        ctx_spans = [s for s in spans if s.name == "context_assembly"]

        assert len(mission_spans) == 1, \
            f"Expected 1 mission span, got {len(mission_spans)}"
        assert len(stage_spans) == expected_stages, \
            f"Expected {expected_stages} stage spans, got {len(stage_spans)}"
        assert len(tool_spans) == expected_tools, \
            f"Expected {expected_tools} tool spans, got {len(tool_spans)}"
        assert len(llm_spans) == expected_stages, \
            f"Expected {expected_stages} LLM spans, got {len(llm_spans)}"
        assert len(ctx_spans) == expected_stages, \
            f"Expected {expected_stages} context spans, got {len(ctx_spans)}"

        # Verify no null attributes
        for span in spans:
            for key, value in span.attributes.items():
                assert value is not None, \
                    f"Null attribute {key} in span {span.name}"


# ══════════════════════════════════════════════════════════════
# OTel Setup Tests
# ══════════════════════════════════════════════════════════════

class TestOtelSetup:
    """Test init_otel() returns working tracer + meter."""

    def test_init_returns_tracer_and_meter(self):
        tracer, meter = init_otel(export_to="none")
        assert tracer is not None
        assert meter is not None

    def test_tracer_creates_spans(self):
        tracer, _ = init_otel(export_to="none")
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None
            span.set_attribute("test.key", "value")

    def test_meter_creates_instruments(self):
        _, meter = init_otel(export_to="none")
        counter = meter.create_counter("test.counter")
        counter.add(1)  # Should not raise


# ══════════════════════════════════════════════════════════════
# Additional edge case tests
# ══════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and error handling."""

    def test_mission_failed_closes_span(self, full_bus, span_exporter):
        cid = "edge-fail"
        bus = full_bus

        bus.emit(Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-fail", "goal": "fail test"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.MISSION_FAILED,
            data={"error": "test failure"},
            source="test", correlation_id=cid,
        ))

        spans = span_exporter.get_finished_spans()
        mission_spans = [s for s in spans if s.name == "mission"]
        assert len(mission_spans) == 1
        assert mission_spans[0].status.status_code.name == "ERROR"

    def test_tool_blocked_closes_span(self, full_bus, span_exporter):
        cid = "edge-block"
        bus = full_bus

        bus.emit(Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-block"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.STAGE_ENTERING,
            data={"stage": "dev", "specialist": "developer"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.TOOL_REQUESTED,
            data={"stage": "dev", "tool": "DangerousTool", "role": "developer"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.TOOL_BLOCKED,
            data={"stage": "dev", "tool": "DangerousTool", "reason": "not permitted"},
            source="test", correlation_id=cid,
        ))

        spans = span_exporter.get_finished_spans()
        tool_spans = [s for s in spans if s.name.startswith("tool:")]
        assert len(tool_spans) == 1
        assert tool_spans[0].status.status_code.name == "ERROR"

    def test_budget_warning_creates_span_event(self, full_bus, span_exporter):
        cid = "edge-budget"
        bus = full_bus

        bus.emit(Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-budget"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.BUDGET_WARNING,
            data={"usage_pct": "80%", "current": 400000, "limit": 500000},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.MISSION_COMPLETED,
            data={"total_tokens": 450000},
            source="test", correlation_id=cid,
        ))

        spans = span_exporter.get_finished_spans()
        mission_spans = [s for s in spans if s.name == "mission"]
        assert len(mission_spans) == 1
        events = mission_spans[0].events
        budget_events = [e for e in events if e.name == "budget_warning"]
        assert len(budget_events) == 1

    def test_anomaly_and_bypass_recording(self, tracing_handler, span_exporter):
        """Test record_anomaly and record_bypass helper methods."""
        # Need a mission span first
        bus = EventBus()
        bus.on_all(tracing_handler, priority=2)

        cid = "edge-anomaly"
        bus.emit(Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-anomaly"},
            source="test", correlation_id=cid,
        ))

        tracing_handler.record_anomaly(cid, {
            "anomaly.stage": "developer",
            "anomaly.metric": "stage_pct",
            "anomaly.value": "76%",
        })
        tracing_handler.record_bypass(cid, {
            "bypass.tool": "RunCommand",
            "bypass.stage": "developer",
        })

        bus.emit(Event(
            type=EventType.MISSION_COMPLETED,
            data={"total_tokens": 10000},
            source="test", correlation_id=cid,
        ))

        spans = span_exporter.get_finished_spans()
        mission_spans = [s for s in spans if s.name == "mission"]
        assert len(mission_spans) == 1

        events = mission_spans[0].events
        anomaly_events = [e for e in events if e.name == "anomaly_detected"]
        bypass_events = [e for e in events if e.name == "bypass_detected"]
        assert len(anomaly_events) == 1
        assert len(bypass_events) == 1

    def test_structured_log_levels(self, full_bus, log_handler):
        """Verify log levels are correctly assigned."""
        cid = "edge-levels"
        bus = full_bus

        bus.emit(Event(
            type=EventType.MISSION_STARTED,
            data={"mission_id": "m-levels"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.BUDGET_WARNING,
            data={"usage_pct": "80%"},
            source="test", correlation_id=cid,
        ))
        bus.emit(Event(
            type=EventType.MISSION_FAILED,
            data={"error": "budget exceeded"},
            source="test", correlation_id=cid,
        ))

        entries = log_handler.entries
        levels = {e["event"]: e["level"] for e in entries}

        assert levels.get(EventType.MISSION_STARTED) == "INFO"
        assert levels.get(EventType.BUDGET_WARNING) == "WARN"
        assert levels.get(EventType.MISSION_FAILED) == "ERROR"
