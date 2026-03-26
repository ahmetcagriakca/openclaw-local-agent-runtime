# D-102: Event-Driven Token Governance Architecture (Complete)

**Status:** Frozen
**Date:** 2026-03-26
**Sprint:** 13 — Phase 5.5, Task 13.0

---

## Decision

Agent runtime adopts event-driven architecture for token governance. In-process EventBus with 13 ordered handlers, 28 event types, 3-layer bypass prevention, 4-tier budget enforcement.

**Current state:** L3/L4/L5 implemented inline. This decision adds EventBus + extracts into handlers + implements L1/L2 + enforcement + monitoring.

---

## EventBus API

```python
@dataclass(frozen=True)
class Event:
    type: str          # 28 event types
    ts: datetime
    data: dict
    source: str

class EventBus:
    on(event_type, handler) → None
    emit(event) → list[HandlerResult]    # halt stops propagation
    history(event_type?, since?) → list[Event]
```

---

## 13 Handlers (Registration Order)

| # | Handler | Role | Halts? |
|---|---------|------|--------|
| 1 | AuditTrail | Immutable chain-hash record | Never |
| 2 | TokenLogger | Operational log (jsonl) | Never |
| 3 | BypassDetector | MCP call vs bus event cross-check | Alert only |
| 4 | ToolPermissionHandler | Role-based tool access | Yes |
| 5 | BudgetEnforcer | 4-tier token budget | Yes |
| 6 | ApprovalGate | Operator pause/resume/abort | Yes |
| 7 | ToolExecutor | Only way to call MCP (on cleared) | — |
| 8 | LLMExecutor | Only way to call LLM (on cleared) | — |
| 9 | ContextAssembler | Tiered assembly (on request) | — |
| 10 | StageTransitionHandler | Validates context via bus | Yes |
| 11 | ReportCollector | Metrics aggregation | Never |
| 12 | AnomalyDetector | Pattern detection | Never |
| 13 | MetricsExporter | Real-time metrics dict | Never |

---

## Budget Tiers

| Tier | Soft Limit | Hard Limit | Action |
|------|-----------|-----------|--------|
| Tool response | 10K tok | 50K tok | Truncate / Block |
| Stage input | 50K tok | 80K tok | Warn / Pause+Approval |
| Stage cumulative | 100K tok | 150K tok | Warn / Pause+Approval |
| Mission total | — | 300K tok | Hard abort |

---

## Role Permissions

| Role | FileSystem.read | FileSystem.write | UIOverview | Snapshot | Terminal |
|------|----------------|-----------------|-----------|---------|---------|
| product_owner | ✅ | ❌ | ❌ | ❌ | ❌ |
| analyst | ✅ | ❌ | ✅ | ❌ | ❌ |
| architect | ✅ | ❌ | ✅ | ❌ | ❌ |
| developer | ✅ | ✅ | ✅ | ✅ | ✅ |
| pm | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## Context Assembly (L1 + L2)

**L1:** Stage boundary strips tool history. Only `StageResult.artifact_text` passes downstream.

**L2:** Tiered truncation:

| Tier | Distance | Max Chars |
|------|----------|-----------|
| A | Previous stage | 5,000 |
| B | 2 back | 2,000 |
| C | 3+ back | 500 |

**Result:** Developer input 219K → ~5K tokens (97.8% reduction).

---

## Enforcement Guarantees

**No public side-effect functions exist.** Tool calls, LLM calls, stage transitions all go through bus.

| Layer | Mechanism |
|-------|-----------|
| Architectural | ToolExecutor/LLMExecutor = only callers. No standalone execute_tool(). |
| Runtime | InstrumentedMCPClient detects unregistered MCP calls. |
| Audit | Chain-hash audit trail. Tamper = integrity failure. |

---

## Monitoring

- **Correlation IDs:** `m-001/s-analyst/tc-002` — grep traces full lifecycle
- **Real-time console:** Live timeline per stage (tokens, tools, budget %)
- **Mission report:** JSON with per-stage breakdown, tool details, latency, anomalies
- **Audit trail:** Immutable, chain-hash, every handler decision recorded

---

## Validation

| # | Test | Expected |
|---|------|----------|
| 1 | Developer input ≤ 30K on complex | Token log confirms |
| 2 | Snapshot blocked for analyst | Returns BLOCKED |
| 3 | Bypass detected if MCP called directly | security.bypass_detected event |
| 4 | Audit trail integrity | verify_integrity() = True |
| 5 | 3 complex missions complete | Reports generated |
| 6 | 3 simple missions no regression | Same quality |

**Rollback:** `TOKEN_GOVERNANCE.enabled = false` → pre-D-102 behavior.
