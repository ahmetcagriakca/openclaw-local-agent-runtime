# Azure OpenAI Deployment Inventory — S77

**Date:** 2026-04-07
**Verified by:** Claude Code (Session 52)

## Deployment Details

| Field | Value |
|-------|-------|
| Endpoint | `https://abdul-m9ji74es-eastus2.openai.azure.com/` |
| API Path | `/openai/responses` |
| API Version | `2025-04-01-preview` |
| Deployment/Model | `gpt-5.3-codex-cagri` |
| Region | eastus2 |
| Auth Mode | api-key (header: `api-key`) |
| Service Tier | auto |
| Env Vars | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` |

## Capability Matrix

| Capability | Supported | Evidence |
|-----------|-----------|----------|
| Text generation | YES | Smoke test: "pong" response, HTTP 200 |
| Function calling (tools) | YES | Tools accepted, strict mode auto-applied |
| Parallel tool calls | YES | `parallel_tool_calls: true` in response |
| Content filters | YES | 6 categories active (jailbreak, hate, sexual, violence, self_harm, protected_material) |
| Responses API (input-based) | YES | `/openai/responses` endpoint, `input` field |
| Reasoning | Available | `reasoning.effort` field present, default "none" |
| Streaming | TBD | Not tested in smoke — to verify in T-77.06 |
| MCP | NO | Not natively supported by Azure OpenAI |
| Code interpreter | NO | Not available via Responses API |
| Browser / web search | NO | Not available |

## Constraints

| Constraint | Value |
|-----------|-------|
| min_output_tokens | 16 |
| Retirement date | Unknown — monitor Azure portal |
| Rate limits | Default tier — monitor via 429 responses |

## Response Format

Responses API returns:
- `output[]` array with message objects
- Each message has `content[]` with `output_text` type
- Tool calls appear as `function_call` type in output
- `usage` with `input_tokens`, `output_tokens`, `total_tokens`
- `status`: "completed" on success

## Env Var Mapping

```
AZURE_OPENAI_ENDPOINT=https://abdul-m9ji74es-eastus2.openai.azure.com/
AZURE_OPENAI_API_KEY=<from APIM_KEY>
AZURE_OPENAI_DEPLOYMENT=gpt-5.3-codex-cagri
AZURE_OPENAI_API_VERSION=2025-04-01-preview
```
