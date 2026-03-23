# Phase 3-A: Agent-MCP Architecture Design Freeze

**Date:** 2026-03-23
**Status:** FROZEN
**Author:** Operator + Claude Opus 4.6
**Scope:** Design only — no implementation in this phase

---

## Section 1: Executive Summary

**What changes:** Static task execution evolves to dynamic AI agent execution. The system gains the ability to interpret natural language requests, select appropriate tools, assess risk, seek approval when needed, and return typed artifacts.

**What stays:** Bridge (`oc-bridge.ps1`), oc runtime (task queue/worker/runner), monitoring (health engine, dashboard, watchdog), notifications (Phase 1.7), WSL Guardian, all existing task definitions and scheduled tasks. Agent capabilities are purely ADDITIVE.

**Design philosophy:** "Single agent today, governed multi-agent tomorrow." Every component is designed as the first entry in a registry, not a singleton. Every interface supports future extension without architectural rewrites.

**First agent:** Claude (Anthropic API, `claude-sonnet-4-20250514`).

**Key architectural pattern:** Every component designed as first-of-many, not only-one:
- Agent Runner is the first entry in an Agent Registry
- Tool access uses role-scoped policies even for one role
- Approval is a service interface, not embedded logic
- Output is typed artifacts, not free-form text
- State can grow from session to mission
- Routing is table-driven, not context-guessed

---

## Section 2: Architecture Overview

### 2.1 System Layers (Updated)

```
Layer 1: User Interface
  - Telegram (via OpenClaw) — unchanged

Layer 2: Conversation + Routing
  - OpenClaw (WSL) — enhanced with deterministic routing table
  - Routes to: agent system, existing runtime, or direct conversation

Layer 3: Agent Execution (NEW)
  - Agent Registry (manages available agents and their capabilities)
  - Agent Runner (executes a specific agent for a request)
  - Currently: single Claude agent. Future: specialist agents.

Layer 4: Services (NEW — designed as interfaces, minimal implementation)
  - Tool Gateway (role-scoped MCP access)
  - Risk Engine (deterministic risk classification)
  - Approval Service (decoupled approval flow)
  - Artifact Store (typed output management)
  - Session/Mission State (extensible state tracking)
  - Audit Service (every action logged)

Layer 5: Tool Layer
  - MCP Tools (windows-mcp, localhost:8001) — for dynamic operations
  - oc runtime (existing task system) — for predefined multi-step tasks

Layer 6: Operating System
  - Windows (PowerShell, filesystem, processes, GUI)
  - WSL Ubuntu-E (OpenClaw, bridge wrappers)
```

### 2.2 Call Flows

**Flow A — Single agent handles request (Phase 3-B):** [FROZEN]

```
User (Telegram)
  -> OpenClaw: routing table -> agent request
  -> wsl/oc-agent-run -> agent/oc-agent-runner.py
    -> Agent Registry: resolve agent (claude)
    -> Claude API: message + tools (from Tool Gateway)
    -> Claude: tool_call response
    -> Tool Gateway: check role permissions -> Risk Engine: classify
      -> low: execute via MCP
      -> high: Approval Service -> Telegram -> user decision
    -> MCP result -> back to Claude -> formatted response
    -> Artifact Store: save typed output
    -> Audit: log everything
  -> response -> OpenClaw -> Telegram
```

**Flow B — Existing runtime (unchanged):** [FROZEN]

```
User -> OpenClaw -> oc-bridge-submit -> Bridge -> oc runtime
```

**Flow C — Future multi-agent mission (design interface only):** [FUTURE]

```
User: "Unity 2D oyun yap"
  -> OpenClaw: routing table -> mission request
  -> Mission Controller (FUTURE): breaks into stages
    -> Stage 1: Analyst Agent -> requirements artifact
    -> Stage 2: PM Agent -> work breakdown artifact
    -> Stage 3: Developer Agent -> code artifact
    -> Stage 4: Tester Agent -> test results artifact
    -> Stage 5: Reviewer Agent -> review decision artifact
  -> All through same Tool Gateway, Risk Engine, Approval Service
  -> Mission State tracks progress across stages
```

Flow C is NOT implemented in Phase 3. But the service interfaces (Tool Gateway, Risk Engine, Approval Service, Artifact Store) are designed to support it.

