# D-133: Policy Engine Contract

**Status:** Frozen
**Sprint:** 48 (Task 48.5)
**Date:** 2026-03-30
**Dependencies:** D-128 (risk classification), B-013 (policyContext), B-014 (timeoutSeconds)

## Decision

The Vezir policy engine is a rule-based, config-driven, fail-closed evaluation layer that runs pre-stage in the mission controller.

### Architecture

- **Type:** Rule-based, config-driven
- **Default behavior:** Fail-closed (deny if no matching rule)
- **Evaluation point:** Controller, pre-stage (before specialist invocation)
- **Storage:** `config/policies/` directory, one rule per file (YAML)
- **Persistence:** D-106 consistent (JSON file store)

### Input Contract

The policy engine receives four inputs at each stage evaluation:

1. **policyContext** (B-013):
   - `dependencyStates`: per-dependency availability (MCP reachable/degraded/unreachable)
   - `riskLevel`: D-128 computed at mission creation
   - `sourceFreshness`: per-source age (normalizer metadata)
   - `retryability`: mission/stage retry eligibility
   - `interactiveCapability`: tool/UI availability state
   - `tenantLimits`: D-121 guardrail thresholds

2. **timeoutConfig** (B-014):
   - `missionSeconds`: mission-level timeout (default 3600)
   - `stageSeconds`: stage-level timeout (default 600)
   - `toolSeconds`: tool-level timeout (default 120)

3. **missionConfig**:
   - `goal`: mission objective
   - `complexity`: tier (trivial/simple/medium/complex)
   - `stages`: specialist list

4. **toolRequest** (per tool call):
   - `tool`: requested tool name
   - `target`: target resource
   - `parameters`: tool parameters

### Output Contract

Each evaluation returns one of four decisions:

| Decision | Effect |
|----------|--------|
| `allow` | Proceed with stage/tool execution |
| `deny` | Stage skip or mission abort (configurable) |
| `escalate` | Transition to `waiting_approval` state |
| `degrade` | Use fallback tool/provider |

### Default Rules

| Condition | Decision | Rationale |
|-----------|----------|-----------|
| WMCP unreachable | `degrade` | MCP graceful degradation (S46 fix) |
| Risk=critical + no approval | `escalate` | D-128 risk classification |
| Stage timeout exceeded | `timed_out` | B-014 timeout contract |
| Budget exceed | `deny` new stages | Token budget enforcement (D-102) |

### Rule Format (YAML)

```yaml
# config/policies/wmcp-degradation.yaml
name: wmcp-degradation
priority: 100
condition:
  dependency_state:
    wmcp: unreachable
decision: degrade
fallback:
  provider: ollama
  tools: []
```

### S49 Boundary

D-133 defines the contract only. Sprint 49 scope:
- Engine code implementation
- Rule CRUD API endpoints
- Rule evaluation tests
- Integration with controller pre-stage hook

## Validation

- policyContext (B-013) input fields match D-133 input contract
- timeoutConfig (B-014) input fields match D-133 input contract
- Output decisions (allow/deny/escalate/degrade) cover all mission controller states
- Default rules cover known failure modes (WMCP, risk, timeout, budget)
