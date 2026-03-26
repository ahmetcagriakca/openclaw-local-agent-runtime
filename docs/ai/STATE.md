# Current State

**Last updated:** 2026-03-26
**Active phase:** Phase 5D DONE (Sprint 12 — Polish + Phase 5 Closure) — implementation_status=done, closure_status=closed
**Note:** Sprint 7 (4.5-C) + Sprint 8 (5A-1) + Sprint 9 (5A-2) + Sprint 10 (5B) + Sprint 11 (5C) complete. Phase 2 deferred — single-user localhost, security hardening not urgent.
**Persistence:** State is file-persisted (state.json, mission.json). Resume not yet implemented.
**API:** Mission Control API on 127.0.0.1:8003 (FastAPI + Uvicorn). Schemas FROZEN (D-067). SSE on /api/v1/events/stream. Mutation endpoints (Sprint 11).
**Frontend:** React dashboard on localhost:3000 (Vite + Tailwind). SSE live updates + polling fallback + intervention buttons. Node.js 20 required.

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
| WSL Guardian | Operational (L2 — VM-level monitor) | `bin\oc-wsl-guardian.ps1` — Windows-side WSL + Vezir monitor |
| Telegram notifications | Operational | `bin\oc-health-notify.ps1` — alerts, startup reports, recovery |
| Agent Runner | Operational (multi-agent missions + 3 providers + 24 tools) | `agent/oc-agent-runner.py` |
| Mission Controller | Operational (9 governed roles, quality gates, state machine) | `agent/mission/controller.py` |
| Risk Engine | Operational | `agent/services/risk_engine.py` |
| Approval Service | Operational (Telegram deprecated D-092, Dashboard primary) | `agent/services/approval_service.py` |
| Approval Store | Operational | `agent/services/approval_store.py` |
| Artifact Store | Operational | `agent/services/artifact_store.py` |
| Context Assembler | Operational (5-tier delivery) | `agent/context/assembler.py` |
| Working Set Enforcer | Operational | `agent/context/working_set_enforcer.py` |
| Role Registry | Operational (9 canonical roles) | `agent/mission/role_registry.py` |
| Skill Contracts | Operational (10 contracts) | `agent/mission/skill_contracts.py` |
| Quality Gates | Operational (3 gates) | `agent/mission/quality_gates.py` |
| Feedback Loops | Operational (2 loops) | `agent/mission/feedback_loops.py` |
| Mission State Machine | Operational (10 states) | `agent/mission/mission_state.py` |
| Complexity Router | Operational (4 tiers) | `agent/mission/complexity_router.py` |
| Schema Validator | Operational | `agent/artifacts/schema_validator.py` |
| Policy Telemetry | Operational (20 event types) | `agent/context/policy_telemetry.py` |
| Mission Control API | Operational (read + write endpoints) | `agent/api/server.py` on :8003 |
| CSRF Middleware | Operational (D-089) | `agent/api/csrf_middleware.py` |
| Mutation Bridge | Operational (atomic signal artifacts) | `agent/api/mutation_bridge.py` |
| SSE Manager | Operational (broadcast, heartbeat 30s) | `agent/api/sse_manager.py` |

