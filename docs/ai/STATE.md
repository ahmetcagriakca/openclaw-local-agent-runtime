# Current State

**Last updated:** 2026-04-06
**Active phase:** Phase 9 — Sprint 72 closed
**Doc model:** This file is canonical for system state. Session context lives in `docs/ai/handoffs/current.md`.
**Note:** All sprints through 53 closed. S54 deferred. S55-S71 closed. All P1 backlog items complete (50/50). Phase 9 active (S69+). Phase 8 complete (S60-S68). 139 frozen decisions + 2 superseded (D-001 → D-142, D-126 skipped, D-132 deferred, D-082/D-098 superseded). Governance: 20-step closure checklist.
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
| Mission State Machine | Operational (11 states) | `agent/mission/mission_state.py` |
| Complexity Router | Operational (4 tiers) | `agent/mission/complexity_router.py` |
| Mission Scheduler | Operational (cron-based, D-120/B-101) | `agent/schedules/` |
| Mission Presets | Operational (3 built-in, B-103) | `config/templates/preset_*.json` |
| Dead Letter Queue | Operational (B-106, 7 API endpoints) | `agent/persistence/dlq_store.py` + `agent/api/dlq_api.py` |
| Resilience Engine | Operational (backoff, circuit breaker, poison pill) | `agent/mission/resilience.py` |
| Auto-Resume | Operational (--resume, --auto-resume) | `agent/mission/auto_resume.py` |
| Cost Dashboard API | Operational (3 endpoints: summary, missions, trends) | `agent/api/cost_api.py` |
| Agent Health API | Operational (4 endpoints: providers, roles, matrix, performance) | `agent/api/agents_api.py` |
| Mission Control API | Operational (~123 endpoints) | `agent/api/server.py` on :8003 |
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
| Sprint 21 | Closure + Archive Automation | Closed |
| Sprint 22 | Automation Hardening / Operationalization | Closed |
| Sprint 23 | Governance Debt Closure (status-sync, pr-validator, stale refs) | Closed |
| Sprint 24 | CI Gate Hardening (benchmark, Playwright, Dependabot, secrets) | Closed |
| Sprint 25 | Contract Execution (archive, OpenAPI SDK, component tests) | Closed |
| Sprint 26 | Foundation Hardening (D-115/116, Docker, SDK drift, live E2E) | Closed |
| Sprint 27 | Identity Foundation (D-117 auth, frontend auth, mock LLM, Docker CI) | Closed |
| Sprint 28 | Auth Hardening (integration tests, token expiry, Jaeger/Grafana) | Closed |
| Sprint 29 | Plugin Foundation (D-118, plugin registry, webhook, session UI) | Closed |
| Sprint 30 | Repeatable Automation (D-119/120/121, templates, timeline, guardrails) | Closed |
| Sprint 31 | Backlog Pipeline (D-122, import tool, generator, sprint bridge) | Closed |
| Sprint 32 | API Throttling + Idempotency (B-005, B-012) | Closed |
| Sprint 33 | Project V2 Contract Hardening (D-123/124/125) | Closed |
| Sprint 34 | Closure Tooling Hardening (D-127) | Closed |
| Sprint 35 | Security Hardening Baseline (D-128, B-003, B-004) | Closed |
| Sprint 36 | Encrypted Secrets + Audit Integrity (D-129, B-006, B-008) | Closed |
| Sprint 42 | Runner Resilience (B-106: DLQ, backoff, circuit breaker, auto-resume) | Closed |
| Sprint 43 | Tech Debt Eritme (Pydantic, bare pass, frontend tests, feature flag) | Closed |
| Sprint 44 | CI/CD & Repo Quality (Python fix, 22 CodeQL fix, coverage, dependabot) | Closed |
| Sprint 45 | B-104 Template Parameter UI (last P1) | Closed |
| Sprint 46 | B-105 Cost Dashboard + B-108 Agent Health View | Closed |
| Sprint 47 | Frontend Quality & UX Hardening (12 issues) | Closed |
| Sprint 48 | Debt-First Hybrid (governance + runtime contract + data normalization + OTel) | Closed |
| Sprint 49 | Policy Engine + Operational Hygiene (B-107, B-026, B-119) | Closed |
| Sprint 50 | API Hardening + DevEx + Governance Debt (policy write API, B-109, D-132, RFC 9457) | Closed |
| Sprint 51 | Contract Testing + Data Safety + Artifact Access (B-110, B-022, B-016) | Closed |
| Sprint 52 | Recovery + Replay + Seed Demo (B-023, B-111, B-112) | Closed |
| Sprint 53 | Docs-as-Product + Policy Context + Timeout Contract (B-113, B-013, B-014) | Closed |
| Sprint 54 | Audit Export + Dynamic Source + Heredoc Cleanup (B-115, B-018, B-025) | Deferred (not implemented, tasks → S55) |
| Sprint 55 | Audit Export + Dynamic Source + Heredoc Cleanup (B-115, B-018, B-025) | Closed |
| Sprint 56 | Task Dir Retention + .bak Cleanup + Intent Mapping (B-027, B-028, B-019) | Closed |
| Sprint 57 | Secret Rotation + Allowlist + Grafana Pack (B-007, B-009, B-117) | Closed |
| Sprint 58 | Knowledge Layer + Multi-tenant + WMCP Cred (B-114, B-116, B-010) | Closed |
| Sprint 59 | Plugin Marketplace / Discovery (B-118, D-136) | Closed |
| Sprint 60 | WSL2 <-> PowerShell Bridge Contract (D-137) | Closed |
| Sprint 61 | Approval Timeout=Deny + Escalation FSM (D-138) | Closed |
| Sprint 62 | Approval FSM Wiring + Decision Drift + Auth Quarantine (B-134, B-135, B-136) | Closed |
| Sprint 63 | Controller Decomposition Boundary + Budget Ownership Design (B-137, B-138, D-139) | Closed |
| Sprint 64 | Controller Extraction Phase 1 + Hard Budget Enforcement (B-139, B-140) | Closed |
| Sprint 65 | Mission Startup Recovery + Plugin Mutation Auth Boundary (B-141, B-142) | Closed |
| Sprint 66 | Persistence Boundary ADR + Tool Reversibility Metadata (B-143, B-144, D-140) | Closed |
| Sprint 67 | Enforcement Chain Doc + Mission Replay CLI (B-145, B-146) | Closed |
| Sprint 68 | Patch/Apply Contract Design (B-147, D-141) — Phase 8C | Closed |
| Sprint 69 | Operating Model Freeze + State Drift Guard (D-142) — Phase 9 | Closed |
| Sprint 70 | Validator/Closer Drift Hardening — Phase 9 | Closed |
| Sprint 71 | Intake Gate + Workflow Writer Enforcement — Phase 9 | Closed |
| Sprint 72 | Session Protocol Enforcement — Phase 9 | Closed |

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
| Sprint 36 | 521 tests, 0 fail | 75 tests, 0 TS errors | +63 backend, +46 frontend (S17-S36 cumulative) |
| Sprint 40 | 618 tests, 0 fail | 82 tests, 0 TS errors | +97 backend, +7 frontend (S37-S40 cumulative) |
| Sprint 41 | 618 tests, 0 fail | 82 tests, 0 TS errors | +1 guard test (atomic write compliance) |
| Sprint 42 | 669 tests, 0 fail | 82 tests, 0 TS errors | +51 backend (DLQ, resilience, auto-resume, G2 patch) |
| Sprint 43 | 682 tests, 0 fail | 168 tests, 0 TS errors | +13 backend (feature flags), +86 frontend (11 new files) |
| Sprint 46 | 705 tests, 0 fail | 215 tests, 0 TS errors | +23 backend (cost+agent APIs), +20 frontend (2 new pages) |
| Sprint 47 | 705 tests, 0 fail | 217 tests, 0 TS errors | +2 frontend (badge tests), format utils, 12 UX fixes |
| Sprint 48 | 736 tests, 0 fail | 217 tests, 0 TS errors | +31 backend (policy context, timeout, state machine) |
| Sprint 49 | 788 tests, 0 fail | 217 tests, 0 TS errors | +52 new (policy engine, DLQ retention, alert scoping). 13 Playwright. 1018 total |
| Sprint 50 | 821 tests, 0 fail | 217 tests, 0 TS errors | +33 new (policy write API, B-109 CLI, D-132 migration, RFC 9457). 13 Playwright. 1051 total |
| Sprint 51 | 871 tests, 0 fail | 217 tests, 0 TS errors | +50 new (contract tests, backup/restore, artifact API). 13 Playwright. 1101 total |
| Sprint 52 | 917 tests, 0 fail | 217 tests, 0 TS errors | +46 new (recovery, replay, seed demo). 13 Playwright. 1147 total |
| Sprint 53 | 992 tests, 0 fail | 217 tests, 0 TS errors | +75 new (docs gen, policyContext, timeout contract). 13 Playwright. 1222 total |
| Sprint 55 | 1057 tests, 0 fail | 217 tests, 0 TS errors | +65 new (audit export 43, sourceUserId 24, compat fix). 13 Playwright. 1287 total |
| Sprint 56 | 1128 tests, 0 fail | 217 tests, 0 TS errors | +71 new (retention 22, cleanup_bak 22, intent mapper 27). 13 Playwright. 1358 total |
| Sprint 57 | 1210 tests, 0 fail | 217 tests, 0 TS errors | +82 new (secret rotation 28, allowlist 24, grafana 30). 13 Playwright. 1440 total |
| Sprint 58 | 1300 tests, 0 fail | 217 tests, 0 TS errors | +90 new (knowledge 37, tenant 30, wmcp-cred 23). 13 Playwright. 1530 total |
| Sprint 59 | 1376 tests, 0 fail | 217 tests, 0 TS errors | +76 new (marketplace 38, API 21, installer 17). 13 Playwright. 1606 total |
| Sprint 60 | 1395 tests, 0 fail | 217 tests, 0 TS errors | +19 new (bridge contract enforcement 19). 13 Playwright. 1625 total |
| Sprint 61 | 1426 tests, 0 fail | 217 tests, 0 TS errors | +31 new (approval FSM 31). 13 Playwright. 1656 total |
| Sprint 62 | 1454 tests, 0 fail | 217 tests, 0 TS errors | +28 new (approval wiring 14, auth quarantine 14). 13 Playwright. 1684 total |
| Sprint 63 | 1454 tests, 0 fail | 217 tests, 0 TS errors | Design-only sprint (no new tests). 13 Playwright. 1684 total |
| Sprint 64 | 1494 tests, 0 fail | 217 tests, 0 TS errors | +40 new (persistence 11, recovery 8, budget 21). 13 Playwright. 1724 total |
| Sprint 65 | 1536 tests, 0 fail | 217 tests, 0 TS errors | +42 new (startup recovery 25, plugin auth 17). 13 Playwright. 1766 total |
| Sprint 66 | 1555 tests, 0 fail | 217 tests, 0 TS errors | +19 new (manifest invariant 7, policy enforcement 10, assertion updates 2). 13 Playwright. 1785 total |
| Sprint 67 | 1555 tests, 0 fail | 217 tests, 0 TS errors | Model B: docs + CLI tool only, no runtime change. 13 Playwright. 1785 total |
| Sprint 68 | 1555 tests, 0 fail | 217 tests, 0 TS errors | Model B: design-only (D-141), no runtime change. 13 Playwright. 1785 total |
| Sprint 69 | 1555 tests, 0 fail | 217 tests, 0 TS errors | +10 state-sync tests. 13 Playwright. 1795 total |
| Sprint 70 | 1555 tests, 0 fail | 217 tests, 0 TS errors | +21 root tests (validator+closer). 13 Playwright. 60 root. 1845 total |
| Sprint 71 | 1555 tests, 0 fail | 217 tests, 0 TS errors | +40 root tests (task-intake). 13 Playwright. 102 root. 1887 total |
| Sprint 72 | 1555 tests, 0 fail | 217 tests, 0 TS errors | +37 root tests (pre-impl-check). 13 Playwright. 139 root. 1924 total |

## Architectural Decisions

139 frozen + 2 superseded decisions (D-001 through D-142, D-126 skipped, D-132 deferred, D-082/D-098 superseded S62). See `docs/ai/DECISIONS.md`. Recent: D-141 patch/review/apply/revert contract (S68). D-142 intake-to-sprint operating model freeze (S69). Governance: 20-step closure checklist.

## Port Map

| Port | Service | Status |
|------|---------|--------|
| 8001 | WMCP (Windows MCP Proxy) | Active |
| 8002 | — | Removed (D-097, Sprint 13) |
| 8003 | Vezir API (FastAPI) | Active |
| 3000 | Vezir UI (React) | Active |
| 9000 | Math Service (example) | Active |
