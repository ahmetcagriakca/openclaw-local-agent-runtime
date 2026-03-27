# Vezir Observability — OpenTelemetry Integration

Sprint 15 output. Full tracing, metrics, and structured logging for the EventBus governance pipeline.

## Quick Start

```python
from observability import init_otel, TracingHandler, MetricsHandler, StructuredLogHandler
from events import EventBus

# Initialize OTel
tracer, meter = init_otel(export_to="console")

# Create handlers
tracing = TracingHandler(tracer=tracer)
metrics_h = MetricsHandler(meter=meter)
logging_h = StructuredLogHandler(tracing_handler=tracing)

# Register on EventBus
bus = EventBus()
bus.on_all(tracing, priority=2, name="TracingHandler")
bus.on_all(metrics_h, priority=3, name="MetricsHandler")
bus.on_all(logging_h, priority=4, name="StructuredLogHandler")
```

---

## 1. Event-to-Trace Coverage Map (28/28)

Every event type in the catalog has a trace representation. Zero blind spots.

| # | Event Type | Trace Representation |
|---|-----------|---------------------|
| 1 | `mission.started` | Mission span open |
| 2 | `mission.completed` | Mission span close (OK) + `total_tokens` attribute |
| 3 | `mission.failed` | Mission span close (ERROR) + `error` attribute |
| 4 | `mission.aborted` | Mission span close (ERROR) + `abort_reason` attribute |
| 5 | `stage.entering` | Stage span open + `input_tokens` attribute |
| 6 | `stage.context_ready` | Context assembly span (child of stage) + `total_tokens` |
| 7 | `stage.completed` | Stage span close + `artifact_tokens`, `total_consumed` |
| 8 | `stage.failed` | Stage span close (ERROR) + `error` attribute |
| 9 | `stage.rework` | Span event on stage span: `stage_rework` |
| 10 | `tool.requested` | Tool span open + `tool.name`, `tool.role` |
| 11 | `tool.cleared` | Attribute on tool span: `tool.cleared=true` |
| 12 | `tool.executed` | Tool span close + `response_tokens`, `latency_ms` |
| 13 | `tool.blocked` | Tool span close (ERROR) + `blocked_reason` |
| 14 | `tool.truncated` | Attributes on tool span: `truncated=true`, `original_tokens` |
| 15 | `llm.requested` | LLM span open + `input_tokens`, `model` |
| 16 | `llm.completed` | LLM span close + `output_tokens`, `latency_ms` |
| 17 | `llm.failed` | LLM span close (ERROR) + `error` attribute |
| 18 | `budget.warning` | Span event on mission span: `budget_warning` |
| 19 | `budget.exceeded` | Span event on mission span: `budget_exceeded` + metric |
| 20 | `budget.truncated` | Span event on parent span: `budget_truncated` |
| 21 | `approval.requested` | Approval span open (child of tool span) |
| 22 | `approval.granted` | Approval span close + `gate.decision=granted` |
| 23 | `approval.denied` | Approval span close (ERROR) + `gate.decision=denied` |
| 24 | `approval.timeout` | Approval span close (ERROR) + `gate.decision=timeout` |
| 25 | `gate.checked` | Gate span open (child of stage span) |
| 26 | `gate.passed` | Gate span close + `gate.result=passed` |
| 27 | `gate.failed` | Gate span close (ERROR) + `gate.result=failed` |
| 28 | `gate.rework` | Gate span close (ERROR) + `gate.result=rework` |

---

## 2. ID Contract

| ID | Format | Created By | Propagated To | Lifetime |
|----|--------|-----------|---------------|----------|
| `correlation_id` | 12-char UUID hex | `EventBus` on event creation | All events in a mission chain | Mission duration |
| `trace_id` | 32-char hex (OTel) | `TracerProvider` on mission span start | All child spans + structured logs | Mission duration |
| `span_id` | 16-char hex (OTel) | `TracerProvider` per span | Structured logs within that span | Span duration |
| `mission_id` | `m-YYYYMMDD-NNN` | `MissionController` on mission start | Event data field + span attributes | Mission duration |

**Ownership rules:**
- `correlation_id` is EventBus-level. Auto-generated per event, shared via `event.child()`.
- `trace_id` + `span_id` are OTel-level. Created by TracerProvider, injected into logs via `StructuredLogHandler`.
- `mission_id` is application-level. Set by controller, carried in `event.data`.

---

## 3. Metric Catalog (17 instruments)

### Counters (6)

| Metric | Labels | What It Answers |
|--------|--------|----------------|
| `vezir.mission.total` | `status` | How many missions completed/failed/aborted? |
| `vezir.tool_call.total` | `tool`, `decision` | Which tools are called most? Which are blocked? |
| `vezir.budget.gate_triggered` | `check_type` | How often do budget warnings/exceeds happen? |
| `vezir.rework.total` | `stage`, `complexity` | Which stages need the most rework? |
| `vezir.bypass.detected` | `tool` | Are tools executing outside the governance pipeline? |
| `vezir.anomaly.detected` | `rule` | What anomaly patterns are we seeing? |

