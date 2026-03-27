# Sprint 16 — Presentation Layer + CI/CD Foundation

**Status:** Advance planning (NOT kickoff-ready)
**Depends on:** Sprint 15 closure (OTel operational, 28/28 events traced, metrics recorded)
**Goal:** Connect measurement to visibility. Operator sees everything. Automated quality gates.

---

## Rationale

Sprint 13 fixed the token problem. Sprint 14 built the architecture. Sprint 15 built the nervous system (OTel). Sprint 16 builds the eyes and the reflexes — the operator sees system behavior and the pipeline guards itself.

```
Sprint 13   Sprint 14A  Sprint 14B  Sprint 15   Sprint 16
fix         build       complete    measure     SEE + GUARD
─────────   ─────────   ─────────   ─────────   ─────────
L1/L2       EventBus    Frontend    OTel        Dashboard API
inline      handlers    features/   traces      Live monitoring
            backend     tooling     metrics     CI/CD pipeline
            restructure Docker      struct logs Alerting
                        monorepo               analyze_telemetry
                                               Phase 6 bridge
```

---

## Source: Deferred Items

### From Sprint 15

| # | Item | Why Deferred |
|---|------|-------------|
| D1 | Operator dashboard data endpoint | Presentation layer, not measurement |
| D2 | analyze_telemetry.py modernization | Consumption tooling, not production |
| D3 | Jaeger/Grafana deployment consideration | Infrastructure, not code |

### From Sprint 14B

| # | Item | Why Deferred |
|---|------|-------------|
| D4 | CI/CD pipeline (GitHub Actions) | After structure + OTel finalized |

### New Items (identified during planning)

| # | Item | Rationale |
|---|------|-----------|
| N1 | Dashboard API endpoints: traces, metrics, logs, mission detail | Dashboard artifact (v4) needs real backend data |
| N2 | WebSocket or SSE for live dashboard updates | Running missions need real-time feed |
| N3 | Alert rules engine: configurable thresholds → notification | OTel metrics exist but no alerting |
| N4 | Telegram alert integration | Operator gets critical alerts on phone |
| N5 | GitHub Actions: test + lint + type check on push | Pre-commit covers local, CI covers remote |
| N6 | GitHub Actions: sprint closure evidence auto-collect | Reduce manual evidence gathering |
| N7 | Performance regression CI gate | Compare benchmark vs baseline, fail if regressed |
| N8 | Dashboard persistence (mission history query) | Current dashboard is in-memory mock — needs persistence layer |
| N9 | User/session model foundation | Dashboard has `akca` placeholder — make it real for future multi-user |

---

## Sprint 16 Architecture

### What Gets Built

```
backend/app/
├── api/v1/
│   ├── ...existing routes...
│   ├── telemetry.py          ← NEW: /api/v1/telemetry/traces, /metrics, /logs
│   ├── dashboard.py          ← NEW: /api/v1/dashboard/missions, /summary
│   └── alerts.py             ← NEW: /api/v1/alerts/rules, /active, /history
│
├── observability/
│   ├── ...existing (Sprint 15)...
│   ├── query.py              ← NEW: trace/metric/log query layer
│   ├── alert_engine.py       ← NEW: rule evaluation, threshold checks
│   └── alert_notifier.py     ← NEW: Telegram + log notification dispatch
│
├── persistence/
│   ├── __init__.py            ← NEW
│   ├── mission_store.py       ← NEW: mission history persistence (JSON file or SQLite)
│   ├── trace_store.py         ← NEW: completed trace storage + query
│   └── metric_store.py        ← NEW: metric snapshot storage + query
│
├── auth/                       ← NEW: foundation only
│   ├── __init__.py
│   └── session.py             ← NEW: session model, operator identity (no auth flow yet)

frontend/src/
├── features/
│   ├── ...existing...
│   └── monitoring/            ← NEW: dashboard v4 integrated
│       ├── MonitoringPage.tsx
│       ├── WaterfallView.tsx  ← from dashboard artifact
│       ├── LogViewer.tsx      ← from dashboard artifact
│       ├── useTraces.ts       ← real API hooks
│       ├── useMetrics.ts
│       ├── useLiveMission.ts  ← SSE/WebSocket hook
│       └── index.ts

.github/
├── workflows/
│   ├── ci.yml                 ← NEW: test + lint + type check
│   ├── benchmark.yml          ← NEW: performance regression gate
│   └── evidence.yml           ← NEW: closure evidence auto-collect
```