### 2.3 Deterministic Routing Table [FROZEN]

NOT context-based guessing. Explicit routing rules:

```json
// agent/routing-rules.json
{
  "rules": [
    {
      "pattern": "merhaba|selam|nasilsin|ne yapabilirsin",
      "route": "conversation",
      "handler": "openclaw",
      "description": "Greetings and meta-questions"
    },
    {
      "pattern": "create_note|notepad_then_ready",
      "route": "runtime_task",
      "handler": "oc-bridge-submit",
      "description": "Known predefined tasks"
    },
    {
      "pattern": "health|sistem durumu|saglik",
      "route": "health_check",
      "handler": "oc-bridge-system-health",
      "description": "System health queries"
    },
    {
      "route": "agent",
      "handler": "oc-agent-run",
      "description": "Default: everything else goes to agent"
    }
  ]
}
```

Routing is deterministic: first match wins, agent is the default fallback. Future: mission-type patterns will route to Mission Controller.

---

## Section 3: Agent Registry [FROZEN]

NOT a singleton agent runner. A registry that manages agents.

### 3.1 Registry Design

```json
// agent/agent-registry.json
{
  "version": 1,
  "agents": {
    "claude-general": {
      "provider": "claude",
      "model": "claude-sonnet-4-20250514",
      "role": "general-assistant",
      "description": "General-purpose Windows automation agent",
      "enabled": true,
      "toolPolicy": "general-assistant",
      "maxTurns": 10,
      "timeoutSeconds": 120
    }
  },
  "futureAgents": {
    "_comment": "These are NOT implemented. They show how the registry extends.",
    "analyst": {
      "role": "analyst",
      "toolPolicy": "read-only",
      "description": "Requirements analysis, research, risk assessment"
    },
    "developer": {
      "role": "developer",
      "toolPolicy": "developer",
      "description": "Code generation, file modification, build"
    },
    "tester": {
      "role": "tester",
      "toolPolicy": "tester",
      "description": "Test execution, bug reporting"
    },
    "reviewer": {
      "role": "reviewer",
      "toolPolicy": "read-only",
      "description": "Code review, quality gate decisions"
    }
  },
  "defaults": {
    "defaultAgent": "claude-general",
    "unknownRequest": "claude-general"
  }
}
```

Phase 3-B implements ONE agent entry. The registry pattern is ready for more.

### 3.2 Agent Selection

For Phase 3-B: always use `claude-general`. For future: selection based on routing rules + mission stage.

The Agent Runner reads the registry, loads the specified agent config, applies the tool policy, and runs the conversation.

---

## Section 4: Provider Abstraction [FROZEN]

### 4.1 Provider Interface

```python
class AgentProvider:
    """Base interface — every LLM provider implements this."""
    def chat(self, messages: list, tools: list, max_tokens: int) -> AgentResponse
    def name(self) -> str

class AgentResponse:
    """Standardized response regardless of provider."""
    text: str | None           # Final text response
    tool_calls: list[ToolCall] # Tool calls to execute
    stop_reason: str           # "end_turn", "tool_use", "max_tokens"
```

### 4.2 First Provider: Claude [FROZEN]

- Model: `claude-sonnet-4-20250514`
- API: `anthropic` Python SDK (direct, no LangChain)
- Tool format: native Anthropic `tool_use`
- Config: API key from env `ANTHROPIC_API_KEY`

### 4.3 Future Providers (interface only, stub implementations) [FUTURE]

- GPT: `openai` SDK, model `gpt-4o`
- Ollama: HTTP API, configurable model
- Custom: any provider implementing `AgentProvider`

**Decision D-028:** Start with direct SDK calls. Evaluate LangChain ONLY if adding 3rd+ provider becomes painful.

---

## Section 5: Tool Gateway (Role-Scoped Access) [FROZEN]

THIS IS THE CRITICAL MULTI-AGENT EXTENSIBILITY POINT.

Instead of giving every agent all tools, the Tool Gateway filters tools based on the agent's role/toolPolicy.

### 5.1 Tool Policies

