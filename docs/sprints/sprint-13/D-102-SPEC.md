# D-102: Token Governance — Context Window Fix

**Status:** Frozen (amended 2026-03-27)
**Date:** 2026-03-26
**Amendment:** D-102-AMENDMENT — Sprint 13 scope reconciliation (2026-03-27)

---

## Problem

Developer stage received 219,531 tokens. Root cause: Snapshot MCP tool returns 50-100K tokens (base64 screenshot + UI tree). Analyst and Architect both call Snapshot. Tool call responses bleed into downstream stage context via artifact assembly.

## Decision

### Sprint 13 — Delivered

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

### Sprint 14+ — Deferred

The following items were in original Sprint 13 scope but deferred. L1+L2 alone eliminates the 219K overflow (→ ~5K tokens). Deferred items provide defense-in-depth but are not required for the minimum viable fix.

**Lightweight tools.** Two new tools replace Snapshot for read-only roles:

| Tool | Returns | Target Tokens |
|------|---------|--------------|
| UIOverview | Window list + top-level elements (name, type, enabled). No screenshot, no coordinates. Max 30 elements. | ≤ 1,500 |
| WindowList | Window titles + dimensions only. | ≤ 300 |

**Role restriction update.** Analyst and Architect prompts updated to use UIOverview instead of Snapshot.

**Feature flag.** `CONTEXT_ISOLATION_ENABLED` defaults true. Set false to revert.

**Explicit L3/L4/L5 verification.** L3 (token logging), L4 (budget: >10K truncate, >50K block), L5 (role permissions, 19 denies) already work inline. Currently covered implicitly by backend test suite (225 tests pass at S13 close, 458 at current).

### Sprint 14A — Delivered (EventBus Architecture)

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

| # | Criterion | Sprint | Status |
|---|-----------|--------|--------|
| 1 | extract_stage_result strips tool history | 13 | Done (9 tests) |
| 2 | Tiered assembly ≤ tier sum | 13 | Done (6 tests) |
| 3 | UIOverview ≤ 1500 tokens | Deferred | Tool not built |
| 4 | WindowList ≤ 300 tokens | Deferred | Tool not built |
| 5 | Developer input ≤ 30K on complex mission | Deferred | Requires live pipeline |
| 6 | 3 complex missions complete | Deferred | Requires live pipeline |
| 7 | 3 simple missions no regression | Deferred | Requires live pipeline |
| 8 | Feature flag off reverts | Deferred | Flag not built |

## Rollback

L1/L2 are structural (frozen dataclass + tier constants). Rollback by reverting `extract_stage_result()` and `assembler.py` tier logic.

## Trade-off

| Gain | Cost |
|------|------|
| Overflow eliminated | Upstream tool responses lost at boundary |
| Simple implementation (2 functions) | No tool-level caps yet |
| Quick to implement (1 session) | Full observability deferred to Sprint 15 |
