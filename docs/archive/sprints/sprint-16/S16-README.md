# Sprint 16 — Presentation Layer + CI/CD Foundation

**implementation_status:** done
**closure_status:** closed (operator sign-off: 2026-03-27)
**Owner:** AKCA (operator)
**Implementer:** Claude Code

---

## Goal

Connect measurement to visibility. Operator sees everything. Automated quality gates. Phase 5.5 closure sprint.

## Scope

**5 parallel tracks:**
- Track 0: Dashboard API (persistence + query + endpoints + live SSE)
- Track 1: Alert system (engine + Telegram + API + 9 default rules)
- Track 2: Dashboard frontend (MonitoringPage + API hooks + SSE)
- Track 3: CI/CD pipeline (3 GitHub Actions workflows)
- Track 4: Foundation (analyze_telemetry + session model + Jaeger doc)

## Task Summary

### Track 0: Dashboard API (16.0-16.5)

| Task | Description | Size | Status |
|------|-------------|------|--------|
| 16.0 | Persistence layer: mission_store.py | M | DONE |
| 16.1 | Trace query layer: trace_store.py | M | DONE |
| 16.2 | Metric query layer: metric_store.py | M | DONE |
| 16.3 | Log query endpoint: /api/v1/telemetry/logs | M | DONE |
| 16.4 | Dashboard endpoints: /missions, /summary | M | DONE |
| 16.5 | Live mission SSE: /api/v1/dashboard/live | M | DONE |

### Track 1: Alert System (16.6-16.9)

| Task | Description | Size | Status |
|------|-------------|------|--------|
| 16.6 | Alert rules engine | M | DONE |
| 16.7 | Telegram alert notification | S | DONE |
| 16.8 | Alert API: CRUD + active + history | M | DONE |
| 16.9 | 9 default alert rules | S | DONE |

### Track 2: Dashboard Frontend (16.10-16.13)

| Task | Description | Size | Status |
|------|-------------|------|--------|
| 16.10 | Extract monitoring components | M | DONE |
| 16.11 | API hooks: useTraces, useMetrics, useLogs, useMissions, useLiveMission | M | DONE |
| 16.12 | MonitoringPage with real API data | L | DONE |
| 16.13 | Live event feed via SSE | M | DONE |

### Track 3: CI/CD Pipeline (16.14-16.17)

| Task | Description | Size | Status |
|------|-------------|------|--------|
| 16.14 | ci.yml: pytest + vitest + tsc + ruff | M | DONE |
| 16.15 | benchmark.yml: regression gate | S | DONE |
| 16.16 | evidence.yml: auto-collect | M | DONE |
| 16.17 | compare_benchmark.py tool | S | DONE |

### Track 4: Foundation (16.18-16.20)

| Task | Description | Size | Status |
|------|-------------|------|--------|
| 16.18 | analyze_telemetry.py OTel integration | M | DONE |
| 16.19 | Session/operator model | S | DONE |
| 16.20 | Jaeger evaluation document | S | DONE |

**24/24 implementation tasks complete.**

## Files Created (24 new)

| File | Purpose |
|------|---------|
| `agent/persistence/__init__.py` | Module exports |
| `agent/persistence/mission_store.py` | Mission history CRUD |
| `agent/persistence/trace_store.py` | OTel trace storage |
| `agent/persistence/metric_store.py` | Metric snapshot storage |
| `agent/api/dashboard_api.py` | Dashboard endpoints + live SSE |
| `agent/api/telemetry_query_api.py` | Trace/metric/log query endpoints |
| `agent/api/alerts_api.py` | Alert rules CRUD + active/history |
| `agent/observability/alert_engine.py` | Rule evaluation engine |
| `agent/observability/alert_notifier.py` | Telegram notification dispatch |
| `agent/auth/__init__.py` | Auth module exports |
| `agent/auth/session.py` | Operator session model |
| `agent/tests/test_sprint16.py` | 39 tests |
| `agent/tools/compare_benchmark.py` | Benchmark regression comparison |
| `frontend/src/features/monitoring/index.ts` | Feature barrel exports |
| `frontend/src/features/monitoring/MonitoringPage.tsx` | Dashboard page |
| `frontend/src/features/monitoring/useTraces.ts` | Trace API hook |
| `frontend/src/features/monitoring/useMetrics.ts` | Metrics API hook |
| `frontend/src/features/monitoring/useLogs.ts` | Log query hook |
| `frontend/src/features/monitoring/useMissions.ts` | Dashboard missions hook |
| `frontend/src/features/monitoring/useLiveMission.ts` | SSE live events hook |
| `.github/workflows/ci.yml` | CI: test + lint + type check |
| `.github/workflows/benchmark.yml` | Performance regression gate |
| `.github/workflows/evidence.yml` | Sprint evidence auto-collect |
| `docs/JAEGER-EVALUATION.md` | Jaeger export path evaluation |

## API Endpoints Added (15)

| Method | Path | Purpose |
|--------|------|---------|
| GET | /dashboard/missions | Filtered, paginated mission list |
| GET | /dashboard/missions/{id} | Full mission detail |
| GET | /dashboard/summary | KPI summary |
| GET | /dashboard/live | SSE live events |
| GET | /telemetry/traces | List traces |
| GET | /telemetry/traces/{id} | Get trace span tree |
| GET | /telemetry/metrics/current | Current metrics |
| GET | /telemetry/metrics/history | Historical metrics |
| GET | /telemetry/logs | Filtered log query |
| GET | /alerts/rules | List alert rules |
| GET | /alerts/rules/{id} | Get rule |
| PUT | /alerts/rules/{id} | Update rule |
| POST | /alerts/rules | Create rule |
| GET | /alerts/active | Active alerts |
| GET | /alerts/history | Alert history |

## Test Results

| Suite | Count | Status |
|-------|-------|--------|
| Sprint 16 new | 39 | All pass |
| Full backend | 458 | All pass |
| Frontend TypeScript | — | 0 errors |

## Evidence

18 evidence files in `docs/sprints/sprint-16/evidence/`.
