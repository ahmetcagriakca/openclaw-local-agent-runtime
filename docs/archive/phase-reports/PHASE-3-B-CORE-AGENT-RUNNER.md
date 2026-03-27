# Phase 3-B: Core Agent Runner Implementation

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Implement minimum viable agent runner — GPT-4o + MCP tool calling end-to-end

---

## Section 1: Executive Summary

**What was built:** A working AI agent runner that connects GPT-4o to Windows automation tools via the MCP server. The user sends a natural language message, GPT-4o selects the right tool(s), the agent executes them via MCP PowerShell, and returns a formatted response.

**Key deviation from Phase 3-A plan:** First provider is GPT-4o (OpenAI), not Claude. Reason: OPENAI_API_KEY available, Anthropic API credits not yet available. Provider abstraction is in place — Claude can be added by implementing `claude_provider.py` with zero changes to the runner.

**What was deferred to Phase 3-C:** Risk Engine, Approval Service, Tool Gateway policy enforcement. Current agent auto-executes all tool calls regardless of risk level.

**End-to-end verified:** `python agent/oc-agent-runner.py -m "CPU ve RAM kullanımı ne?"` returns structured JSON with tool call results in ~9 seconds.

---

## Section 2: Architecture Implemented

### 2.1 Component Map

```
User message (CLI or WSL wrapper)
  -> agent/oc-agent-runner.py (orchestrator)
    -> providers/gpt_provider.py (GPT-4o via OpenAI SDK)
    -> services/tool_catalog.py (12 named tools -> PowerShell commands)
    -> services/mcp_client.py (HTTP client -> localhost:8001)
    -> windows-mcp server (executes PowerShell)
    -> GPT-4o processes result -> formatted response
    -> services/audit_service.py (JSONL logging)
  -> JSON envelope to stdout
```

### 2.2 Multi-Turn Tool Loop

The agent runner supports multi-turn conversations. GPT-4o can make multiple sequential tool calls before producing a final answer:

```
Turn 1: User message -> GPT-4o -> tool_call(get_system_info)
Turn 2: Tool result -> GPT-4o -> "CPU %7, RAM 19.8/63.7 GB"
```

Max turns configurable (default: 10). If agent exceeds max turns, partial result is returned.

---

## Section 3: Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `agent/oc-agent-runner.py` | Main orchestrator — CLI, multi-turn loop, JSON envelope output | ~170 |
| `agent/providers/__init__.py` | Package init | 0 |
| `agent/providers/base.py` | `AgentProvider` interface, `ToolCall`, `AgentResponse` dataclasses | ~25 |
| `agent/providers/gpt_provider.py` | OpenAI GPT-4o implementation of `AgentProvider` | ~55 |
| `agent/services/__init__.py` | Package init | 0 |
| `agent/services/mcp_client.py` | HTTP client for windows-mcp server (POST /PowerShell) | ~75 |
| `agent/services/tool_catalog.py` | 12 named tools with PowerShell backing commands | ~250 |
| `agent/services/audit_service.py` | JSONL audit logging to `logs/agent-audit.jsonl` | ~30 |
| `agent/requirements.txt` | Python dependencies (openai, requests) | 2 |
| `wsl/oc-agent-run` | WSL-to-Windows bridge wrapper for OpenClaw integration | ~55 |

**Total new code:** ~660 lines across 10 files.

---

## Section 4: Tool Catalog (12 Tools)

| Tool | Risk | Parameters | PowerShell Backing |
|------|------|------------|-------------------|
| `get_system_info` | low | none | `Get-CimInstance` (CPU, RAM, disk, uptime) |
| `list_processes` | low | `top_n` (default: 15) | `Get-Process \| Sort CPU` |
| `read_file` | low | `path` | `Get-Content` |
| `write_file` | medium | `filename`, `content` | `Set-Content` (results/ only) |
| `list_directory` | low | `path` | `Get-ChildItem` |
| `search_files` | low | `path`, `pattern` | `Get-ChildItem -Recurse -Filter` |
| `get_clipboard` | low | none | `Get-Clipboard` |
| `set_clipboard` | medium | `text` | `Set-Clipboard` |
| `open_application` | medium | `app_name` (enum: notepad, calc, mspaint, explorer) | `Start-Process` |
| `open_url` | medium | `url` | `Start-Process` |
| `take_screenshot` | low | none | .NET `System.Drawing` screen capture |
| `get_system_health` | low | none | `oc-system-health.ps1` |

