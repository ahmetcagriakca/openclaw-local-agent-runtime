# S77 — Azure OpenAI Provider Foundation

- **Goal:** Azure OpenAI'ı primary provider olarak entegre et, fallback chain kur, telemetry ekle.
- **Decision dependency:** D-148 (frozen)
- **Prerequisite:** D-148 frozen. No hard dependency on cleanup/migration — provider integration is architecturally independent. If cleanup is still in progress, S77 may run in parallel.
- **Sprint class:** Product
- **Mutation budget:** 5

-----

## Gates

### Gate A — Foundation PASS
- Config/schema validated
- Azure provider adapter works (mock + unit)
- Health + retirement guard works
- Telemetry emits provider selection events
- Fallback chain works (Azure disabled → OpenAI/Anthropic handles)
- Canonical request/response contract used by ALL providers (including fallback)

### Gate B — Broad Default PASS (post-Foundation)
- Live Azure smoke test passes against real deployment
- Fallback proven end-to-end
- Routing logs show correct provider choice for ≥ 5 different task types
- No unresolved capability mismatch
- Operator kill switch verified
- Gate B is NOT required for sprint closure — it gates Phase 2 (Safe Activation)

-----

## Task Breakdown

### T-77.00: Azure tenant/deployment inventory + compatibility proof

**Scope:**
- Verify live Azure endpoint, deployment name, region, auth mode, api version
- Record actual supported capabilities for the target deployment (function calling, MCP, streaming, etc.)
- Record known unsupported paths (code interpreter, browser, etc.)
- Record retirement date and fallback target deployment
- Record rate-limit / quota assumptions if available
- Produce frozen inventory artifact

**Acceptance criteria:**
- `azure-deployment-inventory.md` artifact exists
- Target deployment proven callable (raw curl/SDK smoke)
- Supported/unsupported capability matrix frozen
- S77 implementation targets a real deployment, not assumptions

**Evidence:** `azure-deployment-inventory.md`, `azure-smoke-precheck.txt`

---

### T-77.01: AzureDeploymentConfig + agent-config.json schema

**Scope:**
- `AzureDeploymentConfig` dataclass: endpoint, deployment_name, api_version, auth_mode, region, capabilities list, retirement_date, timeout, retry_policy
- `agent-config.json`'a `azure-openai` agent entry eklenmesi
- `.env.example`'a Azure env vars eklenmesi
- Config validation: eksik/geçersiz field → startup deny (D-013 pattern)

**Acceptance criteria:**
- Config load + validate çalışıyor
- Eksik endpoint → ValueError
- Retirement date geçmişse → warning log + `retired: true` flag

**Evidence:** pytest, config validation output

---

### T-77.02: AzureOpenAIProvider adapter + canonical contract migration

**Scope:**
- `agent/providers/azure_openai_provider.py` — `AgentProvider` base'den türer
- Azure OpenAI SDK (`openai.AzureOpenAI`) kullanır
- Responses API contract: `input`-based request normalization
- Function calling / tool support
- Error mapping: 404 (deployment not found), 401 (auth), 429 (rate limit), timeout
- **Canonical contract migration:** `base.py`'da `TaskRequest` / `ProviderResponse` tanımla. Azure adapter bu contract'ı kullanır.
- **Existing provider migration:** GPTProvider, ClaudeProvider, OllamaProvider da aynı canonical `TaskRequest` input ve `ProviderResponse` output contract'ına migrate edilir. Bu olmadan fallback path legacy-coupled kalır.

**Acceptance criteria:**
- `AzureOpenAIProvider.chat()` çalışıyor (mock + integration)
- Tool call roundtrip (function calling)
- Error cases unit tested (404, 401, 429, timeout)
- `AgentResponse` canonical format'a dönüyor
- **GPTProvider, ClaudeProvider, OllamaProvider canonical TaskRequest kabul ediyor**
- **Tüm provider'lar canonical ProviderResponse üretiyor**
- No provider-specific branching outside provider layer

**Evidence:** pytest, mock roundtrip output

---

### T-77.03: Provider factory + routing policy

**Scope:**
- `factory.py`'a `azure-openai` branch eklenmesi
- `ProviderRoutingPolicy` class: primary/fallback rules
  - Default: Azure for all standard workloads
  - Fallback: unsupported capability → OpenAI/Anthropic
  - Fallback: unhealthy → next provider
  - Fallback: kill switch → skip Azure entirely
- Routing policy config in `agent-config.json`

**Acceptance criteria:**
- Factory creates Azure provider from config
- Routing policy selects Azure as default
- Kill switch (`azure.enabled=false`) → fallback provider selected
- Unsupported tool → fallback triggered
- **Fallback path uses canonical TaskRequest/ProviderResponse (not legacy adapter)**
- **Test: Azure → Anthropic fallback roundtrip**
- **Test: Azure → OpenAI fallback roundtrip**
- **Test: Azure disabled → fallback handles full workload**

