# D-148: Azure OpenAI Primary Provider Adoption

- **ID:** D-148
- **Title:** Azure OpenAI Primary Provider Adoption
- **Status:** frozen
- **Phase:** S77
- **Date:** 2026-04-07 (frozen)
- **Owner:** AKCA
- **Recommended by:** Claude (architecture analysis) + GPT (cross-review)

-----

## Context

- Mevcut provider layer 3 adapter içeriyor: OpenAI (GPT), Anthropic (Claude), Ollama (local). Hepsi `messages`-based legacy contract kullanıyor.
- Azure OpenAI artık Responses API (`input`-based, `messages` değil) üzerinden çalışıyor. v1 API güncel özellikler için zorunlu.
- Azure'da model retirement gerçek operasyon riski — bazı `gpt-4o` / `gpt-4o-mini` standard deployment'ları 2026-03-31'de retire olmuş.
- Operator'ın Azure tenant'ı maliyet avantajı sağlıyor — enterprise billing/governance tek yüzey.
- `model` alanı Azure'da deployment name ile eşleşmek zorunda; aksi halde 404.
- Dynamic role selection (D-150) için en az iki aktif provider gerekli — Azure eklenmeden routing policy test edilemez.

-----

## Decision

1. **Azure OpenAI = default primary provider** for agent calls.
2. **Mevcut OpenAI / Anthropic = controlled fallback.** Silinmez, degrade edilmez, ama default routing'den çıkar.
3. **Responses API contract zorunlu.** Azure adapter `messages`-based legacy path kullanmaz.
4. **Tüm provider'lar tek canonical internal request schema'ya normalize edilir.**
5. **Retirement-aware deployment guard zorunlu.** Retirement window'a giren deployment fail-closed veya reroute.
6. **Fallback deterministic.** Unsupported capability, unhealthy deployment, budget aşımı, latency threshold → otomatik reroute.
7. **Provider seçimi telemetry'de traceable.** Her agent call'da seçilen provider, nedeni ve fallback durumu loglanır.

-----

## Azure-First Routing Semantics

**Azure-first MEANS:**
- All agent calls enter `ProviderRoutingPolicy` — no call bypasses the router.
- Azure is the default primary candidate in the routing table.
- Unsupported capability, unhealthy deployment, or high-risk mismatch → deterministic reroute to fallback provider.
- Routing decision is logged with reason on every call.

**Azure-first does NOT mean:**
- Force every call to Azure regardless of capability or health.
- Remove or disable fallback providers.
- Bypass provider health check or retirement guard.
- Treat Azure as the only provider — it is the preferred provider.

-----

## Non-Negotiable Rules

| # | Rule |
|---|---|
| 1 | Azure primary path is `execute(TaskRequest) -> ProviderResponse` via Responses API. Legacy `chat(messages)` compatibility shim is permitted as a temporary boundary adapter until all callers migrate to `execute()`. The shim MUST NOT be the primary interface — `execute()` is canonical. |
| 2 | All provider calls go through one internal canonical request schema. |
| 3 | Fallback remains enabled — no single-provider hard lock. |
| 4 | Unsupported capability must fail-closed or reroute deterministically. |
| 5 | Retirement-aware deployment guard is mandatory. |
| 6 | Provider choice must be traceable in runtime telemetry. |
| 7 | No Azure-specific branching outside provider layer — core runtime stays provider-agnostic. |
| 8 | Kill switch: `azure.enabled = false` → all traffic falls back to existing provider. |

-----

## Internal Canonical Request Schema (v1)

### TaskRequest

| Field | Type | Required | Description |
|---|---|---|---|
| `task_type` | string | Yes | review, analysis, implementation, tool_call, research |
| `prompt` | string | Yes | Input text/instruction |
| `tools_required` | list[str] | No | Tool names needed for this task |
| `risk_tier` | enum | Yes | low / medium / high / critical (D-128) |
| `provider_preference` | string | No | Explicit override: azure / openai / anthropic / ollama |

**Deferred to v2:** `cost_budget`, `latency_target`, `browser_mode`, `verification_required` — ölçüm datası olmadan threshold belirlenemez.

### ProviderResponse

| Field | Type | Description |
|---|---|---|
| `provider` | string | azure-openai / openai / anthropic / ollama |
| `deployment` | string | Azure deployment name or model ID |
| `model_family` | string | gpt-4o / claude-sonnet / llama etc. |
| `tool_calls` | list | Executed tool calls |
| `finish_reason` | string | end_turn / tool_use / error |
| `token_usage` | object | prompt_tokens, completion_tokens, total |
| `latency_ms` | int | End-to-end call latency |
| `fallback_used` | bool | Whether fallback provider was invoked |
| `error_class` | string | null if success; timeout / auth / deployment_not_found / unsupported_capability |

-----

## v1 Components