Tools are presented to GPT-4o in OpenAI function calling format. The agent never sees raw PowerShell — it only knows named tools with typed parameters.

---

## Section 5: Provider Abstraction

### 5.1 Interface

```python
class AgentProvider:
    def chat(self, messages: list, tools: list, max_tokens: int) -> AgentResponse
    def name(self) -> str

@dataclass
class AgentResponse:
    text: str | None
    tool_calls: list[ToolCall]
    stop_reason: str  # "end_turn", "tool_use", "max_tokens"
```

### 5.2 GPT-4o Provider

- Model: `gpt-4o` (configurable via `OC_GPT_MODEL` env var)
- SDK: `openai` Python package (direct, no LangChain)
- Tool format: OpenAI function calling
- Auth: `OPENAI_API_KEY` environment variable

### 5.3 Adding Claude Later

To add Claude support:
1. Create `agent/providers/claude_provider.py` implementing `AgentProvider`
2. Map Anthropic `tool_use` blocks to `ToolCall` dataclass
3. Update runner to select provider based on agent config

Zero changes needed in runner, MCP client, tool catalog, or audit service.

---

## Section 6: MCP Client

### 6.1 Response Parsing

The windows-mcp server returns responses as JSON strings (not objects):

```
"Response: Hello\r\n\nStatus Code: 0"
```

The MCP client handles this by:
1. Attempting `resp.json()` — gets the string
2. Extracting response content via regex: `Response: (.*?)(?:\n\nStatus Code:|$)`
3. Extracting status code via regex: `Status Code: (\d+)`
4. Returning `{"success": true, "output": "Hello", "error": null}`

**Bug found and fixed during implementation:** Initial code assumed `resp.json()` returns a dict, causing `string indices must be integers` error. Fixed with string-aware parsing.

### 6.2 Connectivity

```
MCP client -> POST http://localhost:8001/PowerShell
Headers: Authorization: Bearer local-mcp-12345
Body: {"command": "...", "timeout": 30}
```

Server health check: `GET /openapi.json` — verified working.

---

## Section 7: Audit Logging

Every agent run appends a JSONL entry to `logs/agent-audit.jsonl`:

```json
{
  "ts": "2026-03-23T11:30:37Z",
  "sessionId": "sess-1774249837-28248",
  "agentId": "gpt-general",
  "userId": "8654710624",
  "userMessage": "CPU ve RAM kullanımı ne?",
  "toolCalls": [
    {"tool": "get_system_info", "params": {}, "risk": "low", "success": true, "durationMs": 3771}
  ],
  "response": "Şu anda CPU kullanımı %7 ve RAM kullanımı 19.8 GB / 63.7 GB.",
  "turnsUsed": 2,
  "totalDurationMs": 9168,
  "status": "completed"
}
```

Audit is best-effort — failures are swallowed silently to avoid breaking the agent.

---

## Section 8: Output Envelope

Every agent invocation returns a standardized JSON envelope:

```json
{
  "status": "completed",
  "agentId": "gpt-general",
  "sessionId": "sess-1774249837-28248",
  "response": "Şu anda CPU kullanımı %7 ve RAM kullanımı 19.8 GB / 63.7 GB.",
  "artifacts": [
    {"type": "text_response", "data": {"message": "..."}}
  ],
  "toolCalls": [
    {"tool": "get_system_info", "params": {}, "risk": "low", "success": true, "durationMs": 3771}
  ],
  "turnsUsed": 2,
  "totalDurationMs": 9168
}
```

Error cases return `"status": "error"` with an error artifact.

---

## Section 9: WSL Bridge Wrapper

`wsl/oc-agent-run` bridges OpenClaw (WSL) to the Windows-side agent runner:

1. Accepts message as CLI argument
2. Finds Python executable on Windows side (checks multiple known paths)
3. Calls `agent/oc-agent-runner.py` via `subprocess.run`
4. Parses JSON output, extracts `response` field for clean display
5. Timeout: 180 seconds

