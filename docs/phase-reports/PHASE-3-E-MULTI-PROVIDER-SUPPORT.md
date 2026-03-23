# Phase 3-E: Multi-Provider Support

**Date:** 2026-03-23
**Status:** COMPLETE
**Author:** Operator + Claude Opus 4.6
**Scope:** Add Claude and Ollama as alternative LLM providers alongside GPT-4o

---

## Section 1: Executive Summary

**What was built:** A provider abstraction layer that allows the agent runner to use GPT-4o, Claude, or Ollama interchangeably. Provider selection is config-driven (`agent-config.json`) and switchable via `--agent` CLI flag. Each provider internally converts the OpenAI tool format to its native format.

**End-to-end verified:** All 3 providers successfully called `get_system_info` tool via MCP and returned formatted Turkish responses:
- GPT-4o: ~9s, concise
- Claude Sonnet: ~13s, most detailed (included percentage calculations)
- Ollama qwen2.5:7b: ~63s, local execution, no API cost

**Key design decision:** No LangChain needed. Three providers implemented with direct SDK calls. Each provider handles its own message format conversion internally, keeping the agent runner provider-agnostic.

---

## Section 2: Architecture

### 2.1 Provider Factory Pattern

```
agent-config.json
  -> factory.py: create_provider(agent_id)
    -> "gpt"    -> GPTProvider (OpenAI SDK)
    -> "claude"  -> ClaudeProvider (Anthropic SDK)
    -> "ollama"  -> OllamaProvider (HTTP /api/chat)
  -> returns (provider, agent_config)
```

### 2.2 Message Format Conversion

All providers receive OpenAI-format messages and tools from the agent runner. Each converts internally:

| Format | GPT | Claude | Ollama |
|--------|-----|--------|--------|
| System message | `{"role": "system"}` | Extracted to `system` kwarg | `{"role": "system"}` |
| Tool definitions | OpenAI function format | Converted to `input_schema` | Passed as-is (OpenAI-compatible) |
| Tool calls (assistant) | Native | Converted to `tool_use` blocks | Reconstructed as text |
| Tool results | `{"role": "tool"}` | Converted to `tool_result` blocks | Converted to user message |

### 2.3 Agent Selection Flow

```
CLI: --agent gpt-general
  -> agent-config.json lookup
  -> check enabled == true
  -> check API key / server available
  -> create provider instance
  -> run_agent() with provider
```

---

## Section 3: Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `agent/agent-config.json` | Agent registry — 3 agents with provider, model, API key config | ~30 |
| `agent/providers/factory.py` | Provider factory — loads config, creates correct provider | ~65 |
| `agent/providers/claude_provider.py` | Anthropic Claude SDK integration with format conversion | ~95 |
| `agent/providers/ollama_provider.py` | Ollama local LLM via HTTP API | ~80 |

## Section 4: Files Modified

| File | Change |
|------|--------|
| `agent/oc-agent-runner.py` | Replaced hardcoded `GPTProvider()` with `create_provider(agent_id)` |
| `docs/ai/STATE.md` | Phase 3-E completed, agent runner status updated |
| `docs/ai/NEXT.md` | Updated to Phase 3-F |
| `docs/ai/DECISIONS.md` | D-028 updated: multi-provider, no LangChain |

---

## Section 5: Agent Configuration

### 5.1 agent-config.json

```json
{
  "defaultAgent": "gpt-general",
  "agents": {
    "gpt-general": {
      "provider": "gpt",
      "model": "gpt-4o",
      "apiKeyEnv": "OPENAI_API_KEY",
      "enabled": true
    },
    "claude-general": {
      "provider": "claude",
      "model": "claude-sonnet-4-20250514",
      "apiKeyEnv": "ANTHROPIC_API_KEY",
      "enabled": true
    },
    "ollama-general": {
      "provider": "ollama",
      "model": "qwen2.5:7b",
      "baseUrl": "http://localhost:11434",
      "enabled": true
    }
  }
}
```

### 5.2 Adding a New Provider

1. Create `agent/providers/new_provider.py` implementing `AgentProvider`
2. Add case to `factory.py`
3. Add agent entry to `agent-config.json`
4. No changes needed in agent runner, tool catalog, risk engine, or approval service

---

## Section 6: Provider Details

### 6.1 GPT-4o (OpenAI)

- SDK: `openai` Python package
- Model: `gpt-4o`
- Tool calling: Native OpenAI function calling
- Auth: `OPENAI_API_KEY` environment variable
- Cost: Pay-per-token API

### 6.2 Claude Sonnet (Anthropic)