```json
// agent/tool-policies.json
{
  "policies": {
    "general-assistant": {
      "description": "Phase 3-B default — broad access with risk controls",
      "allowedTools": ["*"],
      "deniedTools": ["run_powershell"],
      "riskOverrides": {},
      "requiresApprovalAbove": "medium"
    },
    "read-only": {
      "_comment": "FUTURE — for analyst and reviewer agents",
      "allowedTools": [
        "get_system_info", "list_processes", "read_file",
        "list_directory", "search_files", "get_clipboard",
        "get_system_health", "check_runtime_task"
      ],
      "deniedTools": ["*"],
      "riskOverrides": {},
      "requiresApprovalAbove": "none"
    },
    "developer": {
      "_comment": "FUTURE — for developer agent",
      "allowedTools": [
        "get_system_info", "list_processes", "read_file", "write_file",
        "list_directory", "search_files", "open_application",
        "submit_runtime_task", "check_runtime_task"
      ],
      "deniedTools": ["system_shutdown", "system_restart", "run_powershell"],
      "riskOverrides": {},
      "requiresApprovalAbove": "high"
    },
    "tester": {
      "_comment": "FUTURE — for tester agent",
      "allowedTools": [
        "get_system_info", "list_processes", "read_file",
        "list_directory", "search_files", "take_screenshot",
        "check_runtime_task"
      ],
      "deniedTools": ["write_file", "close_application", "system_shutdown", "run_powershell"],
      "riskOverrides": {},
      "requiresApprovalAbove": "medium"
    },
    "executor": {
      "_comment": "FUTURE — privileged execution agent",
      "allowedTools": ["*"],
      "deniedTools": [],
      "riskOverrides": {},
      "requiresApprovalAbove": "high"
    }
  }
}
```

Phase 3-B implements `general-assistant` policy only. But the Tool Gateway always checks policy — never bypasses it.

**CRITICAL DECISION D-023:** `run_powershell` is DENIED by default in `general-assistant`. The agent uses NAMED tools (`get_system_info`, `read_file`, etc.) instead. `run_powershell` is only available to the future `executor` role, and even then requires approval above "high".

If the agent needs something no named tool covers, it returns: "Bu islem icin ozel arac yok. Operator run_powershell ile yapabilir."

This prevents the agent from bypassing the entire tool catalog via shell escape.

### 5.2 Tool Catalog [FROZEN]

Named tools the agent can use (instead of raw PowerShell):

| Tool name | Description | PowerShell backing | Default risk | Available to |
|-----------|-------------|-------------------|--------------|--------------|
| `get_system_info` | CPU, RAM, disk, uptime | `Get-CimInstance` queries | low | all |
| `list_processes` | Running processes with CPU/memory | `Get-Process` | low | all |
| `read_file` | Read file contents | `Get-Content` | low | all |
| `write_file` | Write file to allowed paths | `Set-Content` (results/ only) | medium | general, developer |
| `list_directory` | List files in directory | `Get-ChildItem` | low | all |
| `search_files` | Search files by name/content | `Get-ChildItem -Recurse -Filter` | low | all |
| `open_application` | Open allowed application | `Start-Process` (allowlist) | medium | general, developer |
| `close_application` | Close application by name | `Stop-Process` | high | general, executor |
| `open_url` | Open URL in default browser | `Start-Process` (URL) | medium | general, developer |
| `get_clipboard` | Read clipboard contents | `Get-Clipboard` | low | all |
| `set_clipboard` | Write to clipboard | `Set-Clipboard` | medium | general, developer |
| `take_screenshot` | Capture screen to file | .NET Screen capture | low | all except executor |
| `lock_screen` | Lock the workstation | `rundll32 user32.dll,LockWorkStation` | medium | general |
| `system_shutdown` | Shutdown computer | `Stop-Computer` | critical | executor only |
| `system_restart` | Restart computer | `Restart-Computer` | critical | executor only |
| `submit_runtime_task` | Submit task to oc runtime | calls `oc-bridge-submit` | medium | general, developer |
| `check_runtime_task` | Check runtime task status | calls `oc-bridge-status` | low | all |
| `get_system_health` | Full system health check | calls `oc-bridge-system-health` | low | all |
| `run_powershell` | Arbitrary PowerShell (RESTRICTED) | Direct MCP call | high+ (content-based) | executor only |

For each tool: exact PowerShell command template, input parameters with types, output format, and error handling are specified in implementation.