## Completed Phases

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Runtime Stabilization | Closed |
| Phase 1.5-A | Architecture Freeze | Closed |
| Phase 1.5-B | Legacy Cleanup | Closed |
| Phase 1.5-C | Bridge Contract Freeze | Closed |
| Phase 1.5-D | Security Baseline Freeze | Closed |
| Phase 1.5-E | Bridge Implementation | Closed |
| Phase 1.5-F | Exit Verification (local) | Closed |
| Phase TG-1R | Vezir Telegram Wiring | Closed |
| Phase 1.5-TG-R | Real Telegram Closure | **FULLY SEALED** |
| Phase 1.6 | Operational Monitoring | Closed |
| Phase 1.7 | Proactive Notifications | Closed |
| Phase 3-A | Agent-MCP Architecture Design Freeze | **FROZEN** |
| Phase 3-B | Core Agent Runner | Closed |
| Phase 3-C | Risk Engine + Approval Service | Closed |
| Phase 3-D | Full Tool Catalog + Typed Artifacts | Closed |
| Phase 3-E | Multi-Provider Support (GPT, Claude, Ollama) | Closed |
| Phase 3-F | Multi-Agent Foundation | Closed |
| Phase 4 Sprint 0+1 | Governance Enforcer (Working Set, Path Resolver) | Closed |
| Phase 4 Sprint 1H+2 | Governance Context (Context Assembler, Expansion Broker) | Closed |
| Phase 4 Sprint 2C | Integration Completion (Summary Cache, Artifact Identity) | Closed |
| Phase 4 Sprint 3 | Role Expansion (9 roles, 10 skill contracts, feedback loops) | Closed |
| Phase 4 Sprint 4 | Complexity Router + Discovery Governance | Closed |
| Phase 4 Sprint 5 | Quality Gates + State Machine + Approval Store | Closed |
| Phase 4 Sprint 5C | Controller Integration (state machine, gates, recovery, approval store) | Closed |
| Phase 4 Sprint 6 | Integration Test Suite (110/110 pass) | Closed |
| Phase 4 Sprint 6C | Closure Hardening (typed artifacts + model wiring) | Closed |
| Phase 4 Sprint 6D | Final Seal (structured extraction + strict approval) | Closed |
| Phase 4.5-A | Telemetry Tooling | Closed |
| Phase 4.5-B | E2E Validation | Closed |
| Phase 4.5-C (Sprint 7) | Operational Tuning | Closed |
| Phase 5A-1 (Sprint 8) | Backend Read Model | Closed |
| Phase 5A-2 (Sprint 9) | React Read-Only UI | Closed |
| Phase 5B (Sprint 10) | SSE Live Updates | Closed |
| Phase 5C (Sprint 11) | Intervention / Mutation | Closed |
| Phase 5D (Sprint 12) | Polish + Phase 5 Closure | Closed |

## Agent System (Phase 3-4)

### 9 Governed Roles

| Role | Default Skill | Tool Policy | Model | Discovery |
|------|---------------|-------------|-------|-----------|
| product-owner | requirement_structuring | no_tools | gpt-4o | forbidden |
| analyst | repository_discovery | read_only_14 | claude-sonnet | primary |
| architect | architecture_synthesis | read_only_14 | claude-sonnet | primary |
| project-manager | work_breakdown | no_tools | gpt-4o | forbidden |
| developer | targeted_code_change | dev_14 | claude-sonnet | forbidden |
| tester | test_validation | test_tools | claude-sonnet | forbidden |
| reviewer | quality_review | review_tools | claude-sonnet | forbidden |
| manager | summary_compression | no_tools | gpt-4o | forbidden |
| remote-operator | controlled_execution | operational | gpt-4o | forbidden |

### 10 Skill Contracts

| Skill | Output Artifact | Roles |
|-------|-----------------|-------|
| requirement_structuring | requirements_brief | product-owner |
| repository_discovery | discovery_map | analyst |
| architecture_synthesis | technical_design | architect |
| work_breakdown | work_plan | project-manager |
| targeted_code_change | code_delivery | developer |
| test_validation | test_report | tester |
| quality_review | review_decision | reviewer |
| controlled_execution | execution_result | remote-operator |
| summary_compression | artifact_summary | product-owner, manager |
| recovery_triage | recovery_decision | analyst |

### 3 Quality Gates

| Gate | After | Before | Checks |
|------|-------|--------|--------|
| Gate 1 | PO, Analyst, Architect, PM | Developer | Requirements + Design Approval |
| Gate 2 | Developer, Tester | Reviewer | Code Review + Testing |
| Gate 3 | All stages | Final | Artifact Validation |

### Complexity Routing