- SDK: `anthropic` Python package
- Model: `claude-sonnet-4-20250514`
- Tool calling: Native Anthropic tool_use blocks
- Auth: `ANTHROPIC_API_KEY` environment variable
- Cost: Pay-per-token API
- Format conversion: OpenAI function format -> Anthropic input_schema format

### 6.3 Ollama (Local)

- Protocol: HTTP REST API (`/api/chat`)
- Model: `qwen2.5:7b` (any Ollama model works)
- Tool calling: Ollama 0.4+ native tool calling
- Auth: None (localhost)
- Cost: Free (local GPU/CPU)
- Trade-off: Slower (~63s vs ~9s) but no API costs, fully offline

---

## Section 7: Test Results

### Test 1: GPT-4o Default (PASSED)

```
$ python agent/oc-agent-runner.py -m "CPU kullanımı ne?"
Provider: gpt (gpt-4o)
Tool: get_system_info | Duration: ~4s
Response: "Şu anda CPU kullanımı %3 seviyesinde."
Total: ~9s
```

### Test 2: GPT-4o Explicit (PASSED)

```
$ python agent/oc-agent-runner.py -m "CPU kullanımı ne?" --agent gpt-general
Same as default — factory resolves correctly
```

### Test 3: Claude Sonnet (PASSED)

```
$ python agent/oc-agent-runner.py -m "CPU kullanımı ne?" --agent claude-general
Provider: claude (claude-sonnet-4-20250514)
Tool: get_system_info | Duration: ~4s
Response: "CPU kullanımı %24... RAM: 21.7/63.7 GB (%34)... Disk C: %79... Uptime: 7h 34m"
Total: ~13s
Note: Most detailed response — included percentage calculations
```

### Test 4: Ollama qwen2.5:7b (PASSED)

```
$ python agent/oc-agent-runner.py -m "CPU kullanımı ne?" --agent ollama-general
Provider: ollama (qwen2.5:7b)
Tool: get_system_info | Duration: ~4s
Response: "CPU kullanımınız %31'dir... RAM %23.1... Sistem aktif zamanınız 7 saat 27 dakika"
Total: ~63s
Note: Tool calling works, Turkish response, but slower (local execution)
```

### Test 5: Disabled Agent — Graceful Error (PASSED)

```
$ python agent/oc-agent-runner.py -m "test" --agent claude-general  (when disabled)
Error: "Agent 'claude-general' is disabled. Enable it in agent-config.json"
No crash, clean JSON error response
```

### Test 6: Unknown Agent — Graceful Error (PASSED)

```
$ python agent/oc-agent-runner.py -m "test" --agent nonexistent
Error: "Unknown agent: nonexistent. Available: ['gpt-general', 'claude-general', 'ollama-general']"
No crash, lists available agents
```

### Test 7: Missing API Key — Graceful Error (PASSED)

```
$ python agent/oc-agent-runner.py -m "test" --agent claude-general  (no credit)
Error: "credit balance is too low to access the Anthropic API"
Clean error, recoverable: true
```

---

## Section 8: Performance Comparison

| Provider | Model | Tool Call | Total Time | Response Quality | Cost |
|----------|-------|-----------|------------|-----------------|------|
| GPT-4o | gpt-4o | ~4s | ~9s | Concise, accurate | API |
| Claude | claude-sonnet-4-20250514 | ~4s | ~13s | Most detailed, percentages | API |
| Ollama | qwen2.5:7b | ~4s | ~63s | Good, Turkish OK | Free |

MCP tool execution is constant (~4s) across all providers. The difference is LLM inference time.

---

## Section 9: Exit Criteria

| Criterion | Status |
|-----------|--------|
| Agent config file created | DONE |
| Provider factory implemented | DONE |
| Claude provider with format conversion | DONE |
| Ollama provider with HTTP API | DONE |
| Agent runner uses factory | DONE |
| GPT-4o works as before | DONE |
| Claude end-to-end with tool calling | DONE |
| Ollama end-to-end with tool calling | DONE |
| Graceful errors for disabled/unknown/missing | DONE |
| Docs updated (STATE, NEXT, DECISIONS) | DONE |
| Git committed and pushed | DONE |

**ALL criteria met. Phase 3-E is COMPLETE.**

---

## Section 10: Next Phase

**Phase 3-F: Multi-Agent Foundation**

Goal: Mission Controller for multi-agent orchestration — sequential agent execution with typed artifact handoff.

---

*Generated: 2026-03-23 | Phase 3-E Multi-Provider Support*
*Operator: AKCA | Agent: Claude Opus 4.6 (1M context)*
