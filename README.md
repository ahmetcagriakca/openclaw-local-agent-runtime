# OpenClaw Local Agent Runtime

Personal task automation runtime with Telegram integration via OpenClaw.

## Architecture

```
User (Telegram)
  -> OpenClaw (WSL, conversation flow owner)
  -> Bridge (Windows, stateless adapter + trust boundary)
  -> oc runtime (Windows, sole task execution orchestrator)
  -> queue -> worker -> runner -> action -> result
```

## Repository Structure

```
bin/              Runtime scripts (worker, watchdog, enqueue, health, etc.)
bridge/           Bridge entrypoint + test + allowlist template
wsl/              WSL-side bridge wrappers (deployed to /home/akca/bin/)
actions/          Action scripts + manifest.json
defs/tasks/       Task definitions
config/           Environment variable templates
docs/ai/          Living project state (STATE, BACKLOG, DECISIONS, NEXT)
docs/architecture/ Frozen design documents
docs/phase-reports/ Completed phase reports
docs/tasks/       Historical task reports
```

## Quick Start

```powershell
# 1. Copy and configure allowlist
Copy-Item bridge\allowlist.example.json bridge\allowlist.json
# Edit with your real Telegram user ID

# 2. Start WMCP server
pwsh -NoProfile -ExecutionPolicy Bypass -File bin\start-wmcp-server.ps1

# 3. Test Bridge
pwsh -NoProfile -ExecutionPolicy Bypass -File bridge\oc-bridge.ps1 -RequestJson '{"operation":"get_health","source":"test","sourceUserId":"YOUR-ID","requestId":"test-1"}'
```

## Phases

| Phase | Status |
|-------|--------|
| Phase 1 — Runtime Stabilization | Closed |
| Phase 1.5 — Bridge + Security Baseline | Sealed |
| Phase 2 — Security / Policy Hardening | Next |
| Phase 3 — Productization | Planned |
| Phase 4 — Reproducibility / DR | Planned |
