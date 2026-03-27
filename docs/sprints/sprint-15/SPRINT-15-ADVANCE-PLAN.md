# Sprint 15 — Full Observability: OpenTelemetry Integration

**Status:** Advance planning (NOT kickoff-ready)
**Depends on:** Sprint 14A closure (EventBus operational, event emit points stable)
**Does NOT depend on:** Sprint 14B (frontend/tooling/monorepo — irrelevant to backend observability)
**Goal:** Kusursuz ölçüm. Every action traced, every metric recorded, every log correlated. Zero blind spots.

---

## Scope Boundary

**In scope:** Trace production, metric recording, structured log emission, completeness verification.
**Out of scope:** Dashboard endpoint, analyze_telemetry.py modernization, Jaeger/Grafana deployment, UI consumption. These are Sprint 16+ (presentation layer comes after measurement layer).

---

## 3 Mandatory Pre-Sprint Gates

These are kickoff blockers. Sprint 15 cannot start without all three frozen.

### Gate 1: Event Catalog Frozen

28 event types with fixed names and schemas. No changes during Sprint 15.

```
Verification: grep -c "^[A-Z_]" backend/app/events/catalog.py == 28
Freeze evidence: D-XXX decision record OR commit hash with "event catalog frozen" message
```

If event names or schemas change during Sprint 15, coverage percentage is meaningless. This gate prevents that.

### Gate 2: Correlation ID Contract Frozen

4 ID types with clear ownership and propagation rules:

| ID | Format | Created By | Propagated To | Lifetime |
|----|--------|-----------|---------------|----------|
| `mission_id` | `m-YYYYMMDD-NNN` | AgentRunner on mission.start | All events in that mission | Mission duration |
| `trace_id` | 32-char hex (OTel standard) | TracerProvider on mission span start | All spans + all structured logs | Mission duration |
| `span_id` | 16-char hex (OTel standard) | TracerProvider per span | Structured logs within that span | Span duration |
| `correlation_id` | `{mission_id}/s-{stage}/tc-{NNN}` | AgentRunner per action | All events for that specific action | Action duration |

**Ownership rules:**
- `mission_id` is application-level. Created by runner, carried in every Event.data.
- `trace_id` + `span_id` are OTel-level. Created by TracerProvider, injected into logs via context.
- `correlation_id` is bridge between app and OTel. Maps 1:1 to a span.

```
Verification: all 4 IDs documented in observability/README.md with format, creator, propagation
Freeze evidence: D-XXX decision record
```

### Gate 3: No-Blind-Spots Test = Closure Blocker

Test `test_e2e_no_blind_spots` must PASS for Sprint 15 to close. Not advisory. Not informational. Blocking.

```python
def test_e2e_no_blind_spots():
    """
    CLOSURE BLOCKER: If this test fails, Sprint 15 cannot close.
    
    Runs a full mission. Collects all bus events. Verifies every event
    has a trace representation (span or span attribute). Zero exceptions.
    """
    bus_events = collect_all_bus_events(mission_run)
    trace_spans = collect_all_trace_spans(mission_run)
    
    uncovered = []
    for event in bus_events:
        if not event_has_trace_representation(event, trace_spans):
            uncovered.append(event.type)
    
    assert uncovered == [], f"BLIND SPOTS DETECTED: {uncovered}"
```

This test is referenced in the closure checklist. Closure script checks for its PASS.

---

## Task Table

| Task | Description | Size |
|------|-------------|------|
| **15.0** | **OTel setup: TracerProvider + MeterProvider + exporter config (console dev, file prod)** | **S** |
| 15.1 | TracingHandler: mission + stage spans (open/close on bus events) | M |
| 15.2 | TracingHandler: tool_call + llm_call child spans | M |
| 15.3 | TracingHandler: approval_gate + context_assembly spans | S |
| 15.4 | TracingHandler: anomaly + bypass as span events | S |
| 15.5 | MetricsHandler: 17 metrics (counters + histograms) | M |
| 15.6 | StructuredLogHandler: JSON format + trace_id/span_id injection | M |
| 15.7 | Coverage verification: event completeness + span hierarchy + metric coverage + log correlation tests | M |
| 15.8 | E2E trace completeness: 3 missions, full span tree verified | M |
| 15.9 | observability/README.md: coverage map, ID contracts, extension guide | S |
| 15.MID-REPORT | Mid-review report | S |
| 15.MID | GPT mid-review | — |
| 15.CLAUDE-MID | Claude mid-assessment | — |
| 15.REPORT | Final review report | S |
| 15.RETRO | Retrospective | S |
| 15.FINAL | GPT final + Claude assessment | — |
| 15.CLOSURE | Closure (no-blind-spots test = blocker) | S |