| Component | Responsibility |
|---|---|
| `AzureOpenAIProvider` | Adapter: auth, request normalization (Responses API), response parsing, error mapping |
| `AzureDeploymentConfig` | Config object: endpoint, deployment_name, api_version, auth_mode, region, capabilities, retirement_date, timeout, retry_policy |
| `AzureHealthCheck` | Liveness probe + retirement guard — unhealthy/retired → fallback triggered |
| `ProviderRoutingPolicy` | Primary/fallback selection rules — deterministic, config-driven |
| `ProviderSelectionTelemetry` | Logs provider choice, reason, fallback status to policy-telemetry.jsonl |

-----

## v1 Scope

### Included

- Text generation
- Structured reasoning
- Function calling (tools)
- Standard agent orchestration (mission mode)
- MCP tool usage (Azure Responses API MCP support)
- Health check + retirement guard

### Excluded in v1

- Browser mutation as default path
- Code Interpreter (ek maliyet, ayrı karar gerektirir)
- Provider-specific shortcuts that leak into core runtime
- Hard delete of existing fallback providers
- Cost/latency optimization (requires measurement data from v1)

-----

## Routing Policy v1

### Primary (Azure)

- Review, planning, analysis workloads
- Standard implementation tasks
- Tool-calling / function-calling workloads
- MCP-based orchestration

### Fallback Triggers

| Condition | Action |
|---|---|
| Requested tool/capability unsupported by Azure | Reroute to capable provider |
| Azure deployment unhealthy | Reroute to fallback |
| Retirement window breached | Reroute to fallback + alert operator |
| Auth failure | Reroute to fallback + alert |
| Latency/error threshold exceeded | Reroute to fallback (threshold TBD after v1 data) |
| Explicit `provider_preference` override | Honor override |

-----

## Rollout Plan

| Phase | Scope |
|---|---|
| Phase 1 — Foundation | Provider adapter, config, health check, deployment registry, kill switch |
| Phase 2 — Safe Activation | Route low-risk tasks to Azure default, keep fallback active, record telemetry |
| Phase 3 — Broad Default | Expand Azure default to most agent calls, explicit exceptions only |
| Phase 4 — Optimization | Tune deployment by task type, add cheaper/premium deployment tiers |

-----

## Required Config (.env / agent-config.json)

```
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_API_VERSION=2025-03-01-preview
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
AZURE_OPENAI_REGION=<region>
AZURE_OPENAI_RETIREMENT_DATE=<ISO-8601>
AZURE_OPENAI_AUTH_MODE=api_key  # or entra_id
```

-----

## Verification

| Test | Type |
|---|---|
| Provider smoke test (text generation roundtrip) | Integration |
| Function-call roundtrip | Integration |
| MCP tool roundtrip | Integration |
| Unsupported capability → reroute | Unit + Integration |
| Health-check failure → fallback | Unit |
| Deployment name mismatch → 404 → fallback | Unit |
| Retirement guard → deny + alert | Unit |
| Telemetry emission (provider choice logged) | Unit |
| Kill switch (azure.enabled=false → full fallback) | Integration |
| Canonical request schema normalization | Unit |

-----

## Impacted Files

| File | Change |
|---|---|
| `agent/providers/azure_openai_provider.py` | New |
| `agent/providers/factory.py` | Add azure-openai branch |
| `agent/providers/base.py` | Extend with canonical request/response types |
| `agent-config.json` | Add azure-openai agent entry |
| `.env.example` | Add Azure env vars |
| `agent/api/agents_api.py` | Add Azure to provider liveness check |
| `agent/api/health_api.py` | Add Azure to health components |
| `agent/context/policy_telemetry.py` | Add provider selection event type |
| `agent/mission/controller.py` | Use routing policy for provider selection |
| `config/capabilities.json` | Add Azure provider capabilities |
| Tests | New test module + existing provider test updates |

-----

## Trade-offs

| + | - |
|---|---|
| Enterprise billing/governance tek yüzey | Azure-specific API contract complexity (Responses API) |
| Maliyet avantajı (operator tenant) | Model retirement tracking operasyonel yük |
| MCP native support in Responses API | Region/deployment availability constraints |
| Multi-provider routing test edilebilir hale gelir | v1 component sayısı artışı |

-----

## Rollback / Reversal

- Kill switch: `azure.enabled = false` in config → all traffic reverts to existing providers
- No core runtime change → rollback is config-only
- Azure provider module can be disabled without code deletion

-----

## Dependencies

- D-024 (Tool Gateway — role-scoped) — Azure tools same gateway'den geçer
- D-028 (Direct SDK — no framework) — Azure SDK direct kullanılır
- D-030 (Same LLM differentiated by prompt+policy) — Azure da aynı pattern'e uyar
- D-117 (Auth contract) — Azure auth mode provider-internal, core auth unchanged

-----

## Decision Lifecycle

| Date | Event |
|---|---|
| 2026-04-06 | Proposed by Claude (architecture analysis) |
| 2026-04-07 | Frozen by operator — sprint S77 kickoff |