### Dashboard Data Flow

```
OTel SDK → TracerProvider → traces → trace_store.py → /api/v1/telemetry/traces → frontend
         → MeterProvider → metrics → metric_store.py → /api/v1/telemetry/metrics → frontend
         → StructuredLog → jsonl → /api/v1/telemetry/logs → frontend (filtered, paginated)

EventBus → stage.complete → alert_engine.py → rule check → alert_notifier.py → Telegram
         → budget.approval_required → live SSE → frontend dashboard (real-time)
         → mission.complete → mission_store.py → /api/v1/dashboard/missions → frontend
```

---

## Task Table

### Track 0: Dashboard API (backend)

| Task | Description | Size |
|------|-------------|------|
| 16.0 | Persistence layer: mission_store.py (JSON-file or SQLite based, mission history CRUD) | M |
| 16.1 | Trace query layer: trace_store.py (read completed OTel traces, filter by mission/stage/time) | M |
| 16.2 | Metric query layer: metric_store.py (snapshot current OTel metrics, historical query) | M |
| 16.3 | Log query endpoint: /api/v1/telemetry/logs (filtered, paginated, level/stage/time range) | M |
| 16.4 | Dashboard endpoints: /api/v1/dashboard/missions (list, filter, detail), /summary (KPIs) | M |
| 16.5 | Live mission SSE endpoint: /api/v1/dashboard/live (real-time stage progress, tool calls, budget events) | M |

### Track 1: Alert System

| Task | Description | Size |
|------|-------------|------|
| 16.6 | Alert rules engine: configurable thresholds, evaluation on EventBus events | M |
| 16.7 | Alert notification: Telegram bot integration (critical alerts to operator) | S |
| 16.8 | Alert API: /api/v1/alerts/rules (CRUD), /active (current), /history (past) | M |
| 16.9 | Default alert rules: budget gate >3 per mission, stage >50% tokens, rework >limit, bypass detected | S |

### Track 2: Dashboard Frontend Integration

| Task | Description | Size |
|------|-------------|------|
| 16.10 | Extract dashboard artifact components: WaterfallView, LogViewer, StageBreakdown, BudgetPanel | M |
| 16.11 | API hooks: useTraces, useMetrics, useLogs, useMissions, useLiveMission (SSE) | M |
| 16.12 | MonitoringPage: replace mock data with real API hooks, connect filters to query params | L |
| 16.13 | Live mission view: real-time waterfall updates via SSE, auto-refresh on stage.complete | M |

### Mid-Review Gate

| Task | Description |
|------|-------------|
| 16.MID-REPORT | Mid-review report |
| 16.MID | GPT mid-review |
| 16.CLAUDE-MID | Claude mid-assessment |

### Track 3: CI/CD Pipeline

| Task | Description | Size |
|------|-------------|------|
| 16.14 | GitHub Actions ci.yml: pytest + vitest + tsc --noEmit + ruff + mypy on push/PR | M |
| 16.15 | GitHub Actions benchmark.yml: run benchmark, compare vs baseline, fail if regressed >10% | S |
| 16.16 | GitHub Actions evidence.yml: auto-collect closure evidence (test outputs, coverage, structure) | M |
| 16.17 | Pre-commit → CI parity check: verify local pre-commit rules match CI checks | S |

### Track 4: Foundation Items

| Task | Description | Size |
|------|-------------|------|
| 16.18 | analyze_telemetry.py modernization: read OTel traces + metrics instead of ad-hoc logs | M |
| 16.19 | Session/operator model: auth/session.py — operator identity, session tracking (no auth flow) | S |
| 16.20 | Jaeger evaluation: can we export OTel traces to Jaeger? Document setup path, do not deploy. | S |

### Track 5: Verification + Closure

| Task | Description | Size |
|------|-------------|------|
| 16.21 | Full integration test: real mission → OTel traces → persistence → API → dashboard renders | M |
| 16.22 | Alert E2E: trigger budget gate → alert fires → Telegram receives notification | S |
| 16.23 | CI pipeline verification: push branch → CI runs → all checks pass | S |
| 16.REPORT | Final review report | S |
| 16.RETRO | Retrospective | S |
| 16.FINAL | GPT final + Claude assessment | — |
| 16.CLOSURE | Closure + Phase 5.5 closure report (final stabilization sprint) | S |