### 5.3 Tool Gateway Implementation [FROZEN]

```python
class ToolGateway:
    """Mediates all tool access. Checks policy before execution."""

    def __init__(self, policy_name: str, mcp_client, risk_engine, approval_service):
        self.policy = load_policy(policy_name)
        self.mcp = mcp_client
        self.risk = risk_engine
        self.approval = approval_service

    def get_available_tools(self) -> list:
        """Returns tool definitions filtered by policy. LLM only sees allowed tools."""
        # Filter catalog by policy.allowedTools / policy.deniedTools
        # LLM never even knows about tools it can't use

    def execute_tool(self, tool_name: str, params: dict, context: ExecutionContext) -> ToolResult:
        """Execute with full policy + risk + approval chain."""
        # 1. Check tool allowed by policy
        # 2. Classify risk (Risk Engine)
        # 3. If risk > policy.requiresApprovalAbove -> Approval Service
        # 4. Execute via MCP
        # 5. Log to Audit
        # 6. Return result
```

This is the key extensibility point: new agents get different policies, same gateway, same risk engine, same approval service.

---

## Section 6: Risk Engine [FROZEN]

Deterministic, NOT LLM-based.

### 6.1 Risk Classification Rules

```json
// agent/risk-rules.json
{
  "version": 1,
  "rules": [
    {
      "tools": ["get_system_info", "list_processes", "read_file", "list_directory",
                "search_files", "get_clipboard", "take_screenshot",
                "check_runtime_task", "get_system_health"],
      "risk": "low",
      "description": "Read-only operations"
    },
    {
      "tools": ["write_file", "open_application", "open_url", "set_clipboard",
                "lock_screen", "submit_runtime_task"],
      "risk": "medium",
      "description": "Controlled write/launch operations"
    },
    {
      "tools": ["close_application"],
      "risk": "high",
      "description": "Destructive process operations"
    },
    {
      "tools": ["system_shutdown", "system_restart"],
      "risk": "critical",
      "description": "System-level dangerous operations"
    },
    {
      "tools": ["run_powershell"],
      "risk": "high",
      "riskEscalation": {
        "patterns": [
          {"match": "Remove-Item|del |rm |format|diskpart", "escalateTo": "critical"},
          {"match": "Stop-Computer|Restart-Computer|shutdown", "escalateTo": "critical"},
          {"match": "Invoke-Expression|DownloadString|encodedcommand", "escalateTo": "blocked"}
        ]
      },
      "description": "Arbitrary PowerShell — content-inspected, escalates by command"
    }
  ],
  "blockedPatterns": [
    "Invoke-Expression.*http",
    "Net.WebClient.*DownloadString",
    "encodedcommand",
    "bypass.*executionpolicy",
    "reg.*add.*HKLM.*Security",
    "netsh.*advfirewall.*off",
    "Disable-WindowsOptionalFeature.*Defender"
  ],
  "defaultRisk": "medium"
}
```

### 6.2 Risk Levels and Actions [FROZEN]

| Risk level | Agent response | Approval needed |
|-----------|---------------|-----------------|
| low | Auto-execute | No |
| medium | Auto-execute (general-assistant) or approval (stricter roles) | Policy-dependent |
| high | Always requires explicit Telegram approval | Yes |
| critical | Telegram approval + 10s countdown + re-confirmation | Yes |
| blocked | Immediate reject, never executed | N/A — hard block |

---

## Section 7: Approval Service [FROZEN]

Designed as a SERVICE INTERFACE, not embedded in agent logic. This is critical for multi-agent: multiple agents may need approval simultaneously.

### 7.1 Approval Request

```json
{
  "approvalId": "apv-20260323-143022-001",
  "sessionId": "sess-12345",
  "missionId": null,
  "requestedByAgent": "claude-general",
  "userId": "8654710624",
  "toolName": "close_application",
  "toolParams": {"name": "chrome"},
  "risk": "high",
  "reason": "Agent wants to close Chrome browser",
  "expiresAt": "2026-03-23T14:31:22Z",
  "status": "pending"
}
```

### 7.2 Approval Flow

