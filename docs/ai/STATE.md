# Current State

**Last updated:** 2026-03-27
**Active phase:** Sprint 20 CLOSED — Project Integration + PR Traceability (2026-03-27)
**Doc model:** This file is canonical for system state. Session context lives in `docs/ai/handoffs/current.md`.
**Note:** All sprints through 16 closed. Phase 6 ready to start. Phase 2 deferred — single-user localhost, security hardening not urgent.
**Persistence:** State is file-persisted (state.json, mission.json). Mission history via persistence layer (Sprint 16).
**API:** Vezir API on 127.0.0.1:8003 (FastAPI + Uvicorn). Schemas FROZEN (D-067). SSE on /api/v1/events/stream. Dashboard API + Alert API + Telemetry Query API (Sprint 16).
**Frontend:** React dashboard on localhost:3000 (Vite + Tailwind). SSE live updates + polling fallback + intervention buttons + monitoring dashboard. Node.js 20 required.
**Observability:** OpenTelemetry traces (28/28 events), 17 metrics, structured JSON logs with trace correlation (Sprint 15). Alert engine with 9 rules + Telegram notification (Sprint 16).
**CI/CD:** GitHub Actions: ci.yml (test+lint), benchmark.yml (evidence-only, D-109), evidence.yml (manual evidence collection) (Sprint 16+17).

---

## System Status

