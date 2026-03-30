# OTel Attribute Contract — Vezir Platform

**Status:** Internal standard (Sprint 48, 48.3c)
**Scope:** Naming convention for all OTel spans, metrics, and events.
**Migration:** Full OTel GenAI Semantic Conventions alignment deferred to S50+.

---

## Naming Convention

- **Namespace prefix:** `vezir.` for all custom metrics
- **Span attributes:** `{domain}.{attribute}` (e.g., `mission.id`, `stage.role`)
- **Metric instruments:** `vezir.{domain}.{metric}` (e.g., `vezir.mission.duration`)
- **Event types:** snake_case (e.g., `policy_denied`, `stage_failed`)

---

## Mission Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `mission.id` | string | Mission identifier | tracing.py |
| `mission.goal` | string | User's mission goal | tracing.py |
| `mission.complexity` | string | Complexity tier (trivial/simple/medium/complex) | tracing.py |
| `mission.stage_count` | int | Total planned stages | tracing.py |
| `mission.total_tokens` | int | Total tokens consumed | tracing.py |
| `mission.stages_completed` | int | Stages completed | tracing.py |
| `mission.error` | string | Error message (if failed) | tracing.py |
| `mission.abort_reason` | string | Abort reason (if aborted) | tracing.py |

## Stage Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `stage.name` | string | Stage identifier | tracing.py |
| `stage.role` | string | Specialist role | tracing.py |
| `stage.input_tokens` | int | Input token count | tracing.py |
| `stage.context_tokens` | int | Context tokens from assembler | tracing.py |
| `stage.artifact_tokens` | int | Artifact output tokens | tracing.py |
| `stage.total_consumed` | int | Total tokens consumed | tracing.py |
| `stage.tool_calls` | int | Tool call count | tracing.py |
| `stage.duration_ms` | int | Stage execution duration | tracing.py |
| `stage.error` | string | Error message (if failed) | tracing.py |

## Tool Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `tool.name` | string | Tool name | tracing.py |
| `tool.role` | string | Requesting role | tracing.py |
| `tool.permitted` | bool | Policy evaluation result | tracing.py |
| `tool.cleared` | bool | Budget cleared | tracing.py |
| `tool.response_tokens` | int | Response token count | tracing.py |
| `tool.latency_ms` | int | Tool execution latency | tracing.py |
| `tool.budget_decision` | string | Budget gate decision | tracing.py |
| `tool.blocked_reason` | string | Reason if blocked | tracing.py |
| `tool.truncated` | bool | Response was truncated | tracing.py |

## LLM Call Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `llm.model` | string | LLM model name | tracing.py |
| `llm.stage` | string | Stage context | tracing.py |
| `llm.input_tokens` | int | Input tokens | tracing.py |
| `llm.output_tokens` | int | Output tokens | tracing.py |
| `llm.cleared` | bool | Budget cleared | tracing.py |
| `llm.latency_ms` | int | LLM call latency | tracing.py |
| `llm.error` | string | Error message | tracing.py |

## Gate Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `gate.name` | string | Gate name (G1/G2/G3) | tracing.py |
| `gate.stage` | string | Stage at gate | tracing.py |
| `gate.result` | string | Gate result | tracing.py |
| `gate.approval_id` | string | Approval request ID | tracing.py |
| `gate.tool` | string | Tool requiring approval | tracing.py |
| `gate.risk` | string | Risk classification | tracing.py |
| `gate.decision` | string | Approval decision | tracing.py |

## Budget Attributes

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `budget.exceeded` | bool | Budget exceeded flag | tracing.py |
| `budget.check` | string | Budget check result | tracing.py |
| `budget.usage_pct` | float | Usage percentage | tracing.py |
| `budget.current` | int | Current token usage | tracing.py |
| `budget.limit` | int | Token budget limit | tracing.py |

## Correlation

| Attribute | Type | Description | Source |
|-----------|------|-------------|--------|
| `vezir.correlation_id` | string | Cross-span correlation ID | tracing.py |

---

## Metric Instruments (17)

### Counters (6)

| Name | Unit | Attributes | Description |
|------|------|------------|-------------|
| `vezir.mission.total` | count | status, complexity | Total missions executed |
| `vezir.tool_call.total` | count | tool, decision | Total tool calls |
| `vezir.budget.gate_triggered` | count | check_type | Budget gate triggers |
| `vezir.rework.total` | count | — | Total rework cycles |
| `vezir.bypass.detected` | count | tool | Policy bypass detections |
| `vezir.anomaly.detected` | count | rule | Anomaly detections |

### Histograms (11)

| Name | Unit | Attributes | Description |
|------|------|------------|-------------|
| `vezir.mission.duration` | ms | complexity | Mission execution time |
| `vezir.mission.tokens` | tokens | — | Tokens per mission |
| `vezir.stage.duration` | ms | complexity | Stage execution time |
| `vezir.stage.tokens.input` | tokens | stage | Input tokens per stage |
| `vezir.stage.tokens.output` | tokens | stage | Output tokens per stage |
| `vezir.tool_call.duration` | ms | tool | Tool call latency |
| `vezir.tool_call.response_tokens` | tokens | tool | Response tokens per tool |
| `vezir.llm_call.duration` | ms | stage | LLM call latency |
| `vezir.llm_call.input_tokens` | tokens | stage | LLM input tokens |
| `vezir.llm_call.output_tokens` | tokens | stage | LLM output tokens |
| `vezir.budget.approval.duration` | ms | decision | Approval wait time |

---

## Policy Event Types (6)

| Event | Description | Source |
|-------|-------------|--------|
| `policy_denied` | Tool request denied by policy | policy_telemetry.py |
| `policy_soft_denied` | Tool request soft-denied (logged, not blocked) | policy_telemetry.py |
| `filesystem_tool_allowed` | Filesystem tool access granted | policy_telemetry.py |
| `path_resolution_failed` | File path resolution failed | policy_telemetry.py |
| `mutation_surface_mismatch` | Mutation API surface mismatch | policy_telemetry.py |
| `budget_exhausted` | Token budget exhausted | policy_telemetry.py |

---

## Controller Telemetry Events (added Sprint 48)

| Event | Description | Source |
|-------|-------------|--------|
| `mission_timed_out` | Mission exceeded timeout (B-014) | controller.py |
| `stage_timeout_exceeded` | Stage exceeded timeout (B-014) | controller.py |
| `mission_state_transition` | State machine transition | mission_state.py |
| `invalid_state_transition` | Invalid state transition attempt | mission_state.py |
| `stage_failed` | Stage execution failure | controller.py |
| `complexity_classified` | Mission complexity determined | controller.py |
| `planning_llm_fallback` | Planning fell back to LLM | controller.py |
| `recovery_triage_decision` | Recovery triage action taken | controller.py |
| `quality_gate_checked` | Quality gate evaluation | controller.py |
| `model_selected` | Agent/model selected for stage | controller.py |

---

## Future: OTel GenAI Semantic Conventions

Current attributes use Vezir-internal naming. Full alignment with
[OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
is a S50+ carry-forward item. Key mapping:

| Current | GenAI Convention | Status |
|---------|------------------|--------|
| `llm.model` | `gen_ai.request.model` | S50+ |
| `llm.input_tokens` | `gen_ai.usage.input_tokens` | S50+ |
| `llm.output_tokens` | `gen_ai.usage.output_tokens` | S50+ |
| `tool.name` | `gen_ai.tool.name` | S50+ |
