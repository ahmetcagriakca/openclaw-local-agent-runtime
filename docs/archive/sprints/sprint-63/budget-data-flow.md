# Budget Enforcement Data Flow — Sprint 63 (B-138)

**Decision:** D-139 (Controller Decomposition Boundary Freeze)
**Issue:** #326 (B-138)
**Status:** Design-only — no implementation

---

## Ownership Model

```
┌──────────────────────────────────────────────────────────┐
│                    MissionController                      │
│                                                          │
│  Per-stage: cumulative_tokens += stage.token_report      │
│  Per-stage: policyContext.totalTokens = cumulative       │
│                                                          │
│  OWNER: token accumulation + context building            │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│                     PolicyEngine                          │
│                                                          │
│  Rule: budget_exceeded                                   │
│    IF totalTokens >= max_token_budget THEN deny          │
│                                                          │
│  Rule: budget_warning                                    │
│    IF totalTokens >= max_token_budget * 0.8 THEN alert   │
│                                                          │
│  OWNER: budget evaluation + decision                     │
└───────────────────────┬──────────────────────────────────┘
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
┌──────────────────┐   ┌──────────────────┐
│   ALLOW           │   │   DENY            │
│   (continue)      │   │   "budget_        │
│                   │   │    exceeded"       │
│   IF >= 80%:      │   │   mission →       │
│   AlertEngine     │   │   FAILED          │
│   → Telegram      │   │                   │
└──────────────────┘   └──────────────────┘
```

---

## Token Tracking Flow

### Per-Stage Accumulation

```python
# In execute_mission, after stage completes (line ~432):
stage["token_report"] = result.get("tokenReport")

# Future (S64 B-140):
cumulative_tokens = sum(
    s.get("token_report", {}).get("total_tokens", 0)
    for s in mission["stages"]
    if s.get("status") == "completed"
)
mission["cumulativeTokens"] = cumulative_tokens
```

### Policy Context Integration

```python
# In build_policy_context (mission/policy_context.py):
# Current: totalTokens field exists but not populated from cumulative
# Future (S64): populate from mission["cumulativeTokens"]
policy_ctx = PolicyContext(
    totalTokens=mission.get("cumulativeTokens", 0),
    maxTokenBudget=mission.get("maxTokenBudget", 1_000_000),
    # ...existing fields...
)
```

### Policy Rule Evaluation

```yaml
# config/policies/budget-enforcement.yaml (draft)
# Evaluated by PolicyEngine.evaluate()
- name: budget_exceeded
  condition: "totalTokens >= maxTokenBudget"
  decision: deny
  reason: "Mission token budget exceeded: {totalTokens}/{maxTokenBudget}"

- name: budget_warning
  condition: "totalTokens >= maxTokenBudget * 0.8"
  decision: allow
  action: alert
  alert_rule: budget_warning_80pct
  reason: "Mission approaching budget limit: {totalTokens}/{maxTokenBudget} (80%)"
```

---

## Data Sources

| Data | Source | When Set |
|------|--------|----------|
| `stage.token_report.total_tokens` | LLM provider response | After each stage completes |
| `mission.cumulativeTokens` | Controller accumulation | After each stage (S64) |
| `mission.maxTokenBudget` | Mission config / default | At mission creation |
| `policyContext.totalTokens` | `build_policy_context()` | Before each stage evaluation |
| `policyContext.maxTokenBudget` | Mission config | Before each stage evaluation |

## Alert Integration

| Threshold | Action | Channel |
|-----------|--------|---------|
| 80% of budget | `alert_engine.fire("budget_warning_80pct")` | Telegram |
| 100% of budget | `PolicyDecision.DENY` → mission FAILED | Mission state |

## Default Budget

| Complexity | Default max_token_budget |
|------------|------------------------|
| trivial | 50,000 tokens |
| standard | 200,000 tokens |
| complex | 500,000 tokens |
| critical | 1,000,000 tokens |

**Override:** Per-mission config via `maxTokenBudget` field in mission creation request.

---

## Implementation Plan (S64 — B-140)

1. Add `cumulativeTokens` field to mission dict
2. Accumulate after each stage in `execute_mission`
3. Wire `totalTokens` in `build_policy_context()`
4. Add budget rules to `config/policies/`
5. Add budget alert rule to AlertEngine
6. Add tests: budget deny, budget warning, budget override
