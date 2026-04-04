# CLAUDE.md — Vezir Platform

## Project

Vezir — governed multi-agent mission platform.
Windows 11 + WSL2 + Python 3.14 + PowerShell.
9 specialist roles, 3 quality gates, 11-state mission state machine.
24 MCP tools, 3 LLM providers (GPT-4o, Claude Sonnet, Ollama).

## Key Files

| File | Purpose |
|------|---------|
| `agent/mission/controller.py` | Mission orchestrator (sole executor) |
| `agent/mission/specialists.py` | 9 role specialist prompts |
| `agent/mission/quality_gates.py` | 3 quality gates |
| `agent/api/server.py` | Vezir API (FastAPI on :8003) |
| `agent/telegram_bot.py` | Telegram bot poller |
| `agent/observability/` | OTel tracing + metrics + structured logging |
| `agent/persistence/` | Mission/trace/metric stores (JSON file) |
| `frontend/` | React dashboard on :3000 (Vite + Tailwind, Node.js 20) |
| `bridge/oc-bridge.ps1` | PowerShell bridge to Windows |
| `config/capabilities.json` | Capability manifest (auto-generated) |

## Documentation

| Doc | Purpose |
|-----|---------|
| `docs/ai/STATE.md` | Canonical system state |
| `docs/ai/NEXT.md` | Roadmap + carry-forward |
| `docs/ai/DECISIONS.md` | Frozen decisions (D-001→D-130, D-126 skipped) |
| `docs/ai/GOVERNANCE.md` | Sprint governance rules |
| `docs/ai/BACKLOG.md` | Open backlog items |
| `docs/ai/handoffs/current.md` | Session context (supplementary) |
| `docs/ai/reviews/` | GPT review verdicts |
| `docs/decisions/` | Formal decision records |

## Build & Test

```bash
# Backend (1128 tests)
cd agent && python -m pytest tests/ -v

# Frontend (217 tests, requires Node.js 20)
cd frontend && npx tsc --noEmit
cd frontend && npx vitest run

# Playwright E2E (13 tests)
cd frontend && npx playwright test

# Total: 1128 backend + 217 frontend + 13 Playwright = 1358 (D-131)

# Preflight (all-in-one local CI)
bash tools/preflight.sh

# Benchmark (evidence-only, D-109)
python tools/benchmark_api.py
```

## Port Map

| Port | Service |
|------|---------|
| 8001 | WMCP (Windows MCP Proxy) |
| 8003 | Vezir API (FastAPI) |
| 3000 | Vezir UI (React) |
| 9000 | Math Service |

## Hard Rules

- Turkish conversation, English technical terms.
- Every task produces concrete output. No chat-only.
- Blocking fixes first.
- Frozen decisions use D-XXX format.
- Atomic writes: temp → fsync → os.replace().
- Source precedence: state.json > mission.json, summary > telemetry.
- Every sprint ends with git commit + push. Not closed without push.
- `closure_status=closed` = operator-only.

## Session Protocol

1. Read `docs/ai/handoffs/current.md` + `docs/ai/state/open-items.md`
2. Work autonomously, commit at milestones
3. Update handoff + open-items at session end

## Do Not

- Do not replace existing architecture with "clean rewrite."
- Do not write to files without atomic_write_json().
- Do not claim "done" without verification evidence.
- Do not leave "to be clarified later" in any task.