**Implementation: 24 | Process: 7 | Total: 31 tasks**

---

## Dashboard API Specifications

### GET /api/v1/dashboard/missions

```
Query params:
  ?status=completed,aborted    (multi-select filter)
  ?complexity=medium,complex   (multi-select filter)
  ?search=login                (goal text search)
  ?from=2026-03-26T00:00:00Z   (time range)
  ?to=2026-03-27T00:00:00Z
  ?limit=20&offset=0           (pagination)
  ?sort=tokens_desc            (sort: tokens_desc, duration_desc, ts_desc)

Response:
{
  "total": 42,
  "missions": [
    {
      "id": "m-001",
      "goal": "Create login page",
      "complexity": "medium",
      "status": "completed",
      "tokens": 73570,
      "duration": 45.2,
      "stages": 5,
      "tools": 6,
      "reworks": 1,
      "ts": "2026-03-26T14:30:00Z",
      "operator": "akca",
      "budget_pct": 24.5,
      "anomaly_count": 1,
      "budget_events": 1
    }
  ]
}
```

### GET /api/v1/dashboard/missions/{id}

Full mission detail: stage breakdown, tool calls, budget events, anomalies. Same schema as dashboard mock data — just from persistence instead of memory.

### GET /api/v1/dashboard/summary

```
Response:
{
  "total_missions": 42,
  "completed": 35,
  "aborted": 4,
  "running": 3,
  "total_tokens": 2450000,
  "avg_duration": 38.5,
  "avg_tokens": 58333,
  "total_tool_calls": 186,
  "total_blocked": 8,
  "total_budget_events": 12,
  "total_anomalies": 6,
  "bypass_detections": 0,
  "audit_integrity": "verified"
}
```

### GET /api/v1/telemetry/traces/{mission_id}

Returns OTel trace as span tree. Same structure as dashboard waterfall expects.

### GET /api/v1/telemetry/logs

```
Query params:
  ?mission_id=m-001
  ?level=WARN,ERROR
  ?event=tool_call.blocked
  ?stage=developer
  ?from=...&to=...
  ?search=Snapshot
  ?limit=100&offset=0

Response:
{
  "total": 847,
  "logs": [
    {
      "ts": "2026-03-26T14:30:03.245Z",
      "level": "WARN",
      "event": "budget.approval_required",
      "stage": "developer",
      "tool": "Snapshot",
      "message": "62,000 tok > 50K limit",
      "tokens": 62000,
      "trace_id": "abc123...",
      "span_id": "span789..."
    }
  ]
}
```

### SSE /api/v1/dashboard/live

Real-time event stream for running missions:

```
event: stage.start
data: {"mission_id":"m-006","stage":"architect","input_tokens":3200}

event: tool_call.response
data: {"mission_id":"m-006","stage":"architect","tool":"UIOverview","tokens":1050,"latency":195}

event: budget.approval_required
data: {"mission_id":"m-006","stage":"developer","tool":"Snapshot","value":62000,"limit":50000}

event: stage.complete
data: {"mission_id":"m-006","stage":"architect","tokens":5200,"duration":3.1}
```

Frontend `useLiveMission` hook subscribes to this SSE and updates waterfall in real-time.

---

## Alert Rules Engine

### Default Rules

| Rule ID | Trigger | Threshold | Severity | Action |
|---------|---------|-----------|----------|--------|
| A-001 | Budget gates per mission | > 3 | Warning | Log + Telegram |
| A-002 | Stage token percentage | > 50% of mission | Warning | Log |
| A-003 | Rework count per stage | > complexity limit | Warning | Log + Telegram |
| A-004 | Bypass detected | Any | Critical | Log + Telegram + mission flag |
| A-005 | Audit integrity failure | Any | Critical | Log + Telegram + system pause |
| A-006 | Mission total tokens | > 250K (approaching 300K limit) | Warning | Log + Telegram |
| A-007 | Tool response > 50K | Blocked by budget | Info | Log |
| A-008 | Mission aborted | Any | Warning | Log + Telegram |
| A-009 | Consecutive mission failures | > 2 in a row | Warning | Log + Telegram |

### Alert Notification Format (Telegram)

