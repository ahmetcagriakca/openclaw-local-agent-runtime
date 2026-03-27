# Vezir Local Agent Runtime

Personal AI-powered Windows automation system with Telegram integration. 9 governed agent roles orchestrated by Mission Controller with quality gates, feedback loops, and artifact-driven context economy. Supports GPT-4o, Claude, and Ollama providers with 24 specialized tools executed via MCP on Windows.

## Architecture

```
User (Telegram)h
  -> Vezir (WSL Ubuntu-E, conversation gateway)
  -> Agent Runner (Windows, multi-provider)
     Single-agent: GPT-4o/Claude/Ollama + 24 tools
     Mission mode: MissionController
       -> Complexity Router (trivial→complex)
       -> 9 Governed Roles (PO→Analyst→Architect→PM→Dev→Tester→Reviewer→Manager)
       -> Quality Gates (3) + Feedback Loops (2)
       -> Context Assembler (5-tier delivery)
       -> Working Set Enforcer (bounded filesystem)
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
| Agent Runner | `agent/oc-agent-runner.py` | Multi-provider orchestrator with multi-turn tool calling |
| Mission Controller | `agent/mission/controller.py` | 9-role mission orchestration with state machine |
| Role Registry | `agent/mission/role_registry.py` | 9 canonical roles with tool policies and budgets |
| Skill Contracts | `agent/mission/skill_contracts.py` | 10 skill contracts with typed input/output |
| Quality Gates | `agent/mission/quality_gates.py` | 3 gates validating artifacts between stage groups |
| Feedback Loops | `agent/mission/feedback_loops.py` | 2 feedback loops for rework detection |
| Complexity Router | `agent/mission/complexity_router.py` | 4-tier routing (trivial→complex) |
| Mission State Machine | `agent/mission/mission_state.py` | 10-state mission lifecycle |
| Context Assembler | `agent/context/assembler.py` | 5-tier artifact delivery (metadata→full+neighbors) |
| Working Set Enforcer | `agent/context/working_set_enforcer.py` | Bounded filesystem access per stage |
| Policy Telemetry | `agent/context/policy_telemetry.py` | 20 mandatory telemetry event types |
| Tool Catalog | `agent/services/tool_catalog.py` | 24 named tools mapped to PowerShell commands |
| Risk Engine | `agent/services/risk_engine.py` | Deterministic risk classification + blocked patterns |
| Approval Service | `agent/services/approval_service.py` | Telegram-based approval for high-risk operations |
| Approval Store | `agent/services/approval_store.py` | Persistent approval records |
| Artifact Store | `agent/services/artifact_store.py` | Typed output (12 artifact types) |
| Schema Validator | `agent/artifacts/schema_validator.py` | Artifact schema validation |
| MCP Client | `agent/services/mcp_client.py` | HTTP client for windows-mcp server |
| Provider Factory | `agent/providers/factory.py` | Multi-provider: GPT-4o, Claude, Ollama |
| Bridge | `bridge/oc-bridge.ps1` | Stateless adapter for legacy task system |
| oc runtime | `bin/` | Task queue, worker, watchdog, health engine |
| WSL Guardian | `bin/oc-wsl-guardian.ps1` | Active WSL + Vezir monitor with auto-restart |

## 9 Governed Roles

| Role | Default Skill | Tool Policy | Model | Discovery |
|------|---------------|-------------|-------|-----------|
| product-owner | requirement_structuring | no_tools | gpt-4o | forbidden |
| analyst | repository_discovery | read_only (14 tools) | claude-sonnet | primary |
| architect | architecture_synthesis | read_only (14 tools) | claude-sonnet | primary |
| project-manager | work_breakdown | no_tools | gpt-4o | forbidden |
| developer | targeted_code_change | dev (14 tools) | claude-sonnet | forbidden |
| tester | test_validation | test tools | claude-sonnet | forbidden |
| reviewer | quality_review | review tools | claude-sonnet | forbidden |
| manager | summary_compression | no_tools | gpt-4o | forbidden |
| remote-operator | controlled_execution | operational | gpt-4o | forbidden |

## Quality Gates

| Gate | Runs After | Runs Before | Validates |
|------|-----------|-------------|-----------|
| Gate 1 | PO, Analyst, Architect, PM | Developer | Requirements + Design artifacts |
| Gate 2 | Developer, Tester | Reviewer | Code delivery + Test report |
| Gate 3 | All stages | Final | All artifact schemas validated |

## Repository Structure

```
agent/                 AI agent system (Phase 3-4)
  oc-agent-runner.py     Main orchestrator
  oc_agent_runner_lib.py Agent orchestration logic
  providers/             LLM providers (GPT-4o, Claude, Ollama)
  services/              MCP client, tool catalog, risk engine, approval, artifacts, audit
  mission/               Controller, roles, skills, gates, loops, state machine, router
  context/               Context Assembler, Working Set, Path Resolver, Telemetry
  artifacts/             Schema Validator