| Tier | Roles Used | Example |
|------|-----------|---------|
| Trivial | Analyst → Developer → Tester | Simple single-file change |
| Simple | + Reviewer | File change with review |
| Medium | + Product Owner, Architect, Manager | Structured requirements + design |
| Complex | Full 9-role pipeline | Complete project planning |

## Caller Paths

```
Agent path (primary):
Telegram user (8654710624)
  -> Vezir (WSL Ubuntu-E)
  -> /home/akca/bin/oc-agent-run (Python)
  -> agent/oc-agent-runner.py (Windows)
     Single-agent: GPT-4o/Claude/Ollama + 24 tools
     Mission mode: MissionController
       -> Complexity Router (trivial→complex)
       -> 9 Governed Roles
       -> Quality Gates (3) + Feedback Loops (2)
       -> Context Assembler (5-tier delivery)
       -> Working Set Enforcer (bounded filesystem)
  -> Response -> Telegram

Legacy path (predefined tasks):
Telegram user (8654710624)
  -> Vezir (WSL Ubuntu-E)
  -> /home/akca/bin/oc-bridge-submit (Python)
  -> /home/akca/bin/oc-bridge-call (Bash)
  -> pwsh.exe -File bridge/oc-bridge.ps1 (Windows)
  -> oc-task-enqueue.ps1 (runtime)
```

## Scheduled Tasks (Windows)

| Task | Trigger | Purpose |
|------|---------|---------|
| VezirTaskWorker | AtLogOn | Ephemeral -RunOnce worker |
| VezirRuntimeWatchdog | Every 15min | Health + stuck task + worker kick |
| VezirStartupPreflight | AtBoot | Stale recovery + layout validation |
| VezirWmcpServer | AtLogOn | windows-mcp HTTP server on :8001 |
| VezirWslGuardian | AtLogOn | WSL + Vezir active guardian (30s check, auto-restart, Telegram alerts) |
| VezirDashboard | Removed | Legacy dashboard removed (D-097, Sprint 13) |

## Architectural Decisions

101 frozen decisions (D-001 through D-101). Decision debt zero. See `docs/ai/DECISIONS.md`.

## Test Evidence

- 170 tests across Sprint 5C (70) + Sprint 6D (41) + Phase 4.5-A (18) + Sprint 8 API (41) — 0 failures
- 110 integration tests in Sprint 6 (110/110 pass)
- Sprint 7: 129 tests, 0 failures
- Sprint 8: 170 tests (129 legacy + 41 API), 0 failures
- Sprint 9: 18 Vitest frontend tests (4 files), 0 failures. tsc 0 errors. ESLint 0 errors. Production build success.
- Sprint 10: Backend 114 tests (100 legacy + 14 SSE), 0 failures. Frontend 29 Vitest tests (6 files), 0 failures.
- Sprint 11: Backend 195 tests (includes 11 contract), 0 failures. Frontend 29 Vitest tests, 0 failures.
- Sprint 12: Backend 234 tests (195 legacy + 39 E2E), 0 failures. Frontend 29 Vitest tests, 0 failures. Phase 5 scoreboard 15/15.

## Known Operational Notes

- WMCP `local-mcp-12345` API key is a known temporary localhost-only credential
- Bridge wrapper sourceUserId is hardcoded to single user (Phase 2 scope to make dynamic)
- Vezir exec-approvals prompt on first use of each bridge wrapper
- `telegram/oc-telegram-bot.py` is superseded by Vezir path — removed from repo
- WSL stability: two-layer monitoring (L1: systemd keepalive 20s, L2: WSL Guardian 30s) — see `docs/phase-reports/WSL-OPENCLAW-STABILITY-HARDENING.md`
- build_command string template debt — currently generates PowerShell via string concatenation (Phase 4.5 item)
- Approval flow uses strict `approve <id>` / `deny <id>` format (Sprint 6D). Simple "yes/no" deprecated — accepted only with single pending approval
- Telegram approval path deprecated with D-092 sunset warning (Sprint 11). Dashboard is primary approval channel.