```
Agent -> Approval Service: create request
Approval Service -> Telegram (via oc-telegram-notify.ps1):
   "Warning: Agent Approval Request [apv-20260323-143022-001]
   Agent: claude-general
   Tool: close_application
   Parameters: name=chrome
   Risk: HIGH

   Reply: approve apv-001 or deny apv-001
   Auto-deny in 60 seconds."

User replies -> OpenClaw routes to Approval Service
Approval Service updates status -> Agent polls or gets callback
```

### 7.3 Approval Storage

File-based for Phase 3-B (simple, no database needed):

```
logs/approvals/
  apv-20260323-143022-001.json    # request + decision
```

### 7.4 Correlation

User approves by approval ID, not "yes/no". This prevents confusion when multiple approvals are pending (multi-agent future).

Phase 3-B: only one approval at a time (single agent). But the ID-based correlation is already in place for multi-agent.

---

## Section 8: Artifact Store (Typed Output) [FROZEN]

Agent output is NOT free-form text. It's typed artifacts.

### 8.1 Artifact Types

```json
// agent/artifact-types.json
{
  "types": {
    "text_response": {
      "description": "Simple text answer to user",
      "schema": {"message": "string"},
      "example": {"message": "CPU kullanimi: %23"}
    },
    "file_created": {
      "description": "Agent created a file",
      "schema": {"path": "string", "filename": "string", "size": "integer"},
      "example": {"path": "results/screenshot.png", "filename": "screenshot.png", "size": 45230}
    },
    "task_submitted": {
      "description": "Agent submitted a runtime task",
      "schema": {"taskId": "string", "taskName": "string"},
      "example": {"taskId": "task-20260323-143022-001", "taskName": "create_note"}
    },
    "error": {
      "description": "Agent encountered an error",
      "schema": {"error": "string", "recoverable": "boolean"},
      "example": {"error": "MCP server unreachable", "recoverable": true}
    },
    "approval_needed": {
      "description": "Agent is waiting for approval",
      "schema": {"approvalId": "string", "tool": "string", "risk": "string"},
      "example": {"approvalId": "apv-001", "tool": "close_application", "risk": "high"}
    }
  },
  "futureTypes": {
    "_comment": "For multi-agent missions",
    "requirements_doc": {"schema": {"content": "string", "format": "markdown"}},
    "work_breakdown": {"schema": {"tasks": "array", "milestones": "array"}},
    "test_report": {"schema": {"passed": "integer", "failed": "integer", "bugs": "array"}},
    "review_decision": {"schema": {"decision": "string", "comments": "array"}}
  }
}
```

Phase 3-B: implements first 5 types. Future types documented but not implemented.

### 8.2 Agent Output Format [FROZEN]

Every agent invocation returns a standardized envelope:

```json
{
  "status": "completed",
  "agentId": "claude-general",
  "sessionId": "sess-12345",
  "artifacts": [
    {
      "type": "text_response",
      "data": {"message": "CPU kullanimi %23. 142 process aktif."}
    }
  ],
  "toolCalls": [
    {"tool": "get_system_info", "risk": "low", "approved": true, "durationMs": 450}
  ],
  "turnsUsed": 2,
  "totalDurationMs": 2100
}
```

This envelope is the HANDOFF CONTRACT. In multi-agent future, the Mission Controller reads these envelopes to decide next steps.

---

## Section 9: Session & Mission State [FROZEN]

### 9.1 Session State (Phase 3-B — implemented)

Per-invocation state, not persisted across invocations:

```json
// In-memory during agent execution
{
  "sessionId": "sess-20260323-143022",
  "agentId": "claude-general",
  "userId": "8654710624",
  "startedUtc": "2026-03-23T14:30:22Z",
  "messages": [],
  "toolCallCount": 0,
  "pendingApprovals": []
}
```

### 9.2 Mission State (FUTURE — interface designed, not implemented) [FUTURE]

```json
// logs/missions/mission-20260323-001.json
{
  "missionId": "mission-20260323-001",
  "goal": "Create a 2D survival game in Unity",
  "currentStage": "development",
  "assignedAgent": "developer",
  "stages": [
    {"stage": "analysis", "agent": "analyst", "status": "completed", "artifactRef": "..."},
    {"stage": "planning", "agent": "pm", "status": "completed", "artifactRef": "..."},
    {"stage": "development", "agent": "developer", "status": "in_progress", "artifactRef": null},
    {"stage": "testing", "agent": "tester", "status": "pending"},
    {"stage": "review", "agent": "reviewer", "status": "pending"}
  ],
  "openIssues": [],
  "retryCount": 0
}
```

