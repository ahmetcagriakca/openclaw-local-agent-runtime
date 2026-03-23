# Current State

**Last updated:** 2026-03-23
**Active phase:** Phase 3-E — Multi-Provider Support (complete)
**Note:** Phase 2 deferred — single-user localhost, security hardening not urgent

---

## System Status

| Component | Status | Location |
|-----------|--------|----------|
| oc runtime | Operational | `C:\Users\AKCA\oc\bin\` |
| Bridge | Operational, validated | `C:\Users\AKCA\oc\bridge\oc-bridge.ps1` |
| WMCP server | Operational (manual start) | via `bin\start-wmcp-server.ps1` |
| OpenClaw gateway | Operational (WSL Ubuntu-E) | `/home/akca/.openclaw/` |
| Telegram channel | Connected, real user validated | User ID `8654710624` |
| WSL bridge wrappers | Operational | `/home/akca/bin/oc-bridge-*` |
| System health engine | Operational | `bin\oc-system-health.ps1` |
| Web dashboard | Operational (manual start) | via `bin\start-dashboard.ps1` on :8002 |
| WSL Guardian | Operational | `bin\oc-wsl-guardian.ps1` — active WSL + OpenClaw monitor |
| Telegram notifications | Operational | `bin\oc-health-notify.ps1` — alerts, startup reports, recovery |
| Agent Runner | Operational (GPT-4o active, Claude/Ollama ready) | `agent/oc-agent-runner.py` |
| Risk Engine | Operational | `agent/services/risk_engine.py` |
| Approval Service | Operational (Telegram) | `agent/services/approval_service.py` |
| Artifact Store | Operational | `agent/services/artifact_store.py` |

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
| Phase TG-1R | OpenClaw Telegram Wiring | Closed |
| Phase 1.5-TG-R | Real Telegram Closure | **FULLY SEALED** |
| Phase 1.6 | Operational Monitoring | Closed |
| Phase 1.7 | Proactive Notifications | Closed |
| Phase 3-A | Agent-MCP Architecture Design Freeze | **FROZEN** |
| Phase 3-B | Core Agent Runner | Closed |
| Phase 3-C | Risk Engine + Approval Service | Closed |
| Phase 3-D | Full Tool Catalog + Typed Artifacts | Closed |
| Phase 3-E | Multi-Provider Support | Closed |

## Canonical Caller Path

```
Telegram user (8654710624)
  -> OpenClaw (WSL Ubuntu-E)
  -> /home/akca/bin/oc-bridge-submit (Python)
  -> /home/akca/bin/oc-bridge-call (Bash)
  -> pwsh.exe -File bridge/oc-bridge.ps1 (Windows)
  -> oc-task-enqueue.ps1 (runtime)
```

## Scheduled Tasks (Windows)

| Task | Trigger | Purpose |
|------|---------|---------|
| OpenClawTaskWorker | AtLogOn | Ephemeral -RunOnce worker |
| OpenClawRuntimeWatchdog | Every 15min | Health + stuck task + worker kick |
| OpenClawStartupPreflight | AtBoot | Stale recovery + layout validation |
| OpenClawWmcpServer | AtLogOn | windows-mcp HTTP server on :8001 |
| OpenClawWslGuardian | AtLogOn | WSL + OpenClaw active guardian (30s check, auto-restart, Telegram alerts) |
| OpenClawDashboard | AtLogOn | Web dashboard HTTP server on :8002 |

## Known Operational Notes

- WMCP `local-mcp-12345` API key is a known temporary localhost-only credential
- Bridge wrapper sourceUserId is hardcoded to single user (Phase 2 scope to make dynamic)
- OpenClaw exec-approvals prompt on first use of each bridge wrapper
- `telegram/oc-telegram-bot.py` is superseded by OpenClaw path — removed from repo