```
⚠️ VEZIR ALERT — A-001 Budget Gate

Mission: m-007 (Deploy auth module)
Trigger: 4 budget gates triggered (limit: 3)
Stage: developer
Token usage: 185K / 300K (61.7%)

Details:
  • tool_call/Snapshot: 62K → approved (8s)
  • tool_call/Snapshot: 58K → approved (12s)
  • tool_call/Terminal: 15K → truncated to 10K
  • stage_input: 82K → approved (3s)

Action: Review mission complexity classification.
Dashboard: http://localhost:3000/monitoring/m-007
```

### Rule Configuration

```python
# Stored in config, operator-editable via API

ALERT_RULES = [
    {
        "id": "A-001",
        "name": "Budget gates per mission",
        "event": "budget.approval_required",
        "condition": "count_per_mission > threshold",
        "threshold": 3,
        "severity": "warning",
        "notify": ["log", "telegram"],
        "enabled": True,
    },
    # ...
]
```

CRUD via `/api/v1/alerts/rules`:
- `GET /rules` — list all rules
- `PUT /rules/{id}` — update threshold, enable/disable
- `POST /rules` — add custom rule
- `GET /active` — currently firing alerts
- `GET /history?from=...&to=...` — past alerts

---

## CI/CD Pipeline

### ci.yml — On Every Push/PR

```yaml
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.14' }
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: ruff check backend/
      - run: mypy backend/app/
      - run: pytest backend/tests/ -v --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v4

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npx tsc --noEmit
      - run: cd frontend && npx vitest run --coverage
```

### benchmark.yml — Performance Regression Gate

```yaml
name: Benchmark
on:
  push:
    branches: [main]
jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r backend/requirements.txt
      - run: python tools/benchmark_api.py --output benchmark-current.json
      - run: python tools/compare_benchmark.py benchmark-baseline.json benchmark-current.json --threshold 10
      # Fails if any endpoint regressed > 10%
```

### evidence.yml — Sprint Closure Automation

```yaml
name: Evidence Collection
on:
  workflow_dispatch:
    inputs:
      sprint: { description: 'Sprint number', required: true }
jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: mkdir -p evidence/sprint-${{ inputs.sprint }}
      - run: pytest backend/tests/ -v > evidence/sprint-${{ inputs.sprint }}/pytest-output.txt 2>&1 || true
      - run: cd frontend && npx vitest run > ../evidence/sprint-${{ inputs.sprint }}/vitest-output.txt 2>&1 || true
      - run: cd frontend && npx tsc --noEmit > ../evidence/sprint-${{ inputs.sprint }}/tsc-output.txt 2>&1 || true
      - run: ruff check backend/ > evidence/sprint-${{ inputs.sprint }}/ruff-output.txt 2>&1 || true
      - run: mypy backend/app/ > evidence/sprint-${{ inputs.sprint }}/mypy-output.txt 2>&1 || true
      - run: find . -type f -name "*.py" -o -name "*.tsx" -o -name "*.ts" | head -200 > evidence/sprint-${{ inputs.sprint }}/file-manifest.txt
      - uses: actions/upload-artifact@v4
        with:
          name: sprint-${{ inputs.sprint }}-evidence
          path: evidence/sprint-${{ inputs.sprint }}/
```

---

## Evidence Checklist (18 mandatory)

| # | File | Task |
|---|------|------|
| 1 | persistence-tests.txt | 16.0 |
| 2 | trace-query-tests.txt | 16.1 |
| 3 | metric-query-tests.txt | 16.2 |
| 4 | log-endpoint-tests.txt | 16.3 |
| 5 | dashboard-api-tests.txt | 16.4 |
| 6 | sse-live-test.txt | 16.5 |
| 7 | alert-engine-tests.txt | 16.6 |
| 8 | telegram-alert-test.txt | 16.7 |
| 9 | alert-api-tests.txt | 16.8 |
| 10 | dashboard-integration.txt | 16.12 |
| 11 | live-waterfall-test.txt | 16.13 |
| 12 | ci-pipeline-run.txt | 16.14 |
| 13 | benchmark-comparison.txt | 16.15 |
| 14 | evidence-auto-collect.txt | 16.16 |
| 15 | full-e2e-trace-to-dashboard.txt | 16.21 |
| 16 | alert-e2e-telegram.txt | 16.22 |
| 17 | ci-verification.txt | 16.23 |
| 18 | review-summary.md | 16.FINAL |

---

## Acceptance Criteria