Phase 3-B: session state only (in-memory, per-invocation). Phase 3-D: mission state (persistent, multi-stage, multi-agent). The artifact envelope and typed output from Phase 3-B become the building blocks for mission handoffs in Phase 3-D.

---

## Section 10: Audit Service [FROZEN]

Every action logged, no exceptions.

### 10.1 Agent Audit Trail

File: `logs/agent-audit.jsonl`

```json
{
  "ts": "2026-03-23T14:30:22Z",
  "sessionId": "sess-12345",
  "missionId": null,
  "agentId": "claude-general",
  "userId": "8654710624",
  "userMessage": "CPU kullanimi kac?",
  "toolCalls": [
    {
      "tool": "get_system_info",
      "params": {},
      "risk": "low",
      "policyCheck": "allowed",
      "approved": true,
      "approvalMethod": "auto",
      "exitCode": 0,
      "durationMs": 450
    }
  ],
  "artifacts": [{"type": "text_response"}],
  "response": "CPU kullanimi: %23",
  "turnsUsed": 2,
  "totalDurationMs": 2100,
  "status": "completed"
}
```

### 10.2 Integration with Existing Monitoring

- Agent errors detected by watchdog health snapshot
- High-risk approvals sent via Telegram notification (reuse Phase 1.7)
- Agent audit log rotation: same policy as other logs (5MB, keep 3)

---

## Section 11: Agent Runner Design [FROZEN]

Location: `agent/oc-agent-runner.py` (Windows, Python)

### 11.1 CLI Interface

```bash
python agent/oc-agent-runner.py \
  --message "ekran goruntusu al" \
  --agent claude-general \
  --user-id 8654710624 \
  --session-id "sess-12345" \
  --max-turns 10
```

Output: standardized JSON envelope to stdout.

### 11.2 Execution Flow

```python
def run_agent(message, agent_id, user_id, session_id, max_turns):
    # 1. Load agent config from registry
    agent_config = registry.get_agent(agent_id)

    # 2. Load provider
    provider = create_provider(agent_config.provider)

    # 3. Create Tool Gateway with agent's tool policy
    gateway = ToolGateway(
        policy=agent_config.toolPolicy,
        mcp_client=mcp,
        risk_engine=risk_engine,
        approval_service=approval_svc
    )

    # 4. Get available tools (filtered by policy)
    tools = gateway.get_available_tools()

    # 5. Build system prompt
    system_prompt = build_system_prompt(agent_config, tools)

    # 6. Conversation loop
    messages = [system_message, user_message]
    for turn in range(max_turns):
        response = provider.chat(messages, tools)

        if response.stop_reason == "end_turn":
            break  # Agent is done

        if response.tool_calls:
            for call in response.tool_calls:
                result = gateway.execute_tool(call.name, call.params, context)
                messages.append(tool_result(call, result))

    # 7. Build artifact envelope
    return build_envelope(session, messages, tool_log, artifacts)
```

### 11.3 System Prompt Design [RECOMMENDED]

```
You are a Windows automation assistant. You help the user manage their
computer through specialized tools.

Available tools are provided to you. Use them to answer the user's request.
If no tool fits the request, explain what you cannot do.

Rules:
- Never try to bypass tool restrictions
- If a tool call fails, explain the error to the user
- Prefer specific named tools over general approaches
- Answer in the same language the user uses
- Be concise and actionable
- If asked to do something dangerous, explain the risk and suggest
  safer alternatives

You do NOT have access to:
- Direct PowerShell execution (use named tools instead)
- System shutdown/restart (restricted to operator)
- File deletion outside results/ directory
```

---

## Section 12: WSL-Windows Bridge for Agent [FROZEN]

### 12.1 WSL Wrapper

Create: `wsl/oc-agent-run`

