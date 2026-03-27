# Sprint 15 — Retrospective

**Sprint:** 15 — Full Observability: OpenTelemetry Integration
**Date:** 2026-03-27

---

## What Went Well

1. **28/28 event coverage on first pass** — Every event type in the catalog got a trace representation. No-blind-spots closure blocker test passed immediately after first implementation round.
2. **Clean separation of concerns** — Three new handlers (TracingHandler, MetricsHandler, StructuredLogHandler) each have a single responsibility. No coupling between them.
3. **Span hierarchy correct from the start** — mission → stage → tool/llm → approval parent-child chain validated in 6 hierarchy tests without rework.
4. **17 metric instruments operational** — Counters and histograms cover all key observability questions (mission duration, tool latency, stage tokens, budget events).
5. **Zero regressions** — All 418 pre-existing tests continued to pass. Pure addition — no existing files modified.
6. **InMemorySpanExporter workaround** — OTel SDK version didn't include InMemorySpanExporter; wrote a 20-line replacement in test file. No external dependency needed.

## What Could Be Better

1. **Plan event names didn't match catalog** — The advance plan used theoretical event names (e.g., `mission.start`) that differed from actual catalog (`mission.started`). Required mental mapping during implementation.
2. **MetricsHandler missing start-time tracking** — Initial implementation forgot `STAGE_ENTERING` and `LLM_REQUESTED` in the dispatch table for duration tracking. Caught by test, fixed in same session.
3. **Structured log trace_id extraction** — Direct OTel context doesn't always have the span active when the bus handler runs. Had to add fallback path through TracingHandler's active span dictionaries.

## Metrics

| Metric | Sprint 14B | Sprint 15 | Delta |
|--------|-----------|-----------|-------|
| Backend tests | 392 | 419 | +27 |
| New test files | 0 | 1 | +1 |
| OTel event coverage | 0/28 | 28/28 | +28 |
| Metric instruments | 0 | 17 | +17 |
| New Python files | 0 | 5 | +5 |

## Actionable Outputs

- **P-15.1:** When writing advance plans, use actual catalog constant names, not theoretical event names.
- **P-15.2:** Duration metrics always need both start and end event types in the dispatch table — add a checklist item for this.

---

*Sprint 15 Retrospective — Vezir Platform*