**Implementation: 10 | Process: 7 | Total: 17 tasks**

---

## Task Details

### 15.0 — OTel Setup

```python
# observability/otel_setup.py

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader

def init_otel(service_name: str = "vezir-runtime", export_to: str = "console"):
    # Traces
    provider = TracerProvider()
    if export_to == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif export_to == "file":
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    
    # Metrics
    reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=30000)
    meter_provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)
    
    return trace.get_tracer(service_name), metrics.get_meter(service_name)
```

**Acceptance:** `init_otel()` returns tracer + meter. Console exporter produces output on first span.

### 15.1 — Mission + Stage Spans

TracingHandler registers as EventBus consumer. Opens span on `stage.start`, closes on `stage.complete`/`stage.error`. Mission span wraps all stages.

**Span attributes at open:**
- `mission.id`, `mission.complexity`, `mission.stage_count`
- `stage.name`, `stage.role`, `stage.input_tokens`

**Span attributes at close:**
- `stage.artifact_tokens`, `stage.total_consumed`, `stage.tool_calls`

**Acceptance:** After mission run, trace export shows mission → stage hierarchy with all attributes.

### 15.2 — Tool Call + LLM Call Spans

Child spans under stage span. Tool call span carries `tool.name`, `tool.response_tokens`, `tool.latency_ms`, `tool.budget_decision`. LLM call span carries `llm.input_tokens`, `llm.output_tokens`, `llm.model`.

**Acceptance:** Trace shows stage → tool_call/llm_call parent-child. Span attributes populated.

### 15.3 — Approval + Context Assembly Spans

Approval gate span: child of tool_call span that triggered it. Carries `gate.decision`, `gate.operator_wait_seconds`. Context assembly span: child of stage span. Carries `context.total_tokens`, `context.tier_breakdown`.

**Acceptance:** Approval wait time visible as dedicated span. Context assembly overhead visible.

### 15.4 — Anomaly + Bypass as Span Events

Not separate spans — events (annotations) on the mission span.

```python
mission_span.add_event("anomaly_detected", attributes={
    "anomaly.stage": "developer",
    "anomaly.metric": "stage_pct",
    "anomaly.value": "76%",
})
```

**Acceptance:** Trace export shows events attached to mission span with attributes.

### 15.5 — Metrics (17 instruments)

| Instrument | Type | Labels |
|-----------|------|--------|
| `vezir.mission.total` | Counter | status |
| `vezir.mission.duration` | Histogram | complexity |
| `vezir.mission.tokens` | Histogram | — |
| `vezir.stage.duration` | Histogram | stage, complexity |
| `vezir.stage.tokens.input` | Histogram | stage |
| `vezir.stage.tokens.output` | Histogram | stage |
| `vezir.tool_call.total` | Counter | tool, decision |
| `vezir.tool_call.duration` | Histogram | tool |
| `vezir.tool_call.response_tokens` | Histogram | tool |
| `vezir.llm_call.duration` | Histogram | stage |
| `vezir.llm_call.input_tokens` | Histogram | stage |
| `vezir.llm_call.output_tokens` | Histogram | stage |
| `vezir.budget.gate_triggered` | Counter | check_type |
| `vezir.budget.approval.duration` | Histogram | decision |
| `vezir.rework.total` | Counter | stage, complexity |
| `vezir.bypass.detected` | Counter | tool |
| `vezir.anomaly.detected` | Counter | rule |

**Acceptance:** After 3 missions, all 17 metrics have recorded values. Console exporter shows data.

### 15.6 — Structured Logs

Every log entry carries `trace_id` + `span_id` from OTel context:

