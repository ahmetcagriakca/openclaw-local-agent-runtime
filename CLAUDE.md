# CLAUDE.md — Vezir Platform

## Project

Vezir — governed multi-agent mission platform (formerly OpenClaw).
Windows 11 + WSL2 Ubuntu-E + Python 3.14 + PowerShell.
9 specialist roles, 3 quality gates, 11-state mission state machine.
24 MCP tools, 3 LLM providers (GPT-4o, Claude Sonnet, Ollama).
Telegram bot integration, Math Service on :9000.

## Current State

- Phase 4.5-C: implementation_status=done, closure_status=closed (Sprint 7)
- Phase 5A-1: implementation_status=done, closure_status=closed (Sprint 8)
- Phase 5A-2: implementation_status=done, closure_status=closed (Sprint 9)
- Phase 5B: implementation_status=done, closure_status=closed (Sprint 10)
- Phase 5C: implementation_status=done, closure_status=closed (Sprint 11)
- Phase 5D: implementation_status=done, closure_status=closed (Sprint 12)
- Sprint 15: implementation_status=done, closure_status=closed (OTel Observability)
- Sprint 16: implementation_status=done, closure_status=closed (Presentation + CI/CD)
- Frozen decisions: D-001 → D-101 (decision debt zero)

## Last Completed Sprint

Sprint 16 — Presentation Layer + CI/CD Foundation (Phase 5.5 closure)

Outputs:
- Dashboard API: 15 new endpoints (missions, traces, metrics, logs, alerts, live SSE)
- Persistence layer: mission_store, trace_store, metric_store (JSON file)
- Alert system: 9 rules, rule engine, Telegram notification, CRUD API
- Frontend: MonitoringPage + 5 API hooks + live SSE feed
- CI/CD: 3 GitHub Actions (ci.yml, benchmark.yml, evidence.yml)
- Session model foundation (auth/session.py)
- Jaeger evaluation document (not deployed)
- 39 new tests, full suite: 457/458 PASS
- Decision debt zero: D-001→D-101 all frozen
- Backend 234 tests, Frontend 29 tests, 0 failures
- Decisions: D-097→D-101

## Key Reference Docs

- `docs/ai/STATE.md` — current system state
- `docs/ai/DECISIONS.md` — frozen decisions D-001 → D-096
- `docs/ai/PROCESS-GATES.md` — sprint governance rules (v4)
- `docs/ai/DECISION-DEBT-BURNDOWN.md` — debt payment plan
- `docs/sprints/sprint-12/` — Sprint 12 docs + artifacts
- `docs/ai/NEXT.md` — roadmap
- `docs/ai/BACKLOG.md` — backlog
- `docs/ai/PROTOCOL.md` — sprint + freeze protocols
- `tools/sprint-closure-check.sh` — closure evidence generator

## Architecture Quick Reference

```
Telegram → Vezir Bot → Agent Runner (Windows) → Mission Controller
  → 9 roles with quality gates → MCP → PowerShell

Port Map:
  8001  WMCP (Windows MCP Proxy)
  8002  (removed — was Legacy Health Dashboard, D-097)
  8003  Vezir API (FastAPI)
  3000  Vezir UI (React, requires Node.js 20)
  9000  Math Service (example deployable)
```

### Mission Flow
```
User goal → PO → Analyst → Architect → PM → Developer → Tester → Reviewer → Manager
            G1 (requirements)    G2 (code+test)    G3 (review)
```

### Key Files
```
agent/mission/controller.py        — mission orchestrator (sole executor)
agent/mission/specialists.py       — 9 role specialist prompts
agent/mission/quality_gates.py     — 3 quality gates
agent/mission/artifact_extractor.py — 3-layer artifact parse
agent/services/approval_service.py — approval handling
agent/services/policy_enforcer.py  — file system policy enforcement
agent/telegram_bot.py              — Telegram bot poller
agent/math_service/app.py          — example deployable service
bridge/oc-bridge.ps1               — PowerShell bridge to Windows
config/capabilities.json           — capability manifest (auto-generated)
```

## Working Rules

- Turkish conversation, English technical terms.
- Iterative: design → review → revise → freeze.
- Every task produces concrete output (file, code, doc). No chat-only.
- Blocking fixes first.
- Frozen decisions use D-XXX format.
- Unknown ≠ zero. Missing ≠ healthy.
- Atomic writes: temp → fsync → os.replace(). No raw json.dump to file.
- Source precedence: state.json > mission.json (status), summary > telemetry (forensics).
- Capability detection via config/capabilities.json, not heuristics.
- **Every sprint ends with git commit + push of all work (code, docs, evidence). A sprint is not considered closed without push.**

## Build & Test

```bash
# Backend tests (184 total: 70 sprint-5c + 86 legacy + 14 SSE + 14 api)
cd agent && python -m pytest tests/ -v

# Frontend (requires Node.js 20 — portable at C:\Users\AKCA\node20\)
$env:Path = "C:\Users\AKCA\node20\node-v20.18.1-win-x64;$env:Path"
cd frontend && npx tsc --noEmit        # 0 errors
cd frontend && npx vitest run           # 29 tests
cd frontend && npm run build            # production build

# E2E test
python tools/run_e2e_test.py --all

# Telemetry analysis
python tools/analyze_telemetry.py --last 5
```

## Phase 5 Progress (Vezir Dashboard)

"See Everything, Including What's Missing"

- ✅ Sprint 8: FastAPI backend on :8003
- ✅ Sprint 9: React UI on :3000
- ✅ Sprint 10: SSE live updates
- ✅ Sprint 11: Intervention (approve/deny from UI)
- ✅ Sprint 12: Polish + Phase 5 closure
- ✅ Post-Sprint 12: D-102 token budget, Telegram bot, Math Service, Vezir rebrand

## Do Not

- Do not replace existing architecture with "clean rewrite."
- Do not design from mock data. Use normalized API contract.
- Do not use Node.js 14 for frontend. Requires Node.js 20+ (Vite 6).
- Do not write to files without atomic_write_json().
- Do not treat UI mock structure as backend truth.
- Do not claim "done" without verification evidence.
- Do not leave "to be clarified later" in any task.
