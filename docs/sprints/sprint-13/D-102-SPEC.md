# D-102: Token Governance — Context Window Fix

**Status:** Frozen
**Date:** 2026-03-26
**Sprint 13 scope:** Minimum viable fix (L1 + L2 + tools + verify L3/L4/L5)
**Future scope (Sprint 14+):** EventBus full architecture, handler classes, audit trail, bypass detection

---

## Problem

Developer stage received 219,531 tokens. Root cause: Snapshot MCP tool returns 50-100K tokens (base64 screenshot + UI tree). Analyst and Architect both call Snapshot. Tool call responses bleed into downstream stage context via artifact assembly.

## Decision

### Sprint 13 Implements

**L1: Stage boundary isolation.** When a stage completes, only the final assistant message text is passed downstream. All tool call requests, responses, and intermediate messages are discarded.

```python
def extract_stage_result(stage_name: str, messages: list[dict]) -> StageResult:
    """Strip tool history. Return final artifact text only."""
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                return "\n".join(b["text"] for b in content if b.get("type") == "text")
            return content
    return ""
```

**L2: Tiered context assembly.** Replace flat 3000-char truncation with distance-based tiers.

| Tier | Distance | Max Chars |
|------|----------|-----------|
| A | Previous stage (N-1) | 5,000 |
| B | Two stages back (N-2) | 2,000 |
| C | Three+ stages back | 500 |

**Lightweight tools.** Two new tools replace Snapshot for read-only roles:

| Tool | Returns | Target Tokens |
|------|---------|--------------|
| UIOverview | Window list + top-level elements (name, type, enabled). No screenshot, no coordinates. Max 30 elements. | ≤ 1,500 |
| WindowList | Window titles + dimensions only. | ≤ 300 |

**Role restriction update.** Analyst and Architect prompts updated to use UIOverview instead of Snapshot.

**Verify existing inline code.** L3 (token logging), L4 (budget: >10K truncate, >50K block), L5 (role permissions, 19 denies) already work inline. Sprint 13 verifies they are not broken by L1/L2 changes.

**Feature flag.** `CONTEXT_ISOLATION_ENABLED` defaults true. Set false to revert.

### Sprint 14+ Implements (NOT Sprint 13)

- EventBus class with ordered handler dispatch
- 13 handler classes extracted from inline code
- 28 event types with schemas
- Correlation ID system
- InstrumentedMCPClient + BypassDetector
- ApprovalGate (operator pause/resume/abort)
- AuditTrail with chain-hash integrity
- AnomalyDetector, MetricsExporter
- Console real-time timeline

## Expected Impact

Developer input: 219,531 → approximately 5,000 tokens (97.8% reduction).

## Validation

| Test | Expected |
|------|----------|
| extract_stage_result strips tool history | Zero tool_call/tool_result in output |
| Tiered assembly ≤ tier sum | Assembled ≤ 8000 chars for 4 previous stages |
| UIOverview ≤ 1500 tokens | Measured |
| WindowList ≤ 300 tokens | Measured |
| Developer input ≤ 30K on complex mission | Token log |
| 3 complex missions complete | Mission reports |
| 3 simple missions no regression | Comparison |
| Feature flag off reverts | Old behavior restored |

## Rollback

`CONTEXT_ISOLATION_ENABLED = false` in config.

## Trade-off

| Gain | Cost |
|------|------|
| Overflow eliminated | Upstream tool responses lost at boundary |
| Simple implementation (2 functions + 2 tools) | No event-driven governance yet |
| Quick to implement (1-2 sessions) | Full observability deferred |