```json
{
  "ts": "2026-04-15T14:30:03.245Z",
  "level": "INFO",
  "event": "tool_call.response",
  "trace_id": "abc123def456...",
  "span_id": "span789...",
  "mission_id": "m-20260415-001",
  "stage": "analyst",
  "tool": "UIOverview",
  "response_tokens": 1200
}
```

**Acceptance:** Every line in structured log has non-empty `trace_id`. Given any `trace_id`, `grep` returns all logs for that mission.

### 15.7 — Coverage Verification Tests

5 tests. All must pass.

| # | Test | What It Proves |
|---|------|---------------|
| T1 | Every event type in catalog has a TracingHandler listener | No unhandled event types |
| T2 | Span hierarchy: mission → stage → tool/llm correct | Parent-child chain valid |
| T3 | Every countable event type has a MetricsHandler recorder | No unrecorded metrics |
| T4 | Every structured log entry has trace_id + span_id | Log-trace correlation works |
| T5 | **No-blind-spots (CLOSURE BLOCKER):** full mission, all events have trace representation | Zero blind spots |

### 15.8 — E2E Trace Completeness

Run 3 missions (trivial, medium, complex). For each:
- Export trace
- Count spans: mission=1, stage=N, tool_call=M, llm_call=K
- Verify: span count matches event count
- Verify: all span attributes populated (no null/empty)
- Verify: mission span duration ≈ wall clock time

**Acceptance:** 3 trace exports saved as evidence. All span counts match. Zero nulls.

### 15.9 — Observability Documentation

`observability/README.md` contents:

1. Coverage map: 28 events → which span/attribute/metric each maps to
2. ID contract: 4 IDs with format, creator, propagation, lifetime
3. Metric catalog: 17 metrics with type, labels, unit, what question it answers
4. Extension guide: how to add a new event type and ensure OTel coverage
5. Troubleshooting: "I don't see my event in traces" checklist

---

## Event-to-Trace Coverage Map (28/28)

Sprint 15 acceptance requires this table to be 100% filled with no gaps.

| # | Event | Trace Representation |
|---|-------|---------------------|
| 1 | mission.start | Mission span open |
| 2 | mission.complete | Mission span close (OK) + total_tokens attribute |
| 3 | mission.abort | Mission span close (ERROR) + reason attribute |
| 4 | stage.transition_request | Attribute on stage span: transition_validated=true |
| 5 | stage.start | Stage span open + input_tokens attribute |
| 6 | stage.complete | Stage span close + artifact_tokens, total_consumed attributes |
| 7 | stage.error | Stage span close (ERROR) + error attribute |
| 8 | llm_call.request | LLM span open + input_tokens attribute |
| 9 | llm_call.cleared | Attribute on LLM span: cleared=true |
| 10 | llm_call.response | LLM span close + output_tokens attribute |
| 11 | tool_call.request | Tool span open + tool.name, role attributes |
| 12 | tool_call.permitted | Attribute on tool span: permitted=true |
| 13 | tool_call.cleared | Attribute on tool span: cleared=true |
| 14 | tool_call.blocked | Tool span close (ERROR) + reason attribute |
| 15 | tool_call.response | Tool span close + response_tokens, latency_ms attributes |
| 16 | tool_call.truncated | Attributes on tool span: truncated=true, original_tokens, truncated_to |
| 17 | context.assembly_request | Context span open |
| 18 | context.assembled | Context span close + total_tokens, tier_breakdown attributes |
| 19 | budget.within_limits | Attribute on parent span: budget_check=pass |
| 20 | budget.warning | Span event on parent span: "budget_warning" |
| 21 | budget.approval_required | Approval child span open |
| 22 | budget.approval_granted | Approval child span close + decision attribute |
| 23 | budget.approval_denied | Approval child span close (ERROR) + reason |
| 24 | budget.hard_abort | Mission span close (ERROR) + "budget_exceeded" |
| 25 | report.stage_summary | Not a span — metric: vezir.stage.* recorded |
| 26 | report.mission_summary | Not a span — metric: vezir.mission.* recorded |
| 27 | report.anomaly | Span event on mission span: "anomaly_detected" |
| 28 | security.bypass_detected | Span event on mission span (ERROR): "bypass_detected" |