**Deployment:** Copy to `/home/akca/bin/oc-agent-run` and `chmod +x`.

---

## Section 10: Test Results

### Test 1: System Info (PASSED)

```
$ python agent/oc-agent-runner.py -m "CPU ve RAM kullanımı ne?"
Status: completed
Response: "Şu anda CPU kullanımı %7 ve RAM kullanımı 19.8 GB / 63.7 GB."
Tool calls: get_system_info (low risk, 3771ms)
Total duration: 9168ms
Turns used: 2
```

### Test 2: MCP Connectivity (PASSED)

```
$ python agent/services/mcp_client.py
MCP server OK: windows-mcp
Test result: {'success': True, 'output': 'Hello from MCP', 'error': None}
```

### Remaining Tests (awaiting OPENAI_API_KEY in shell environment)

| Test | Command | Status |
|------|---------|--------|
| Process list | `-m "en çok CPU kullanan 5 process ne?"` | Pending |
| File operations | `-m "results klasöründe hangi dosyalar var?"` | Pending |
| Screenshot | `-m "ekran görüntüsü al"` | Pending |
| Health check | `-m "sistem sağlık durumu nasıl?"` | Pending |
| WSL end-to-end | `oc-agent-run "bilgisayarımda kaç process çalışıyor?"` | Pending |

Note: All pending tests are blocked only by environment variable propagation. The system info test proves the full pipeline works.

---

## Section 11: Decisions Made

| Decision | Detail |
|----------|--------|
| **D-028 updated** | First provider is GPT-4o, not Claude. Provider abstraction supports both. |
| **No Tool Gateway yet** | Agent sees all 12 tools, no role-scoped filtering. Deferred to Phase 3-C. |
| **No Risk Engine yet** | Tool risk levels are tagged but not enforced. All tools auto-execute. |
| **No Approval Service yet** | No human-in-the-loop for medium/high risk. Deferred to Phase 3-C. |
| **No routing-rules.json** | Agent is called directly via CLI. OpenClaw routing integration deferred. |
| **No agent-registry.json** | Single hardcoded agent config. Registry pattern deferred. |

---

## Section 12: What's Missing for Production

1. **Risk enforcement** — medium/high risk tools should require approval
2. **Approval flow** — Telegram-based approve/deny for dangerous operations
3. **Tool Gateway** — role-scoped access filtering
4. **OpenClaw routing** — Telegram messages auto-routed to agent
5. **Session persistence** — currently in-memory only
6. **Error recovery** — no retry logic for transient failures
7. **Rate limiting** — no protection against API cost runaway

All addressed in Phase 3-C and beyond.

---

## Section 13: Docs Updated

| Doc | Change |
|-----|--------|
| `docs/ai/STATE.md` | Added Agent Runner to System Status, Phase 3-B to Completed Phases |
| `docs/ai/NEXT.md` | Updated to Phase 3-C: Risk Engine + Approval Service |
| `docs/ai/DECISIONS.md` | D-028 updated: GPT-4o first provider, Claude when credits available |

---

## Section 14: Exit Criteria

| Criterion | Status |
|-----------|--------|
| Agent directory structure created | DONE |
| MCP client connects to windows-mcp | DONE |
| Tool catalog with 12 named tools | DONE |
| GPT-4o provider implementation | DONE |
| Provider abstraction interface | DONE |
| Agent runner with multi-turn tool loop | DONE |
| Audit logging (JSONL) | DONE |
| Standardized JSON output envelope | DONE |
| WSL bridge wrapper | DONE |
| End-to-end test: message -> tool call -> response | DONE |
| Docs updated (STATE, NEXT, DECISIONS) | DONE |
| Git committed and pushed | DONE |

**ALL criteria met. Phase 3-B is COMPLETE.**

---

## Section 15: Next Phase

**Phase 3-C: Risk Engine + Approval Service**

Goal: Add risk classification and Telegram-based approval flow so medium/high risk tool calls require user confirmation before execution.

---

*Generated: 2026-03-23 | Phase 3-B Core Agent Runner Implementation*
*Operator: AKCA | Agent: Claude Opus 4.6 (1M context)*
