# CLAUDE.md — OpenClaw Local Agent Runtime

## Project

OpenClaw Local Agent Runtime — governed multi-agent mission system.
Windows 11 + WSL2 Ubuntu-E + Python 3.14 + PowerShell.
9 specialist roles, 3 quality gates, 10-state mission state machine.
24 MCP tools, 3 LLM providers (GPT-4o, Claude Sonnet, Ollama).

## Current State

- Phase 4.5-C: COMPLETED (Sprint 7 — operational tuning, 10/10 tasks)
- Phase 5A-1: COMPLETED (Sprint 8 — backend read model, 17/17 tasks, 170 tests)
- Phase 5A-2: COMPLETED (Sprint 9 — React read-only UI, 10/10 tasks, 18 frontend tests)
- Phase 5B: COMPLETED (Sprint 10 — SSE live updates, 8/8 tasks, 114 backend + 29 frontend tests)
- Phase 5C: NEXT (Sprint 11 — intervention)
- Frozen decisions: D-059 → D-088 (29 decisions)

## Last Completed Sprint

Sprint 10 — Phase 5B: SSE Live Updates

Outputs:
- FileWatcher: mtime polling 1s (D-085), debounce 500ms/2s
- SSEManager: broadcast, heartbeat 30s, max 10 clients, event buffer 100
- SSE endpoint: GET /api/v1/events/stream, Last-Event-ID replay, D-087 localhost
- useSSE hook: EventSource, exponential backoff (D-088), polling fallback
- SSEContext + useSSEInvalidation: shared connection, per-page subscription
- ConnectionIndicator: 4-state (connecting/connected/reconnecting/polling)
- All 5 pages: SSE invalidation + polling fallback preserved
- Backend 114 tests, Frontend 29 tests, 0 failures
- Decisions: D-085 (polling watcher), D-086 (per-entity events), D-087 (localhost SSE), D-088 (backoff + fallback)

## Key Reference Docs

- `docs/ai/STATE.md` — current system state
- `docs/ai/DECISIONS.md` — frozen decisions D-001 → D-058
- `docs/ai/NEXT.md` — roadmap
- `docs/ai/BACKLOG.md` — backlog
- `docs/ai/PROTOCOL.md` — sprint + freeze protocols

## Architecture Quick Reference

```
Telegram → OpenClaw (WSL) → Agent Runner (Windows) → Mission Controller
  → 9 roles with quality gates → MCP → PowerShell

Port Map:
  8001  WMCP (Windows MCP Proxy)
  8002  Legacy Health Dashboard
  8003  Mission Control API (FastAPI, Sprint 8)
  3000  Mission Control UI (React, Sprint 9, requires Node.js 20)
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
- **Her sprint sonunda tüm çalışmalar (kod, doküman, evidence) git commit + push yapılır. Sprint, push yapılmadan kapatılmış sayılmaz.**

## Build & Test

```bash
# Backend tests (114 total, includes 14 SSE)
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

## Phase 5 Progress

Mission Control Center — "See Everything, Including What's Missing"

- ✅ Sprint 8: FastAPI backend on :8003 — D-061, D-065, D-067, D-068, D-070
- ✅ Sprint 9: React UI on :3000 — D-081, D-082, D-083, D-084
- ✅ Sprint 10: SSE live updates — D-085, D-086, D-087, D-088
- ⬜ Sprint 11: Intervention (approve/deny from UI)
- ⬜ Sprint 12: Polish + migration

## Do Not

- Do not replace existing architecture with "clean rewrite."
- Do not design from mock data. Use normalized API contract.
- Do not use Node.js 14 for frontend. Requires Node.js 20+ (Vite 6).
- Do not write to files without atomic_write_json().
- Do not treat UI mock structure as backend truth.
- Do not claim "done" without verification evidence.
- Do not leave "to be clarified later" in any task.