**28/28 mapped. Zero gaps.**

---

## Evidence Checklist (12 mandatory)

| # | File | Task |
|---|------|------|
| 1 | otel-setup-verify.txt | 15.0 |
| 2 | mission-stage-spans.txt | 15.1 |
| 3 | tool-llm-spans.txt | 15.2 |
| 4 | approval-context-spans.txt | 15.3 |
| 5 | metrics-17-verify.txt | 15.5 |
| 6 | structured-log-sample.txt | 15.6 |
| 7 | coverage-tests-output.txt | 15.7 |
| 8 | no-blind-spots-test.txt (CLOSURE BLOCKER) | 15.7 |
| 9 | e2e-trace-trivial.txt | 15.8 |
| 10 | e2e-trace-medium.txt | 15.8 |
| 11 | e2e-trace-complex.txt | 15.8 |
| 12 | review-summary.md | 15.FINAL |

---

## Acceptance Criteria

1. OTel TracerProvider + MeterProvider operational
2. 28/28 events have trace representation (coverage map fully filled)
3. Span hierarchy correct: mission → stage → tool/llm → approval
4. 17 metrics recorded after 3 test missions
5. Every structured log line has non-empty trace_id + span_id
6. Log-trace correlation: grep trace_id returns all mission logs
7. No-blind-spots test PASSES (closure blocker)
8. 3 E2E traces exported with zero null attributes
9. observability/README.md complete (coverage map, ID contract, metric catalog, extension guide)
10. Event catalog was frozen before sprint started (gate 1 verified)
11. Correlation ID contract was frozen before sprint started (gate 2 verified)

---

## Closure Checklist

| # | Item | Blocking? |
|---|------|-----------|
| 1 | 12/12 evidence files present | Yes |
| 2 | No-blind-spots test PASS in evidence | **Yes — hard blocker** |
| 3 | Coverage verification tests all PASS | Yes |
| 4 | 3 E2E trace exports valid | Yes |
| 5 | GPT final review PASS | Yes |
| 6 | Claude assessment PASS | Yes |
| 7 | Retrospective complete | Yes |
| 8 | Closure script ELIGIBLE | Yes |
| 9 | Operator sign-off | Yes |

---

## What Sprint 15 Does NOT Include

| Item | Why Not | When |
|------|---------|------|
| Operator dashboard data endpoint | Presentation layer, not measurement | Sprint 16 |
| analyze_telemetry.py modernization | Consumption tooling, not production | Sprint 16 |
| Jaeger/Grafana deployment | Infrastructure, not code | Sprint 16 or ops sprint |
| Frontend observability | Different signal source (React profiler) | Phase 6 |
| Alerting rules | Requires monitoring infrastructure | Phase 6 |
| CI/CD OTel integration | After OTel stable | Phase 6 |

---

## File Layout (Sprint 15 additions)

```
backend/app/observability/
├── token_logger.py        # existing (Sprint 14A)
├── audit_trail.py         # existing (Sprint 14A)
├── report_collector.py    # existing (Sprint 14A)
├── anomaly_detector.py    # existing (Sprint 14A)
├── metrics.py             # existing (Sprint 14A) — real-time dict
├── otel_setup.py          # NEW — TracerProvider, MeterProvider init
├── tracing.py             # NEW — TracingHandler (EventBus consumer)
├── meters.py              # NEW — MetricsHandler (EventBus consumer)
├── logging.py             # NEW — StructuredLogHandler (EventBus consumer)
└── README.md              # NEW — coverage map, ID contracts, extension guide
```

4 new files + 1 README. No existing files modified. Pure addition.

---

## Timeline

| Sprint | Duration | Focus |
|--------|----------|-------|
| 13 | ~2 weeks | D-102 minimum fix + bugs + cleanup |
| 14A | ~3 weeks | EventBus + concern-based backend restructure |
| 14B | ~3 weeks | Frontend restructure + tooling + monorepo |
| **15** | **~2 weeks** | **OTel: traces + metrics + logs + completeness gates** |
| 16 | TBD | Dashboard endpoint, telemetry tooling, Jaeger/Grafana, presentation layer |