### Histograms (11)

| Metric | Unit | Labels | What It Answers |
|--------|------|--------|----------------|
| `vezir.mission.duration` | ms | `complexity` | How long do missions take by complexity? |
| `vezir.mission.tokens` | — | — | Total token consumption per mission? |
| `vezir.stage.duration` | ms | `stage`, `complexity` | Which stages are slowest? |
| `vezir.stage.tokens.input` | — | `stage` | Input token cost per stage? |
| `vezir.stage.tokens.output` | — | `stage` | Output/artifact tokens per stage? |
| `vezir.tool_call.duration` | ms | `tool` | Which tools are slowest? |
| `vezir.tool_call.response_tokens` | — | `tool` | Which tools return the most data? |
| `vezir.llm_call.duration` | ms | `stage` | LLM latency per stage? |
| `vezir.llm_call.input_tokens` | — | `stage` | LLM input cost per stage? |
| `vezir.llm_call.output_tokens` | — | `stage` | LLM output per stage? |
| `vezir.budget.approval.duration` | ms | `decision` | How long do operators take to approve? |

---

## 4. Span Hierarchy

```
mission (opened on mission.started, closed on mission.completed/failed/aborted)
├── stage:analyst (opened on stage.entering, closed on stage.completed/failed)
│   ├── context_assembly (opened+closed on stage.context_ready)
│   ├── tool:UIOverview (opened on tool.requested, closed on tool.executed/blocked)
│   │   └── approval_gate (opened on approval.requested, closed on approval.granted/denied)
│   ├── tool:ReadFile
│   ├── llm_call (opened on llm.requested, closed on llm.completed/failed)
│   └── gate:G1 (opened on gate.checked, closed on gate.passed/failed/rework)
├── stage:developer
│   └── ...
└── [span events]
    ├── budget_warning
    ├── budget_exceeded
    ├── anomaly_detected
    └── bypass_detected
```

---

## 5. Extension Guide: Adding a New Event Type

When adding a new event type to the catalog:

### Step 1: Add to catalog
```python
# events/catalog.py
class EventType:
    NEW_EVENT = "namespace.new_event"
```

### Step 2: Add TracingHandler method
```python
# observability/tracing.py
# 1. Add to _EVENT_METHOD_MAP:
EventType.NEW_EVENT: "_on_new_event",

# 2. Implement the method:
def _on_new_event(self, event: Event) -> None:
    # Either open/close a span, set an attribute, or add a span event
    pass
```

### Step 3: Add MetricsHandler (if countable)
```python
# observability/meters.py
# 1. Add to _METRIC_EVENT_TYPES
# 2. Add handler method
# 3. Add to _dispatch table
```

### Step 4: Verify coverage
```bash
cd agent && python -m pytest tests/test_observability.py::TestT1_EventCoverage -v
cd agent && python -m pytest tests/test_observability.py::TestT5_NoBlindSpots -v
```

Both must pass. If T1 fails, the new event type is missing from TracingHandler. If T5 fails, the event has no trace representation at all.

---

## 6. Troubleshooting

### "I don't see my event in traces"

1. **Is the event in the catalog?** Check `EventType.all_types()` includes it.
2. **Is TracingHandler registered?** Check `bus._global_handlers` for TracingHandler.
3. **Is the event mapped?** Check `_EVENT_METHOD_MAP` in `tracing.py`.
4. **Is the span being created?** Add logging to the handler method.
5. **Is the exporter configured?** `init_otel(export_to="console")` should show spans on stdout.

### "Metrics not recording"

1. **Is the event in `_METRIC_EVENT_TYPES`?** Check `meters.py`.
2. **Is the dispatch table entry present?** Check `_dispatch` dict.
3. **Is the reader collecting?** `InMemoryMetricReader.get_metrics_data()` for tests.

### "Structured logs missing trace_id"

1. **Is StructuredLogHandler initialized with tracing_handler?** It needs a reference to `TracingHandler` to extract span contexts.
2. **Is the mission span active?** `trace_id` is extracted from active mission/stage spans.

---

## 7. File Layout

```
agent/observability/
├── __init__.py              — exports: init_otel, TracingHandler, MetricsHandler, StructuredLogHandler
├── otel_setup.py            — TracerProvider + MeterProvider initialization
├── tracing.py               — TracingHandler: 28 event types → spans
├── meters.py                — MetricsHandler: 17 OTel instruments
├── structured_logging.py    — StructuredLogHandler: JSON logs with trace context
└── README.md                — this file

agent/tests/
└── test_observability.py    — T1-T5 coverage tests + E2E trace completeness
```
