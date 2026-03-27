# Next Steps

**Last updated:** 2026-03-27
**Current:** Phase 6 started. Sprint 17 in progress (Model A).
**Doc model:** This file is canonical for roadmap/next steps. Session context lives in `docs/ai/handoffs/current.md`.

---

## Completed Sprints

```
Sprint 12   Phase 5D      Polish + Phase 5 Closure          25 task  CLOSED (2026-03-26)
Sprint 13   Stabilization  L1/L2 + cleanup                  10 task  CLOSED (2026-03-26)
Sprint 14A  EventBus + Backend Restructure                  23 task  CLOSED (2026-03-26)
Sprint 14B  Frontend Restructure + Tooling                   8 task  CLOSED (2026-03-26)
Sprint 15   OTel Observability (traces + metrics + logs)    10 task  CLOSED (2026-03-27)
Sprint 16   Presentation Layer + CI/CD Foundation           24 task  CLOSED (2026-03-27)
Cleanup     Ruff fix + test fix + OpenClaw→Vezir rebrand     —      CLOSED (2026-03-27)
```

### Sprint 15 Deliverables

- TracingHandler: 28/28 event types → OTel spans, zero blind spots
- MetricsHandler: 17 instruments (6 counters + 11 histograms)
- StructuredLogHandler: JSON logs with trace_id/span_id injection
- 27 new tests, no-blind-spots closure blocker PASS

### Sprint 16 Deliverables

- Dashboard API: 15 new endpoints (missions, traces, metrics, logs, alerts, live SSE)
- Persistence layer: mission_store, trace_store, metric_store (JSON file)
- Alert system: 9 rules + engine + Telegram notification + CRUD API
- Frontend: MonitoringPage + 5 API hooks + live SSE feed
- CI/CD: 3 GitHub Actions (ci.yml, benchmark.yml, evidence.yml)
- Session model foundation + Jaeger evaluation doc
- 39 new tests

### Cleanup Deliverables

- Ruff: 169 lint fixes (unused imports, unsorted imports, f-strings, unused vars)
- Test fix: health check test now passes without running services
- ARCHITECTURE.md: OpenClaw → Vezir rebrand
- Final state: **458 backend tests PASS, 0 ruff errors, 0 TS errors**

## Current Capabilities

| Capability | State |
|-----------|-------|
| Token governance | EventBus + 14 handlers + budget enforcement |
| Observability | OTel traces + metrics + structured logs, 28/28 coverage |
| Visibility | Dashboard with real data, live waterfall, filtered logs, alerts |
| Alerting | 9 rules, Telegram notification, configurable thresholds |
| CI/CD | Automated tests + lint + type check + benchmark on push |
| Repository | Concern-based backend, feature-based frontend |
| Developer experience | Pre-commit hooks, ruff, CONTRIBUTING.md |

## Sprint 17 — Phase 6 Controlled Start (IN PROGRESS)

**Model:** A (forced — D-105)
**Scope:** CI benchmark fix, doc model alignment, decision freeze (D-109, D-110)
**Kickoff:** `docs/sprints/sprint-17/S17-KICKOFF.md`

## Phase 6 — Roadmap

Items that become possible now:

| Item | Why After Sprint 16 |
|------|---------------------|
| Browser E2E with Playwright | CI/CD pipeline exists to run it |
| OpenAPI → TypeScript SDK generation | Backend structured, API versioned |
| Multi-user / authentication | Session model foundation exists |
| Jaeger/Grafana deployment | OTel export path documented |
| Plugin system for custom handlers | EventBus architecture supports it |
| Mission templates / presets | Mission persistence exists |
| Cost tracking / billing | Token metrics recorded |
| Frontend component tests | Vitest + React Testing Library |
| Webhook notifications (Slack, Discord) | Alert notifier extensible |

## Decision Debt

- D-001→D-110: all frozen (110 total)

## Phase 5.5 Closure

- Phase 5.5 closure report: `docs/phase-reports/PHASE-5.5-CLOSURE-REPORT.md`
- Sprint 17 must use Model A closure (D-105 constraint: max 2 consecutive Model B)

---

*Next Steps — Vezir Platform*
*Last updated: 2026-03-27*