```python
#!/usr/bin/env python3
"""Bridge from OpenClaw (WSL) to Agent Runner (Windows)."""
import json, os, subprocess, sys, time

message = sys.argv[1] if len(sys.argv) > 1 else None
agent = sys.argv[2] if len(sys.argv) > 2 else "claude-general"
user_id = sys.argv[3] if len(sys.argv) > 3 else "8654710624"

if not message:
    print("usage: oc-agent-run <message> [agent] [userId]", file=sys.stderr)
    sys.exit(2)

# Call Windows-side agent runner
cmd = [
    "/mnt/c/Users/AKCA/AppData/Local/Programs/Python/Python312/python.exe",
    "/mnt/c/Users/AKCA/oc/agent/oc-agent-runner.py",
    "--message", message,
    "--agent", agent,
    "--user-id", user_id,
    "--session-id", f"sess-{int(time.time())}-{os.getpid()}"
]
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stdout)
sys.exit(r.returncode)
```

### 12.2 OpenClaw Integration

OpenClaw routes to agent via `oc-agent-run` wrapper. Same exec-approval pattern as existing bridge wrappers.

---

## Section 13: File Structure [FROZEN]

```
oc/
+-- agent/                              (NEW -- agent system)
|   +-- oc-agent-runner.py              Main orchestrator
|   +-- agent-registry.json             Agent definitions
|   +-- agent-config.json               Provider configs (API keys, models)
|   +-- tool-policies.json              Role-scoped tool access
|   +-- risk-rules.json                 Risk classification rules
|   +-- routing-rules.json              Deterministic request routing
|   +-- artifact-types.json             Typed output schemas
|   +-- providers/
|   |   +-- __init__.py
|   |   +-- base.py                     AgentProvider interface
|   |   +-- claude_provider.py          Anthropic Claude implementation
|   +-- services/
|   |   +-- __init__.py
|   |   +-- tool_gateway.py             Role-scoped MCP access
|   |   +-- risk_engine.py              Deterministic risk classifier
|   |   +-- approval_service.py         Telegram-based approval
|   |   +-- artifact_store.py           Typed output management
|   |   +-- audit_service.py            Structured logging
|   |   +-- mcp_client.py              MCP HTTP client
|   +-- requirements.txt                anthropic, requests
+-- wsl/
|   +-- oc-agent-run                    (NEW -- WSL->Windows agent bridge)
|   +-- ... existing wrappers unchanged
+-- logs/
|   +-- agent-audit.jsonl               (NEW -- agent action log)
|   +-- approvals/                      (NEW -- approval request/decision files)
+-- bin/                                (unchanged)
+-- bridge/                             (unchanged)
+-- ... rest unchanged
```

---

## Section 14: Safety & Guardrails [FROZEN]

### 14.1 Defense Layers (6 layers)

1. **LLM System Prompt:** instructions on restrictions
2. **Tool Gateway + Policy:** agent never sees tools it can't use
3. **Risk Engine:** deterministic pattern matching
4. **Blocked Patterns:** absolute deny list, never overridable
5. **Approval Service:** human-in-the-loop for dangerous operations
6. **Audit Service:** every action recorded, reviewable

### 14.2 run_powershell Decision (FROZEN — D-023)

`run_powershell` is NOT available to `general-assistant` agent. It is reserved for future `executor` role only. Even then, it requires: policy check + risk escalation + approval.

If the agent cannot accomplish a task with named tools, it reports this limitation. The operator can use CLI directly.

This prevents the entire tool catalog from being bypassed via shell escape.

### 14.3 Failure Modes [FROZEN]

| Failure | Behavior |
|---------|----------|
| LLM API down | Return error artifact, don't retry endlessly |
| MCP server down | Return error, suggest checking health |
| Tool call timeout (30s) | Kill, return timeout to LLM |
| Agent loops (>max_turns) | Force stop, return partial artifacts |
| Approval timeout (60s) | Auto-deny, inform user |
| Blocked command detected | Immediate reject, audit log, notify |
| Policy violation | Reject tool call, log incident |

---

## Section 15: Implementation Phases [FROZEN]

**Phase 3-B: Core Agent Runner** (NEXT — implement first)
- `agent/oc-agent-runner.py`
- `agent/providers/claude_provider.py`
- `agent/services/mcp_client.py`
- `agent/services/tool_gateway.py` (basic — allow all named tools)
- `wsl/oc-agent-run`
- `agent-registry.json`, `agent-config.json`
- Test: "CPU kullanimi kac?" works end-to-end via Telegram