**Evidence:** pytest, routing decision log output

---

### T-77.04: AzureHealthCheck + retirement guard

**Scope:**
- Health check: Azure endpoint liveness probe
- Retirement guard: deployment retirement_date check
  - 30 days before retirement → warning log
  - Past retirement → provider marked unhealthy → fallback
- `agents_api.py` ve `health_api.py`'a Azure eklenmesi

**Acceptance criteria:**
- Health check returns ok/error/unavailable
- Retirement guard warns at 30 days
- Retirement guard blocks at retirement date
- Health API lists Azure alongside existing providers

**Evidence:** pytest, health endpoint output

---

### T-77.05: ProviderSelectionTelemetry

**Scope:**
- Her agent call'da provider seçim event'i loglanır
- Event fields: timestamp, task_type, selected_provider, selection_reason, fallback_used, fallback_reason
- `policy-telemetry.jsonl`'e yazılır (D-129 audit pattern)

**Acceptance criteria:**
- Provider selection event emitted on every call
- Fallback event includes reason
- Events queryable in telemetry log

**Evidence:** pytest, telemetry log sample

---

### T-77.06: Integration smoke test + evidence collection

**Scope:**
- Azure endpoint'e gerçek call (text generation)
- Function call roundtrip (basit tool)
- Fallback test: Azure disabled → OpenAI handles
- Health check integration test
- Sprint evidence collection

**Acceptance criteria:**
- Smoke test passes against live Azure deployment
- Fallback verified with kill switch
- Evidence packet complete

**Evidence:** pytest-output.txt, integration-smoke.txt, telemetry-sample.jsonl

---

### T-77.07: Review gate + closure

**Scope:**
- `report.md` hazırla
- GPT cross-review
- Evidence bundle doğrulama
- Sprint closure check

**Acceptance criteria:**
- All T-77.00→T-77.06 DONE (5/5 rule)
- GPT review PASS
- `sprint-closure-check.sh` ELIGIBLE

**Evidence:** review-summary.md, closure-check output

-----

## Evidence Checklist

| Evidence | Source |
|---|---|
| `azure-deployment-inventory.md` | T-77.00 — live deployment verification |
| `azure-smoke-precheck.txt` | T-77.00 — raw curl/SDK smoke output |
| `pytest-output.txt` | `cd agent && python -m pytest tests/ -v` |
| `vitest-output.txt` | `cd frontend && npx vitest run` (regression) |
| `tsc-output.txt` | `cd frontend && npx tsc --noEmit` (regression) |
| `lint-output.txt` | Linter pass |
| `integration-smoke.txt` | Live Azure roundtrip |
| `telemetry-sample.jsonl` | Provider selection events |
| `grep-evidence.txt` | `grep -r "azure" agent/providers/` |
| `review-summary.md` | GPT cross-review result |
| `file-manifest.txt` | Created/modified file list |

-----

## File Manifest (Expected)

| File | Action | Task |
|---|---|---|
| `agent/providers/azure_openai_provider.py` | Create | T-77.02 |
| `agent/providers/factory.py` | Modify | T-77.03 |
| `agent/providers/base.py` | Modify | T-77.02 (canonical types) |
| `agent/providers/routing_policy.py` | Create | T-77.03 |
| `agent/providers/azure_health.py` | Create | T-77.04 |
| `agent/api/agents_api.py` | Modify | T-77.04 |
| `agent/api/health_api.py` | Modify | T-77.04 |
| `agent/context/policy_telemetry.py` | Modify | T-77.05 |
| `agent-config.json` | Modify | T-77.01 |
| `.env.example` | Modify | T-77.01 |
| `config/capabilities.json` | Modify | T-77.01 |
| `agent/tests/test_azure_provider.py` | Create | T-77.02 |
| `agent/tests/test_routing_policy.py` | Create | T-77.03 |
| `agent/tests/test_azure_health.py` | Create | T-77.04 |
| `agent/tests/test_provider_telemetry.py` | Create | T-77.05 |

-----

## Open Decisions

None — D-148 must be frozen at kickoff gate. No open decisions allowed in execution.

-----

## Risks

| Risk | Mitigation |
|---|---|
| Azure deployment name mismatch → 404 | Config validation at startup (T-77.01) |
| Responses API contract farklılıkları | SDK handles normalization; error mapping covers gaps (T-77.02) |
| Model retirement during sprint | Retirement guard active from day 1 (T-77.04) |
| Rate limiting on Azure | Retry policy in config; fallback on 429 (T-77.03) |
