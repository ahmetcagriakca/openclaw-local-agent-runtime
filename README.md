# OpenClaw Local Agent Runtime

Personal AI-powered Windows automation system with Telegram integration. An AI agent (GPT-4o) interprets natural language requests, selects from 24 specialized tools, executes them via MCP on Windows, and returns formatted responses — all controllable from Telegram.

## Architecture

```
User (Telegram)
  -> OpenClaw (WSL Ubuntu-E, conversation gateway)
  -> Agent Runner (Windows, GPT-4o + 24 tools)
     -> Risk Engine (deterministic risk classification)
     -> Approval Service (Telegram approval for high-risk ops)
     -> MCP Client -> WMCP Server (localhost:8001) -> PowerShell
     -> Artifact Store (typed output)
  -> Response -> Telegram

Legacy path (predefined tasks):
  -> Bridge (stateless adapter) -> oc runtime (task queue/worker)
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Agent Runner | `agent/oc-agent-runner.py` | GPT-4o orchestrator with multi-turn tool calling |
| Tool Catalog | `agent/services/tool_catalog.py` | 24 named tools mapped to PowerShell commands |
| Risk Engine | `agent/services/risk_engine.py` | Deterministic risk classification + blocked patterns |
| Approval Service | `agent/services/approval_service.py` | Telegram-based approval for high-risk operations |
| Artifact Store | `agent/services/artifact_store.py` | Typed output (12 artifact types) |
| MCP Client | `agent/services/mcp_client.py` | HTTP client for windows-mcp server |
| GPT Provider | `agent/providers/gpt_provider.py` | OpenAI GPT-4o with provider abstraction |
| Bridge | `bridge/oc-bridge.ps1` | Stateless adapter for legacy task system |
| oc runtime | `bin/` | Task queue, worker, watchdog, health engine |
| WSL Guardian | `bin/oc-wsl-guardian.ps1` | Active WSL + OpenClaw monitor with auto-restart |

## Repository Structure

```
agent/                 AI agent system (Phase 3)
  oc-agent-runner.py     Main orchestrator
  providers/             LLM provider abstraction (GPT-4o, extensible)
  services/              MCP client, tool catalog, risk engine, approval, artifacts, audit
bin/                   Runtime scripts (worker, watchdog, enqueue, health, dashboard, etc.)
bridge/                Bridge entrypoint + allowlist
wsl/                   WSL-side wrappers (oc-agent-run, oc-approve, bridge wrappers)
actions/               Action scripts + manifest
defs/tasks/            Task definitions
config/                Environment variable templates
logs/                  Audit logs, approval records, session artifacts
results/               Agent output files (screenshots, generated files)
docs/ai/               Living project state (STATE, NEXT, DECISIONS)
docs/architecture/     Frozen design documents
docs/phase-reports/    Completed phase reports
```

## Tool Catalog (24 Tools)

| Tool | Risk | Description |
|------|------|-------------|
| get_system_info | low | CPU, RAM, disk, uptime |
| list_processes | low | Top N processes by CPU |
| read_file | low | Read file contents |
| write_file | medium | Write to results/ directory |
| list_directory | low | List directory contents |
| search_files | low | Search files by name pattern |
| find_in_files | low | Search text inside files |
| get_clipboard | low | Read clipboard |
| set_clipboard | medium | Write to clipboard |
| open_application | medium | Open allowed apps |
| open_url | medium | Open URL in browser |
| close_application | high | Kill process (requires approval) |
| take_screenshot | low | Capture screen |
| lock_screen | medium | Lock workstation |
| system_shutdown | critical | Shutdown (requires approval) |
| system_restart | critical | Restart (requires approval) |
| get_system_health | low | OpenClaw health check (6 components) |
| get_process_details | low | Detailed process info |
| get_network_info | low | IP addresses + connectivity |
| list_scheduled_tasks | low | Windows scheduled tasks |
| submit_runtime_task | medium | Submit task to oc runtime |
| check_runtime_task | low | Check runtime task status |
| mcp_status | low | Check WMCP server health |
| mcp_restart | high | Restart WMCP server (requires approval) |

## Risk Levels

| Risk | Action | Examples |
|------|--------|----------|
| low | Auto-execute | System info, file read, process list |
| medium | Auto-execute | File write, clipboard, open app |
| high | Telegram approval required | Close app, restart MCP |
| critical | Telegram approval required | Shutdown, restart |
| blocked | Never executed | Dangerous patterns (Invoke-Expression+http, encodedcommand, etc.) |

## Quick Start

### Prerequisites

- Windows 11 with WSL2 (Ubuntu)
- Python 3.14+ on Windows
- OpenAI API key (`OPENAI_API_KEY` environment variable)
- OpenClaw installed in WSL

### Run Agent

```powershell
# Install dependencies
pip install openai requests

# Test agent (from PowerShell with OPENAI_API_KEY set)
python agent/oc-agent-runner.py -m "CPU ve RAM kullanımı ne?"
python agent/oc-agent-runner.py -m "en çok CPU kullanan 5 process ne?"
python agent/oc-agent-runner.py -m "ekran görüntüsü al"
python agent/oc-agent-runner.py -m "OpenClaw scheduled task'ları listele"
```

### Approve High-Risk Operations

```powershell
# Agent requests approval via Telegram for high-risk tools
# Approve from Telegram: reply "evet" or "approve apv-XXX"
# Or from terminal:
python bin/oc-approve.py list
python bin/oc-approve.py approve apv-XXXXXXXX-XXXXX
```

### Start Infrastructure

```powershell
# Start WMCP server (required for agent)
pwsh -NoProfile -ExecutionPolicy Bypass -File bin\start-wmcp-server.ps1

# Start web dashboard (optional, port 8002)
pwsh -NoProfile -ExecutionPolicy Bypass -File bin\start-dashboard.ps1
```

## Scheduled Tasks

| Task | Trigger | Purpose |
|------|---------|---------|
| OpenClawTaskWorker | AtLogOn | Ephemeral -RunOnce worker |
| OpenClawRuntimeWatchdog | Every 15min | Health + stuck task + worker kick |
| OpenClawStartupPreflight | AtBoot | Stale recovery + layout validation |
| OpenClawWmcpServer | AtLogOn | windows-mcp HTTP server on :8001 |
| OpenClawWslGuardian | AtLogOn | WSL + OpenClaw active guardian |
| OpenClawDashboard | AtLogOn | Web dashboard on :8002 |

## Completed Phases

| Phase | Scope |
|-------|-------|
| 1 | Runtime Stabilization |
| 1.5 | Bridge + Security Baseline |
| 1.6 | Operational Monitoring (WSL Guardian) |
| 1.7 | Proactive Telegram Notifications |
| 3-A | Agent-MCP Architecture Design Freeze |
| 3-B | Core Agent Runner (GPT-4o + MCP) |
| 3-C | Risk Engine + Telegram Approval Service |
| 3-D | Full Tool Catalog (24 tools) + Typed Artifacts |

**Next:** Phase 3-E — Multi-Provider (Claude + Ollama)

## Documentation

- `docs/ai/STATE.md` — Current system state and component status
- `docs/ai/NEXT.md` — Next phase plan
- `docs/ai/DECISIONS.md` — Architectural decisions (frozen)
- `docs/phase-reports/` — Detailed phase completion reports