**Phase 3-C: Risk + Approval**
- `agent/services/risk_engine.py`
- `agent/services/approval_service.py`
- `risk-rules.json`, `tool-policies.json`
- Telegram approval flow integration
- Test: "Chrome'u kapat" triggers approval, works after approve

**Phase 3-D: Tool Catalog + Artifacts**
- Full 18-tool catalog implementation
- `artifact-types.json`, `artifact_store.py`
- Agent audit logging (`audit_service.py`)
- Test: all tool categories work, artifacts typed

**Phase 3-E: Multi-Provider**
- `agent/providers/gpt_provider.py` (OpenAI)
- `agent/providers/ollama_provider.py` (local)
- Provider selection via registry
- Test: same request works with different providers

**Phase 3-F: Multi-Agent Foundation**
- Mission Controller design + implementation
- Specialist agent role definitions (analyst, developer, tester, reviewer)
- Mission state persistence
- Agent-to-agent handoff via Supervisor
- Typed artifact handoff contracts
- Hub-and-spoke orchestration
- This phase uses ALL the extensibility hooks built in 3-B through 3-E

---

## Section 16: What Stays Unchanged

- Bridge (`oc-bridge.ps1`) — unchanged
- Runtime (task queue, worker, runner) — unchanged
- Existing task definitions — unchanged
- Existing WSL wrappers (submit, status, cancel, health) — unchanged
- Monitoring (health engine, dashboard, watchdog) — unchanged
- Notifications (Phase 1.7) — reused for agent alerts
- WSL Guardian — unchanged
- Scheduled tasks — no new scheduled task for agent runner

---

## Section 17: Multi-Agent Evolution Roadmap [FUTURE]

This section documents the FUTURE vision. Nothing here is implemented in Phase 3-A through 3-E. This is the target state for Phase 3-F and beyond.

### 17.1 Target Architecture: Governed Multi-Agent System

```
Mission Controller (Supervisor)
  | hub-and-spoke (agents don't call each other directly)
  +-- Analyst Agent (read-only tools)
  +-- PM Agent (planning tools, no execution)
  +-- Developer Agent (code tools, limited execution)
  +-- Tester Agent (test tools, no destructive ops)
  +-- Reviewer Agent (read-only, quality gate decisions)
  +-- Executor Agent (privileged, approval-gated)
```

### 17.2 Key Principles for Multi-Agent

- **Hub-and-spoke:** all handoffs through Supervisor, not peer-to-peer
- **Role separation:** developer can't approve own work, tester can't deploy
- **Typed artifacts:** structured handoff between agents
- **Mission state:** persistent, survives agent crashes
- **Approval service:** centralized, correlation-based, concurrent-safe

### 17.3 Why These Are Deferred

- No agent runs today — need single-agent experience first
- Tool calling reliability unknown — must test before multi-agent
- Approval UX untested — must validate before concurrent approvals
- Artifact needs unknown — must see real usage patterns first

Each Phase 3 sub-phase generates experience that informs the next. Phase 3-F (multi-agent) will be designed with data from 3-B through 3-E.

---

## Section 18: Exit Criteria for Phase 3-A

| Criterion | Status |
|-----------|--------|
| Architecture layers defined | FROZEN |
| Call flows (A, B, C) documented | FROZEN |
| Agent Registry pattern designed | FROZEN |
| Provider abstraction interface | FROZEN |
| Tool Gateway with role-scoped policies | FROZEN |
| Risk Engine rules frozen | FROZEN |
| Approval Service interface | FROZEN |
| Artifact types defined | FROZEN |
| Session state designed, mission state interface | FROZEN |
| Audit format specified | FROZEN |
| run_powershell restriction frozen (D-023) | FROZEN |
| Deterministic routing table | FROZEN |
| File structure agreed | FROZEN |
| Implementation phases ordered | FROZEN |
| Multi-agent evolution roadmap documented | FROZEN |
| Safety guardrails documented | FROZEN |

ALL criteria met. Phase 3-A is FROZEN.

---

*Generated: 2026-03-23 | Phase 3-A Architecture Design Freeze*
*Operator: AKCA | Agent: Claude Opus 4.6 (1M context)*