### Dashboard API (16.0-16.5)
1. `/api/v1/dashboard/missions` returns filtered, paginated mission list
2. `/api/v1/dashboard/missions/{id}` returns full detail (stages, tools, budget, anomalies)
3. `/api/v1/telemetry/traces/{id}` returns span tree matching OTel data
4. `/api/v1/telemetry/logs` supports level/stage/event/time/search filters with pagination
5. SSE `/api/v1/dashboard/live` streams real-time events during running mission
6. Mission history persists across API restarts

### Alert System (16.6-16.9)
7. Alert engine evaluates 9 default rules on EventBus events
8. Critical alerts delivered to Telegram within 5 seconds
9. Alert rules CRUD via API
10. Alert history queryable by time range

### Dashboard Frontend (16.10-16.13)
11. Waterfall renders from real API data (not mock)
12. Log viewer queries real `/api/v1/telemetry/logs` with filters
13. Live mission updates waterfall in real-time via SSE
14. All filters (status, complexity, search) work against API query params

### CI/CD (16.14-16.17)
15. Push to main triggers CI: pytest + vitest + tsc + ruff + mypy
16. CI failure blocks merge
17. Benchmark regression > 10% fails CI
18. Evidence auto-collection produces valid sprint evidence files

### Foundation (16.18-16.20)
19. analyze_telemetry.py reads OTel trace data
20. Session model tracks operator identity
21. Jaeger export path documented (not deployed)

---

## Decision Dependencies

| Decision | Must Freeze Before | Status |
|----------|-------------------|--------|
| D-106 Persistence backend (JSON file vs SQLite) | Sprint 16 Task 16.0 | Not proposed |
| D-107 Alert severity levels and escalation policy | Sprint 16 Task 16.6 | Not proposed |
| D-108 CI/CD branch strategy (trunk-based vs feature branches) | Sprint 16 Task 16.14 | Not proposed |

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| SSE live feed adds complexity to frontend | Reuse existing SSE infrastructure from Mission Control |
| Alert spam if thresholds too sensitive | Default rules conservative. Operator adjusts via API. |
| Persistence layer scope creep (SQLite → ORM → migrations) | Keep it simple: JSON file store initially. SQLite only if query performance requires. D-106 decides. |
| CI/CD setup specific to GitHub | Abstract test commands in scripts/. CI yml just calls scripts. |
| Dashboard mock→real data mismatch | API response schema matches mock data schema exactly. Frontend code change = swap fetch URL. |

---

## Post-Sprint 16 State

Sprint 16 is the last stabilization sprint (Phase 5.5). After this:

| Capability | State |
|-----------|-------|
| Token governance | EventBus + 13 handlers + budget enforcement |
| Observability | OTel traces + metrics + structured logs, 28/28 coverage |
| Visibility | Dashboard with real data, live waterfall, filtered logs, alerts |
| Alerting | 9 rules, Telegram notification, configurable thresholds |
| CI/CD | Automated tests + lint + type check + benchmark on push |
| Evidence | Auto-collection pipeline |
| Repository | Concern-based backend, feature-based frontend, monorepo docs |
| Developer experience | Docker, dev scripts, pre-commit, CONTRIBUTING.md |

**Phase 6 starts with:** Clean architecture, full observability, automated quality gates, operator visibility. Ready for new features.

---

## Phase 6 Preview (Not Planned Yet)

Items that become possible after Sprint 16:

| Item | Why After Sprint 16 |
|------|-------------------|
| Browser E2E with Playwright | CI/CD pipeline exists to run it |
| OpenAPI → TypeScript SDK generation | Backend structured, API versioned |
| Multi-user / authentication | Session model foundation exists |
| Jaeger/Grafana deployment | OTel export path documented |
| Plugin system for custom handlers | EventBus architecture supports it |
| Mission templates / presets | Mission persistence exists |
| Cost tracking / billing | Token metrics recorded |
| Rate limiting | Alert engine can enforce |
| Webhook notifications (Slack, Discord) | Alert notifier extensible |

---

## Timeline

| Sprint | Duration | Focus | Status |
|--------|----------|-------|--------|
| 13 | ~2 weeks | D-102 minimum fix | Planned (v6) |
| 14A | ~3 weeks | EventBus + backend restructure | Advance plan |
| 14B | ~3 weeks | Frontend + tooling + monorepo | Advance plan |
| 15 | ~2 weeks | OTel: traces + metrics + logs | Advance plan |
| **16** | **~3 weeks** | **Dashboard API + alerts + CI/CD** | **Advance plan** |
| Phase 6 | TBD | New features | Not planned |