| Component | Status | Location |
|-----------|--------|----------|
| oc runtime | Operational | `C:\Users\AKCA\oc\bin\` |
| Bridge | Operational, validated | `C:\Users\AKCA\oc\bridge\oc-bridge.ps1` |
| WMCP server | Operational (manual start) | via `bin\start-wmcp-server.ps1` |
| Vezir gateway | Operational (systemd managed, auto-restart) | `/home/akca/.openclaw/` via `openclaw.service` |
| WSL VM | Bounded (6GB RAM, 4GB swap, 30min idle timeout) | `C:\Users\AKCA\.wslconfig` |
| Vezir keepalive | Operational (20s health loop) | `wsl-openclaw-keepalive.service` |
| Telegram channel | Connected, real user validated | User ID `8654710624` |
| WSL bridge wrappers | Operational | `/home/akca/bin/oc-bridge-*` |
| System health engine | Operational | `bin\oc-system-health.ps1` |
| Web dashboard | Removed (D-097, Sprint 13) | Was `bin\start-dashboard.ps1` on :8002. Replaced by Vezir UI on :3000 |
| WSL Guardian | Operational (L2 — VM-level monitor) | `bin\oc-wsl-guardian.ps1` |
| Telegram notifications | Operational | `bin\oc-health-notify.ps1` |
| Agent Runner | Operational (multi-agent missions + 3 providers + 24 tools) | `agent/oc-agent-runner.py` |
| Mission Controller | Operational (9 governed roles, quality gates, state machine) | `agent/mission/controller.py` |
| EventBus | Operational (28 event types, 14 governance handlers) | `agent/events/bus.py` |
| OTel TracingHandler | Operational (28/28 event coverage) | `agent/observability/tracing.py` |
| OTel MetricsHandler | Operational (17 instruments) | `agent/observability/meters.py` |
| StructuredLogHandler | Operational (JSON + trace context) | `agent/observability/structured_logging.py` |
| Alert Engine | Operational (9 rules, Telegram notification) | `agent/observability/alert_engine.py` |
| Persistence Layer | Operational (mission, trace, metric stores) | `agent/persistence/` |
| Dashboard API | Operational (15 new endpoints) | `agent/api/dashboard_api.py` + `telemetry_query_api.py` + `alerts_api.py` |
| Risk Engine | Operational | `agent/services/risk_engine.py` |
| Approval Service | Operational (Dashboard primary, Telegram deprecated D-092) | `agent/services/approval_service.py` |
| Context Assembler | Operational (5-tier delivery) | `agent/context/assembler.py` |
| Role Registry | Operational (9 canonical roles) | `agent/mission/role_registry.py` |
| Quality Gates | Operational (3 gates) | `agent/mission/quality_gates.py` |
| Mission State Machine | Operational (10 states) | `agent/mission/mission_state.py` |
| Complexity Router | Operational (4 tiers) | `agent/mission/complexity_router.py` |
| Mission Control API | Operational (~35 endpoints) | `agent/api/server.py` on :8003 |
| SSE Manager | Operational (broadcast, heartbeat 30s) | `agent/api/sse_manager.py` |
| Session Model | Foundation (operator identity, no auth flow) | `agent/auth/session.py` |
| CI/CD Pipeline | 7 GitHub Actions workflows | `.github/workflows/` |
| Branch Protection | Active on main (require PR, no direct push) | GitHub Settings |
| Issue Automation | plan.yaml → issues + issues.json via workflow | `.github/workflows/issue-from-plan.yml` |

## Completed Phases

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Runtime Stabilization | Closed |
| Phase 1.5 | Bridge + Security + Telegram | Closed |
| Phase 1.6-1.7 | Monitoring + Notifications | Closed |
| Phase 3 | Agent-MCP Architecture (6 sub-phases) | Closed |
| Phase 4 | Governance (10 sprints: 0→6D) | Closed |
| Phase 4.5 (Sprint 7) | Telemetry + E2E + Operational Tuning | Closed |
| Phase 5A-1 (Sprint 8) | Backend Read Model | Closed |
| Phase 5A-2 (Sprint 9) | React Read-Only UI | Closed |
| Phase 5B (Sprint 10) | SSE Live Updates | Closed |
| Phase 5C (Sprint 11) | Intervention / Mutation | Closed |
| Phase 5D (Sprint 12) | Polish + Phase 5 Closure | Closed |
| Sprint 13 | Stabilization (D-102 minimum fix) | Closed |
| Sprint 14A | EventBus + Backend Restructure | Closed |
| Sprint 14B | Frontend Restructure + Tooling | Closed |
| Sprint 15 | OTel Observability (traces + metrics + logs) | Closed |
| Sprint 16 | Presentation Layer + CI/CD (Phase 5.5 closure) | Closed |
| Sprint 17 | Phase 6 Controlled Start (CI fix + doc alignment) | Closed |
| Sprint 18 | Repo Cleanup (source-of-truth compression) | Closed |
| Sprint 19 | Single-Repo Automation MVP (plan.yaml + issues + branches) | Closed |
| Sprint 20 | Project Integration + PR Traceability | Closed |

## Test Evidence

| Sprint | Backend | Frontend | Notes |
|--------|---------|----------|-------|
| Sprint 12 | 234 tests, 0 fail | 29 tests | Phase 5 scoreboard 15/15 |
| Sprint 13 | 225 tests, 0 fail | — | +30 new tests |
| Sprint 14A | 353 tests, 0 fail | — | +132 new (EventBus 120, quality 12) |
| Sprint 14B | 392 tests, 0 fail | 29 tests | Frontend restructure |
| Sprint 15 | 419 tests, 0 fail | — | +27 new (OTel coverage + E2E) |
| Sprint 16 | 458 tests, 0 fail | 29 tests, 0 TS errors | +39 new (persistence, API, alerts) |
| **Cleanup** | **458 tests, 0 fail** | **0 TS errors** | **Ruff 0 errors, 169 lint fixes** |

## Architectural Decisions

114 frozen decisions (D-001 through D-114). See `docs/ai/DECISIONS.md`. Governance rules in `docs/ai/GOVERNANCE.md` (D-112).

## Port Map

| Port | Service | Status |
|------|---------|--------|
| 8001 | WMCP (Windows MCP Proxy) | Active |
| 8002 | — | Removed (D-097, Sprint 13) |
| 8003 | Vezir API (FastAPI) | Active |
| 3000 | Vezir UI (React) | Active |
| 9000 | Math Service (example) | Active |