bin/                   Runtime scripts (worker, watchdog, enqueue, health, dashboard, etc.)
bridge/                Bridge entrypoint + allowlist
wsl/                   WSL-side wrappers (oc-agent-run, oc-approve, bridge wrappers)
actions/               Action scripts + manifest
defs/tasks/            Task definitions
config/                Environment variable templates
logs/                  Audit logs, approval records, session artifacts
results/               Agent output files (screenshots, generated files)
frontend/              Vezir UI — React dashboard (port 3000)
docs/ai/               Living project state (STATE, NEXT, DECISIONS, BACKLOG, PROTOCOL)
docs/architecture/     Frozen design documents
docs/phase-reports/    Completed phase reports (Phase 1 through Phase 4 Sprint 6C)
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
| get_system_health | low | Vezir health check (11 components) |
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
- Optional: Anthropic API key (`ANTHROPIC_API_KEY`) for Claude provider

### Run Agent (Single-agent mode)

```powershell
# Install dependencies
pip install -r agent/requirements.txt

# Test agent (from PowerShell with OPENAI_API_KEY set)
python agent/oc-agent-runner.py -m "CPU ve RAM kullanımı ne?"
python agent/oc-agent-runner.py -m "en çok CPU kullanan 5 process ne?"
python agent/oc-agent-runner.py -m "ekran görüntüsü al"
```

### Run Agent (Mission mode)

```powershell
# Mission mode — breaks complex goals into governed stages
python agent/oc-agent-runner.py --mission -m "tool_catalog.py'ye yeni tool ekle"
python agent/oc-agent-runner.py --mission -m "dashboard'a CPU grafik ekle"
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

# Start Vezir UI (port 3000, requires Node.js 20)
bash scripts/dev-frontend.sh

# Start Vezir API (port 8003)
bash scripts/dev-backend.sh
```

## Scheduled Tasks

| Task | Trigger | Purpose |
|------|---------|---------|
| VezirTaskWorker | AtLogOn | Ephemeral -RunOnce worker |
| VezirRuntimeWatchdog | Every 15min | Health + stuck task + worker kick |
| VezirStartupPreflight | AtBoot | Stale recovery + layout validation |
| VezirWmcpServer | AtLogOn | windows-mcp HTTP server on :8001 |
| VezirWslGuardian | AtLogOn | WSL + Vezir active guardian |

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
| 3-E | Multi-Provider Support (GPT, Claude, Ollama) |
| 3-F | Multi-Agent Foundation (hub-and-spoke, 2 specialists) |
| 4 | Agent Governance (9 roles, quality gates, state machine, context economy) |

**Next:** Phase 4.5 — Operational Tuning (structured extraction, strict approval, crash resume)

## Documentation

- `docs/ai/STATE.md` — Current system state and component status
- `docs/ai/NEXT.md` — Roadmap and carry-forward items
- `docs/ai/DECISIONS.md` — 114 architectural decisions (frozen)
- `docs/ai/GOVERNANCE.md` — Sprint governance rules (D-112)
- `docs/ai/BACKLOG.md` — Open backlog items
- `docs/phase-reports/` — Active phase/sprint reports (historical in `docs/archive/`)
