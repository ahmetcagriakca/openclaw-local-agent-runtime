# D-102: Event-Driven Token Governance Architecture (Full Specification)

**Status:** Frozen
**Date:** 2026-03-26
**Author:** Claude Opus 4.6 (Architect)
**Sprint:** 13 — Phase 5.5, Task 13.0 (BLOCKER)
**Consolidates:** D-102 base spec + deep analysis + enforcement addendum

---

## 1. Problem

Developer stage received 219,531 tokens. Context window = 200K. Mission failed.

### 1.1 Token Anatomy (Observed 219K Case)

| Component | Tokens | % |
|-----------|--------|---|
| System prompt (Developer specialist) | 381 | 0.2% |
| Instruction (mission description) | 200 | 0.1% |
| Artifact: PO output + tool history | 2,500 | 1.1% |
| Artifact: Analyst output + **Snapshot responses** | **82,000** | **37.3%** |
| Artifact: Architect output + **Snapshot responses** | **78,000** | **35.5%** |
| Artifact: PM output | 3,500 | 1.6% |
| Overhead (framing, role tags) | 2,950 | 1.3% |
| Truncation savings (3000 char on artifact text) | -50,000 | — |
| **Net total** | **219,531** | — |

### 1.2 Snapshot Tool Response Anatomy

Single Snapshot MCP call returns:

| Part | Content | Tokens |
|------|---------|--------|
| Screenshot | Base64 PNG/JPEG of full screen | 30,000-50,000 |
| UI Element Tree | Every button, input, checkbox with coordinates, type, enabled, visible | 20,000-40,000 |
| Window List | Open windows, dimensions, z-order | 500-1,000 |
| Metadata | Timestamp, resolution, focused window | 100 |
| **Total** | | **50,000-91,000** |

### 1.3 Four Problem Layers

```
Layer 4: No budget enforcement — system sends whatever it has, no limit check
Layer 3: No observability — token counts not logged, not visible, not reported
Layer 2: Artifact context bleeding — tool call responses leak to downstream stages
Layer 1: Snapshot response explosion — single tool call = 50-100K tokens
```

---

## 2. Architecture Decision

The agent runtime adopts an event-driven architecture for all cross-cutting concerns. The EventBus is NOT an observer bolted on top — it IS the execution path. No side-effecting action (tool call, LLM call, stage transition) can happen outside the bus.

### 2.1 Scope

This is NOT a full system rewrite. The stage pipeline (PO → Analyst → Architect → PM → Developer) remains sequential. The event bus wraps the existing pipeline with governance capabilities.

### 2.2 Current State (Post Session Report)

| Layer | Status | Sprint 13 Action |
|-------|--------|-------------------|
| L3 (observability) | ✅ Inline in controller.py | Extract → TokenLogger handler |
| L4 (budget) | ✅ Inline (>10K truncate, >50K block) | Extract → BudgetEnforcer handler |
| L5 (permissions) | ✅ Inline (19 policy denies) | Extract → ToolPermissionHandler |
| L1 (stage isolation) | ⬜ Not done | New: StageResult + ContextAssembler |
| L2 (tiered assembly) | ⬜ Not done | New: Tiered A/B/C limits |
| EventBus | ⬜ Not done | New: Full event-driven refactor |
| Enforcement | ⬜ Not done | New: Bypass prevention + audit trail |
| Monitoring | ⬜ Not done | New: Correlation IDs + console timeline |

---

## 3. EventBus Core

### 3.1 Data Types

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Awaitable, Any
from collections import defaultdict

@dataclass(frozen=True)
class Event:
    """Immutable event. Cannot be modified after creation."""
    type: str                       # e.g. "tool_call.response"
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict = field(default_factory=dict)
    source: str = ""                # emitter identity

@dataclass
class HandlerResult:
    action: str                     # "continue" | "halt" | "truncate"
    handler_name: str = ""          # filled by bus
    reason: str = ""
    truncate_to: int | None = None
    metadata: dict = field(default_factory=dict)
```

### 3.2 EventBus Implementation

```python
class EventBus:
    """
    In-process, single-thread, ordered event dispatch.
    No network, no serialization, no external dependencies.
    """
    
    def __init__(self):
        self._handlers: dict[str, list[tuple[str, Callable]]] = defaultdict(list)
        self._history: list[Event] = []
        self._audit: AuditTrail | None = None
    
    def set_audit(self, audit: 'AuditTrail'):
        self._audit = audit
    
    def on(self, event_type: str, handler: Callable[[Event], Awaitable[HandlerResult]], name: str = ""):
        """Register handler. Order = registration order (deterministic)."""
        handler_name = name or handler.__qualname__
        self._handlers[event_type].append((handler_name, handler))
    
    async def emit(self, event: Event) -> list[HandlerResult]:
        """
        Dispatch event to all registered handlers in order.
        If any handler returns "halt", remaining handlers are skipped.
        All events recorded in history regardless of handler results.
        """
        self._history.append(event)
        results = []
        
        for handler_name, handler in self._handlers.get(event.type, []):
            try:
                result = await handler(event)
                if result:
                    result.handler_name = handler_name
                    results.append(result)
                    
                    if result.action == "halt":
                        break  # stop propagation
            except Exception as e:
                # Handler exceptions are caught, logged, recorded — never crash the bus
                error_result = HandlerResult(
                    action="continue",
                    handler_name=handler_name,
                    reason=f"Handler exception: {e}",
                )
                results.append(error_result)
        
        # Audit trail records every event + decisions
        if self._audit:
            self._audit.record(event, results)
        
        return results
    
    def history(self, event_type: str = None, since: datetime = None) -> list[Event]:
        """Query event history. Filterable by type and time."""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        if since:
            events = [e for e in events if e.ts >= since]
        return events
    
    def handler_count(self, event_type: str) -> int:
        return len(self._handlers.get(event_type, []))
```

### 3.3 Guarantees

- Handler execution order = registration order (deterministic)
- `halt` from any handler stops remaining handlers for that event
- All events persisted to history regardless of handler results
- No event silently dropped — even if all handlers fail, event is recorded
- EventBus itself never raises — handler exceptions caught, logged, recorded
- Events are frozen dataclasses — immutable after creation

---

## 4. Event Catalog (28 Event Types)

### 4.1 Pipeline Lifecycle

| Event | Emitted By | Payload Schema |
|-------|-----------|---------------|
| `mission.start` | AgentRunner | `{mission_id: str, complexity: str, stage_count: int}` |
| `mission.complete` | AgentRunner | `{mission_id: str, stage_results: list, total_tokens: int}` |
| `mission.abort` | BudgetEnforcer / AgentRunner | `{mission_id: str, reason: str, stage_reached: str, tokens_consumed: int}` |
| `stage.transition_request` | AgentRunner | `{stage_name: str, previous_stage_result: StageResult, context_assembled_by_bus: bool}` |
| `stage.start` | AgentRunner | `{stage_name: str, role: str, input_tokens: int, context_tier_breakdown: dict}` |
| `stage.complete` | AgentRunner | `{stage_name: str, artifact_text: str, artifact_tokens: int, total_consumed: int, tool_calls_made: int}` |
| `stage.error` | AgentRunner | `{stage_name: str, error: str, tokens_consumed_before_error: int}` |

### 4.2 LLM Call Lifecycle

| Event | Emitted By | Payload Schema |
|-------|-----------|---------------|
| `llm_call.request` | AgentRunner | `{stage: str, input_tokens: int, tools: list[str], correlation_id: str}` |
| `llm_call.cleared` | EventBus (auto) | `{stage: str, input_tokens: int, correlation_id: str}` |
| `llm_call.response` | LLMExecutor | `{stage: str, input_tokens: int, output_tokens: int, has_tool_calls: bool, correlation_id: str}` |

### 4.3 Tool Call Lifecycle

| Event | Emitted By | Payload Schema |
|-------|-----------|---------------|
| `tool_call.request` | AgentRunner | `{stage: str, role: str, tool_name: str, input_summary: str, correlation_id: str}` |
| `tool_call.permitted` | ToolPermissionHandler | `{stage: str, tool_name: str, correlation_id: str}` |
| `tool_call.cleared` | EventBus (auto) | `{stage: str, tool_name: str, input: dict, correlation_id: str}` |
| `tool_call.blocked` | ToolPermissionHandler | `{stage: str, role: str, tool_name: str, reason: str, correlation_id: str}` |
| `tool_call.response` | ToolExecutor | `{stage: str, tool_name: str, response_tokens: int, response_chars: int, latency_ms: int, correlation_id: str}` |
| `tool_call.truncated` | BudgetEnforcer | `{stage: str, tool_name: str, original_tokens: int, truncated_to: int, reason: str, correlation_id: str}` |

### 4.4 Context Assembly

| Event | Emitted By | Payload Schema |
|-------|-----------|---------------|
| `context.assembly_request` | AgentRunner | `{stage_name: str, previous_results: list[StageResult]}` |
| `context.assembled` | ContextAssembler | `{stage_name: str, total_tokens: int, tier_breakdown: dict}` |

### 4.5 Token Budget

| Event | Emitted By | Payload Schema |
|-------|-----------|---------------|
| `budget.within_limits` | BudgetEnforcer | `{check_type: str, value: int, limit: int, utilization_pct: float}` |
| `budget.warning` | BudgetEnforcer | `{check_type: str, value: int, soft_limit: int, hard_limit: int}` |
| `budget.approval_required` | BudgetEnforcer | `{check_type: str, value: int, limit: int, stage: str, breakdown: dict, options: list[str]}` |
| `budget.approval_granted` | ApprovalGate | `{operator_choice: str, original_value: int, limit: int, truncate: bool}` |
| `budget.approval_denied` | ApprovalGate | `{operator_choice: str, reason: str}` |
| `budget.hard_abort` | BudgetEnforcer | `{mission_id: str, total_tokens: int, limit: int}` |

### 4.6 Reporting + Security

| Event | Emitted By | Payload Schema |
|-------|-----------|---------------|
| `report.stage_summary` | ReportCollector | `{stage_name: str, tokens: int, tools: int, artifact_size: int}` |
| `report.mission_summary` | ReportCollector | `{mission_id: str, total_tokens: int, per_stage: list, budget_utilization: dict}` |
| `report.anomaly` | AnomalyDetector | `{stage: str, metric: str, value: float, threshold: float, message: str}` |
| `security.bypass_detected` | BypassDetector | `{tool: str, correlation_id: str, detail: str}` |
| `handler.disabled` | EventBus | `{handler_name: str, disabled_by: str, reason: str}` |

---

## 5. Handler Specifications (Full Code)

### 5.1 AuditTrail (Handler #1)

```python
import hashlib
import json

class AuditTrail:
    """
    Immutable append-only audit log with chain-hash integrity.
    First handler: records everything, even if later handlers halt.
    """
    
    def __init__(self, bus: EventBus, path: str):
        self._path = path
        self._sequence = 0
        self._last_checksum = "genesis"
        bus.set_audit(self)  # special: bus calls record() directly
    
    def record(self, event: Event, handler_results: list[HandlerResult]):
        self._sequence += 1
        
        entry = {
            "seq": self._sequence,
            "ts": event.ts.isoformat(),
            "event_type": event.type,
            "correlation_id": event.data.get("correlation_id", ""),
            "source": event.source,
            "handler_decisions": [
                {
                    "handler": r.handler_name,
                    "action": r.action,
                    "reason": r.reason,
                }
                for r in handler_results
            ],
            "checksum": self._compute_checksum(event),
        }
        
        with open(self._path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def _compute_checksum(self, event: Event) -> str:
        content = f"{self._sequence}:{event.type}:{event.ts.isoformat()}:{self._last_checksum}"
        self._last_checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self._last_checksum
    
    def verify_integrity(self) -> tuple[bool, int, str]:
        """Verify chain: no entries modified or deleted."""
        prev_hash = "genesis"
        count = 0
        
        for line in open(self._path):
            entry = json.loads(line)
            count += 1
            expected_content = f"{entry['seq']}:{entry['event_type']}:{entry['ts']}:{prev_hash}"
            expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()[:16]
            
            if entry["checksum"] != expected_hash:
                return False, count, f"Integrity failure at seq {entry['seq']}"
            prev_hash = entry["checksum"]
        
        return True, count, f"Verified: {count} entries, chain intact"
```

### 5.2 TokenLogger (Handler #2)

```python
class TokenLogger:
    """Operational log. Records every token-relevant event. Never halts."""
    
    def __init__(self, bus: EventBus, log_path: str, console: bool = True):
        self._log_path = log_path
        self._console = console
        
        bus.on("tool_call.request", self._on_tool_request, "TokenLogger")
        bus.on("tool_call.response", self._on_tool_response, "TokenLogger")
        bus.on("tool_call.blocked", self._on_tool_blocked, "TokenLogger")
        bus.on("tool_call.truncated", self._on_tool_truncated, "TokenLogger")
        bus.on("llm_call.response", self._on_llm_response, "TokenLogger")
        bus.on("stage.start", self._on_stage_start, "TokenLogger")
        bus.on("stage.complete", self._on_stage_complete, "TokenLogger")
        bus.on("budget.warning", self._on_budget_event, "TokenLogger")
        bus.on("budget.approval_required", self._on_budget_event, "TokenLogger")
        bus.on("budget.hard_abort", self._on_budget_event, "TokenLogger")
    
    async def _on_tool_response(self, event: Event) -> HandlerResult:
        self._write({
            "event": "tool_call.response",
            "cid": event.data.get("correlation_id"),
            "stage": event.data["stage"],
            "tool": event.data["tool_name"],
            "tokens": event.data["response_tokens"],
            "latency_ms": event.data.get("latency_ms", 0),
        })
        if self._console:
            lat = event.data.get("latency_ms", 0)
            print(f"   🔧 {event.data['tool_name']} → {event.data['response_tokens']} tok [{lat}ms] ✅")
        return HandlerResult(action="continue")
    
    async def _on_tool_blocked(self, event: Event) -> HandlerResult:
        self._write({"event": "tool_call.blocked", "stage": event.data["stage"],
                      "tool": event.data["tool_name"], "reason": event.data["reason"]})
        if self._console:
            print(f"   🚫 {event.data['tool_name']} BLOCKED: {event.data['reason']}")
        return HandlerResult(action="continue")
    
    async def _on_tool_truncated(self, event: Event) -> HandlerResult:
        self._write({"event": "tool_call.truncated", "stage": event.data["stage"],
                      "tool": event.data["tool_name"],
                      "original": event.data["original_tokens"],
                      "truncated_to": event.data["truncated_to"]})
        if self._console:
            print(f"   ✂️  {event.data['tool_name']} truncated: {event.data['original_tokens']} → {event.data['truncated_to']} tok")
        return HandlerResult(action="continue")
    
    async def _on_stage_start(self, event: Event) -> HandlerResult:
        breakdown = event.data.get("context_tier_breakdown", {})
        self._write({"event": "stage.start", "stage": event.data["stage_name"],
                      "input_tokens": event.data["input_tokens"], "breakdown": breakdown})
        if self._console:
            print(f"\n{'─'*60}")
            print(f" ▶ STAGE {event.data['stage_name']}")
            print(f"   📥 Input: {event.data['input_tokens']} tok")
            if breakdown:
                for tier, info in breakdown.items():
                    if info:
                        print(f"      {tier}: {info}")
        return HandlerResult(action="continue")
    
    async def _on_stage_complete(self, event: Event) -> HandlerResult:
        self._write({"event": "stage.complete", "stage": event.data["stage_name"],
                      "artifact_tokens": event.data["artifact_tokens"],
                      "total_consumed": event.data["total_consumed"],
                      "tool_calls": event.data["tool_calls_made"]})
        if self._console:
            print(f"   📤 Complete: artifact {event.data['artifact_tokens']} tok | "
                  f"consumed {event.data['total_consumed']} tok | "
                  f"tools: {event.data['tool_calls_made']}")
        return HandlerResult(action="continue")
    
    async def _on_tool_request(self, event: Event) -> HandlerResult:
        self._write({"event": "tool_call.request", "cid": event.data.get("correlation_id"),
                      "stage": event.data["stage"], "tool": event.data["tool_name"]})
        return HandlerResult(action="continue")
    
    async def _on_llm_response(self, event: Event) -> HandlerResult:
        self._write({"event": "llm_call.response", "stage": event.data["stage"],
                      "input_tokens": event.data["input_tokens"],
                      "output_tokens": event.data["output_tokens"]})
        return HandlerResult(action="continue")
    
    async def _on_budget_event(self, event: Event) -> HandlerResult:
        self._write({"event": event.type, **event.data})
        return HandlerResult(action="continue")
    
    def _write(self, entry: dict):
        entry["ts"] = datetime.now(timezone.utc).isoformat()
        with open(self._log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
```

### 5.3 BypassDetector (Handler #3)

```python
class InstrumentedMCPClient:
    """Wraps real MCP client. Every call notifies detector."""
    
    def __init__(self, real_client, detector: 'BypassDetector'):
        self._real = real_client
        self._detector = detector
    
    async def call(self, tool_name: str, input: dict, correlation_id: str = None):
        cid = correlation_id or f"unregistered-{uuid4().hex[:8]}"
        self._detector.on_raw_call(tool_name, cid)
        return await self._real.call(tool_name, input)


class BypassDetector:
    """Audits MCP calls vs bus events. Detects unauthorized direct calls."""
    
    def __init__(self, bus: EventBus):
        self._bus = bus
        self._registered_cids: set[str] = set()
        bus.on("tool_call.request", self._record, "BypassDetector")
    
    async def _record(self, event: Event) -> HandlerResult:
        cid = event.data.get("correlation_id", "")
        if cid:
            self._registered_cids.add(cid)
        return HandlerResult(action="continue")
    
    def on_raw_call(self, tool_name: str, correlation_id: str):
        """Called by InstrumentedMCPClient on EVERY raw MCP call."""
        if correlation_id not in self._registered_cids:
            import asyncio
            asyncio.create_task(self._bus.emit(Event(
                type="security.bypass_detected",
                data={"tool": tool_name, "correlation_id": correlation_id,
                      "detail": "MCP call without matching bus event"},
                source="BypassDetector",
            )))
```

### 5.4 ToolPermissionHandler (Handler #4)

```python
ROLE_TOOL_PERMISSIONS = {
    "product_owner":  {"FileSystem.read", "WindowList"},
    "analyst":        {"FileSystem.read", "UIOverview", "WindowList"},
    "architect":      {"FileSystem.read", "UIOverview", "WindowList"},
    "developer":      {"FileSystem.read", "FileSystem.write", "UIOverview",
                       "WindowList", "Snapshot", "Terminal"},
    "pm":             {"FileSystem.read"},
}

class ToolPermissionHandler:
    """Enforces role-based tool access. Blocks before execution."""
    
    def __init__(self, bus: EventBus):
        self._bus = bus
        bus.on("tool_call.request", self._check, "ToolPermissionHandler")
    
    async def _check(self, event: Event) -> HandlerResult:
        role = event.data["role"]
        tool = event.data["tool_name"]
        allowed = ROLE_TOOL_PERMISSIONS.get(role, set())
        
        if tool in allowed:
            await self._bus.emit(Event(
                type="tool_call.permitted",
                data={"stage": event.data["stage"], "tool_name": tool,
                      "correlation_id": event.data.get("correlation_id")},
                source="ToolPermissionHandler",
            ))
            return HandlerResult(action="continue")
        
        await self._bus.emit(Event(
            type="tool_call.blocked",
            data={"stage": event.data["stage"], "role": role, "tool_name": tool,
                  "reason": f"{tool} not permitted for {role}. Allowed: {sorted(allowed)}",
                  "correlation_id": event.data.get("correlation_id")},
            source="ToolPermissionHandler",
        ))
        return HandlerResult(action="halt",
                             reason=f"[BLOCKED] {tool} not available for {role}")
```

### 5.5 BudgetEnforcer (Handler #5)

```python
from dataclasses import dataclass

@dataclass
class BudgetConfig:
    tool_response_soft: int = 10_000
    tool_response_hard: int = 50_000
    stage_input_soft: int = 50_000
    stage_input_hard: int = 80_000
    stage_cumulative_soft: int = 100_000
    stage_cumulative_hard: int = 150_000
    mission_total_hard: int = 300_000


class BudgetEnforcer:
    """4-tier token budget enforcement. May truncate, warn, pause, or abort."""
    
    def __init__(self, bus: EventBus, config: BudgetConfig):
        self._bus = bus
        self._config = config
        self._mission_total = 0
        self._stage_cumulatives: dict[str, int] = {}
        
        bus.on("tool_call.response", self._check_tool_response, "BudgetEnforcer")
        bus.on("stage.start", self._check_stage_input, "BudgetEnforcer")
        bus.on("stage.complete", self._update_mission_total, "BudgetEnforcer")
    
    async def _check_tool_response(self, event: Event) -> HandlerResult:
        tokens = event.data["response_tokens"]
        tool = event.data["tool_name"]
        stage = event.data["stage"]
        
        # Tier 1: Per tool response
        if tokens <= self._config.tool_response_soft:
            await self._bus.emit(Event(type="budget.within_limits",
                data={"check_type": "tool_response", "value": tokens,
                      "limit": self._config.tool_response_soft,
                      "utilization_pct": tokens / self._config.tool_response_soft * 100}))
            return HandlerResult(action="continue")
        
        if tokens <= self._config.tool_response_hard:
            await self._bus.emit(Event(type="tool_call.truncated",
                data={"stage": stage, "tool_name": tool, "original_tokens": tokens,
                      "truncated_to": self._config.tool_response_soft,
                      "reason": f"Exceeded soft limit {self._config.tool_response_soft}",
                      "correlation_id": event.data.get("correlation_id")}))
            return HandlerResult(action="truncate",
                                 truncate_to=self._config.tool_response_soft,
                                 reason=f"{tool}: {tokens} → {self._config.tool_response_soft}")
        
        # Hard limit exceeded — block entirely
        return HandlerResult(action="halt",
                             reason=f"{tool} response {tokens} tok exceeds hard limit {self._config.tool_response_hard}")
    
    async def _check_stage_input(self, event: Event) -> HandlerResult:
        tokens = event.data["input_tokens"]
        stage = event.data["stage_name"]
        
        if tokens <= self._config.stage_input_soft:
            return HandlerResult(action="continue")
        
        if tokens <= self._config.stage_input_hard:
            await self._bus.emit(Event(type="budget.warning",
                data={"check_type": "stage_input", "value": tokens,
                      "soft_limit": self._config.stage_input_soft,
                      "hard_limit": self._config.stage_input_hard}))
            return HandlerResult(action="continue")
        
        # Hard limit — pause for approval
        await self._bus.emit(Event(type="budget.approval_required",
            data={"check_type": "stage_input", "value": tokens,
                  "limit": self._config.stage_input_hard, "stage": stage,
                  "breakdown": event.data.get("context_tier_breakdown", {}),
                  "options": ["approve", "abort", "truncate"]}))
        return HandlerResult(action="halt", reason="Operator approval required")
    
    async def _update_mission_total(self, event: Event) -> HandlerResult:
        self._mission_total += event.data["total_consumed"]
        
        if self._mission_total > self._config.mission_total_hard:
            await self._bus.emit(Event(type="budget.hard_abort",
                data={"mission_id": event.data.get("mission_id", ""),
                      "total_tokens": self._mission_total,
                      "limit": self._config.mission_total_hard}))
            return HandlerResult(action="halt", reason="Mission total exceeded")
        
        return HandlerResult(action="continue")
```

### 5.6 ApprovalGate (Handler #6)

```python
class ApprovalGate:
    """Pauses pipeline for operator decision when budget exceeded."""
    
    def __init__(self, bus: EventBus, operator_interface):
        self._operator = operator_interface
        self._bus = bus
        bus.on("budget.approval_required", self._wait, "ApprovalGate")
    
    async def _wait(self, event: Event) -> HandlerResult:
        prompt = self._build_prompt(event)
        decision = await self._operator.prompt(prompt, event.data["options"])
        
        if decision == "approve":
            await self._bus.emit(Event(type="budget.approval_granted",
                data={"operator_choice": "approve", "original_value": event.data["value"],
                      "limit": event.data["limit"], "truncate": False}))
            return HandlerResult(action="continue")
        
        elif decision == "abort":
            await self._bus.emit(Event(type="budget.approval_denied",
                data={"operator_choice": "abort", "reason": "Operator chose to abort"}))
            await self._bus.emit(Event(type="mission.abort",
                data={"reason": "operator_abort", "stage_reached": event.data["stage"]}))
            return HandlerResult(action="halt", reason="Operator aborted")
        
        else:  # truncate
            await self._bus.emit(Event(type="budget.approval_granted",
                data={"operator_choice": "truncate", "original_value": event.data["value"],
                      "limit": event.data["limit"], "truncate": True}))
            return HandlerResult(action="continue", metadata={"truncate": True})
    
    def _build_prompt(self, event: Event) -> str:
        d = event.data
        breakdown = d.get("breakdown", {})
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║  ⚠ BUDGET GATE — Approval Required                          ║",
            "╠══════════════════════════════════════════════════════════════╣",
            f"║  Stage:    {d['stage']:<50}║",
            f"║  Check:    {d['check_type']} = {d['value']:,} tokens{' '*(37-len(str(d['value'])))}║",
            f"║  Limit:    {d['limit']:,} tokens (hard){' '*(38-len(str(d['limit'])))}║",
            f"║  Overage:  +{d['value']-d['limit']:,} tokens ({(d['value']-d['limit'])/d['limit']*100:.1f}%){' '*20}║",
            "║                                                              ║",
        ]
        if breakdown:
            lines.append("║  Breakdown:                                                  ║")
            for k, v in breakdown.items():
                if v:
                    lines.append(f"║    {k}: {v!s:<50}║")
        lines.extend([
            "║                                                              ║",
            "║  [1] APPROVE  — proceed                                     ║",
            "║  [2] ABORT    — stop mission, generate report               ║",
            "║  [3] TRUNCATE — re-assemble at 50% limits, retry            ║",
            "╚══════════════════════════════════════════════════════════════╝",
        ])
        return "\n".join(lines)
```

### 5.7 ToolExecutor (Handler #7)

```python
class ToolExecutor:
    """
    The ONLY way to execute an MCP tool.
    Listens on tool_call.cleared (NOT request).
    No public execute_tool() function exists anywhere.
    """
    
    def __init__(self, bus: EventBus, mcp_client: InstrumentedMCPClient):
        self._mcp = mcp_client
        self._bus = bus
        bus.on("tool_call.cleared", self._execute, "ToolExecutor")
    
    async def _execute(self, event: Event) -> HandlerResult:
        import time
        start = time.monotonic()
        
        response = await self._mcp.call(
            event.data["tool_name"],
            event.data["input"],
            correlation_id=event.data.get("correlation_id"),
        )
        
        latency_ms = int((time.monotonic() - start) * 1000)
        response_tokens = estimate_tokens(response)
        
        await self._bus.emit(Event(
            type="tool_call.response",
            data={
                "stage": event.data["stage"],
                "tool_name": event.data["tool_name"],
                "response_tokens": response_tokens,
                "response_chars": len(str(response)),
                "response_content": response,
                "latency_ms": latency_ms,
                "correlation_id": event.data.get("correlation_id"),
            },
            source="ToolExecutor",
        ))
        
        return HandlerResult(action="continue", metadata={"response": response})
```

### 5.8 LLMExecutor (Handler #8)

```python
class LLMExecutor:
    """The ONLY way to call the LLM. Listens on llm_call.cleared."""
    
    def __init__(self, bus: EventBus, llm_client):
        self._llm = llm_client
        self._bus = bus
        bus.on("llm_call.cleared", self._execute, "LLMExecutor")
    
    async def _execute(self, event: Event) -> HandlerResult:
        response = await self._llm.create(
            messages=event.data["messages"],
            tools=event.data.get("tools", []),
        )
        
        output_tokens = count_response_tokens(response)
        
        await self._bus.emit(Event(
            type="llm_call.response",
            data={
                "stage": event.data["stage"],
                "input_tokens": event.data["input_tokens"],
                "output_tokens": output_tokens,
                "has_tool_calls": has_tool_calls(response),
                "correlation_id": event.data.get("correlation_id"),
            },
            source="LLMExecutor",
        ))
        
        return HandlerResult(action="continue", metadata={"response": response})
```

### 5.9 ReportCollector (Handler #11)

```python
class ReportCollector:
    """Aggregates metrics. Generates mission token report at end."""
    
    def __init__(self, bus: EventBus, report_path_template: str):
        self._template = report_path_template
        self._stages: list[dict] = []
        self._tool_details: list[dict] = []
        self._approvals: list[dict] = []
        self._truncations: int = 0
        self._anomalies: list[dict] = []
        
        bus.on("stage.complete", self._on_stage, "ReportCollector")
        bus.on("tool_call.response", self._on_tool, "ReportCollector")
        bus.on("tool_call.truncated", self._on_truncation, "ReportCollector")
        bus.on("budget.approval_granted", self._on_approval, "ReportCollector")
        bus.on("report.anomaly", self._on_anomaly, "ReportCollector")
        bus.on("mission.complete", self._generate, "ReportCollector")
        bus.on("mission.abort", self._generate, "ReportCollector")
    
    async def _on_stage(self, event: Event) -> HandlerResult:
        self._stages.append({
            "name": event.data["stage_name"],
            "tokens_consumed": event.data["total_consumed"],
            "artifact_tokens": event.data["artifact_tokens"],
            "tool_calls": event.data["tool_calls_made"],
        })
        return HandlerResult(action="continue")
    
    async def _on_tool(self, event: Event) -> HandlerResult:
        self._tool_details.append({
            "stage": event.data["stage"],
            "tool": event.data["tool_name"],
            "tokens": event.data["response_tokens"],
            "latency_ms": event.data.get("latency_ms", 0),
        })
        return HandlerResult(action="continue")
    
    async def _on_truncation(self, event: Event) -> HandlerResult:
        self._truncations += 1
        return HandlerResult(action="continue")
    
    async def _on_approval(self, event: Event) -> HandlerResult:
        self._approvals.append(event.data)
        return HandlerResult(action="continue")
    
    async def _on_anomaly(self, event: Event) -> HandlerResult:
        self._anomalies.append(event.data)
        return HandlerResult(action="continue")
    
    async def _generate(self, event: Event) -> HandlerResult:
        mission_id = event.data.get("mission_id", "unknown")
        total = sum(s["tokens_consumed"] for s in self._stages)
        
        report = {
            "mission_id": mission_id,
            "status": "completed" if event.type == "mission.complete" else "aborted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tokens": total,
            "budget_utilization": {
                "mission_total": {"used": total, "limit": 300_000,
                                  "pct": round(total / 300_000 * 100, 1)},
            },
            "stages": [
                {**s, "pct_of_total": round(s["tokens_consumed"] / max(1, total) * 100, 1),
                 "tool_details": [t for t in self._tool_details if t["stage"] == s["name"]]}
                for s in self._stages
            ],
            "approval_gates_triggered": len(self._approvals),
            "approval_details": self._approvals,
            "truncations": self._truncations,
            "anomalies": self._anomalies,
        }
        
        path = self._template.format(mission_id=mission_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        
        return HandlerResult(action="continue")
```

### 5.10 AnomalyDetector (Handler #12)

```python
class AnomalyDetector:
    """Pattern detection. Alerts but never halts."""
    
    RULES = {
        "stage_pct_threshold": 0.50,
        "tool_multiplier_threshold": 5,
        "max_truncations_per_stage": 3,
        "max_approvals_per_mission": 3,
    }
    
    def __init__(self, bus: EventBus, rules: dict = None):
        self._bus = bus
        self._rules = rules or self.RULES
        self._tool_averages: dict[str, list[int]] = defaultdict(list)
        self._stage_truncations: dict[str, int] = defaultdict(int)
        self._mission_cumulative = 0
        self._approval_count = 0
        
        bus.on("stage.complete", self._check_stage, "AnomalyDetector")
        bus.on("tool_call.response", self._check_tool, "AnomalyDetector")
        bus.on("tool_call.truncated", self._check_truncations, "AnomalyDetector")
        bus.on("budget.approval_granted", self._check_approvals, "AnomalyDetector")
    
    async def _check_stage(self, event: Event) -> HandlerResult:
        consumed = event.data["total_consumed"]
        self._mission_cumulative += consumed
        
        if self._mission_cumulative > 0:
            pct = consumed / self._mission_cumulative
            if pct > self._rules["stage_pct_threshold"]:
                await self._bus.emit(Event(type="report.anomaly",
                    data={"stage": event.data["stage_name"], "metric": "stage_pct",
                          "value": pct, "threshold": self._rules["stage_pct_threshold"],
                          "message": f"{event.data['stage_name']} consumed {pct:.0%} of mission tokens"}))
        return HandlerResult(action="continue")
    
    async def _check_tool(self, event: Event) -> HandlerResult:
        tool = event.data["tool_name"]
        tokens = event.data["response_tokens"]
        self._tool_averages[tool].append(tokens)
        
        if len(self._tool_averages[tool]) >= 3:
            avg = sum(self._tool_averages[tool]) / len(self._tool_averages[tool])
            if tokens > avg * self._rules["tool_multiplier_threshold"]:
                await self._bus.emit(Event(type="report.anomaly",
                    data={"stage": event.data["stage"], "metric": "tool_spike",
                          "value": tokens, "threshold": avg * self._rules["tool_multiplier_threshold"],
                          "message": f"{tool} returned {tokens} tok ({tokens/avg:.1f}× average)"}))
        return HandlerResult(action="continue")
    
    async def _check_truncations(self, event: Event) -> HandlerResult:
        stage = event.data["stage"]
        self._stage_truncations[stage] += 1
        if self._stage_truncations[stage] >= self._rules["max_truncations_per_stage"]:
            await self._bus.emit(Event(type="report.anomaly",
                data={"stage": stage, "metric": "truncation_count",
                      "value": self._stage_truncations[stage],
                      "threshold": self._rules["max_truncations_per_stage"],
                      "message": f"{stage}: {self._stage_truncations[stage]} truncations"}))
        return HandlerResult(action="continue")
    
    async def _check_approvals(self, event: Event) -> HandlerResult:
        self._approval_count += 1
        if self._approval_count >= self._rules["max_approvals_per_mission"]:
            await self._bus.emit(Event(type="report.anomaly",
                data={"stage": "", "metric": "approval_count",
                      "value": self._approval_count,
                      "threshold": self._rules["max_approvals_per_mission"],
                      "message": f"Mission triggered {self._approval_count} approval gates"}))
        return HandlerResult(action="continue")
```

---

## 6. Context Assembly (L1 + L2)

### 6.1 StageResult Extraction (L1)

```python
@dataclass
class StageResult:
    """Immutable output of a completed stage. Tool history is dead here."""
    stage_name: str
    artifact_text: str          # final assistant message text ONLY
    artifact_tokens: int
    total_tokens_consumed: int  # metric — content NOT passed
    tool_calls_made: int        # metric — responses NOT passed


def extract_stage_result(stage_name: str, messages: list[dict]) -> StageResult:
    """
    Strip tool history. Extract only final artifact.
    Called at stage boundary — tool responses die here.
    """
    artifact_text = ""
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [b["text"] for b in content if b.get("type") == "text"]
                artifact_text = "\n".join(text_parts)
            elif isinstance(content, str):
                artifact_text = content
            break
    
    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in messages)
    tool_calls = sum(1 for msg in messages
                     if msg.get("role") == "assistant"
                     and isinstance(msg.get("content"), list)
                     and any(b.get("type") == "tool_use" for b in msg["content"]))
    
    return StageResult(
        stage_name=stage_name,
        artifact_text=artifact_text,
        artifact_tokens=estimate_tokens(artifact_text),
        total_tokens_consumed=total_tokens,
        tool_calls_made=tool_calls,
    )
```

### 6.2 Tiered ContextAssembler (L2)

```python
TIER_CONFIG = {
    "A": {"max_chars": 5000, "label": "full"},
    "B": {"max_chars": 2000, "label": "summarized"},
    "C": {"max_chars": 500,  "label": "one-liner"},
}

class ContextAssembler:
    """Tiered context assembly. Registered as bus handler."""
    
    def __init__(self, bus: EventBus, tier_config: dict = None):
        self._tiers = tier_config or TIER_CONFIG
        self._bus = bus
        bus.on("context.assembly_request", self._assemble, "ContextAssembler")
    
    async def _assemble(self, event: Event) -> HandlerResult:
        stage_name = event.data["stage_name"]
        results: list[StageResult] = event.data["previous_results"]
        
        parts = []
        breakdown = {}
        
        for i, result in enumerate(results):
            distance = len(results) - i  # how far back
            
            if distance == 1:
                tier = "A"
            elif distance == 2:
                tier = "B"
            else:
                tier = "C"
            
            limit = self._tiers[tier]["max_chars"]
            text = self._truncate(result.artifact_text, limit)
            
            parts.append(f"## {result.stage_name} Output (Tier {tier})\n{text}")
            breakdown[f"tier_{tier}_{result.stage_name}"] = {
                "stage": result.stage_name,
                "tier": tier,
                "original_chars": len(result.artifact_text),
                "truncated_chars": len(text),
                "tokens": estimate_tokens(text),
            }
        
        assembled = "\n\n".join(parts)
        
        await self._bus.emit(Event(
            type="context.assembled",
            data={"stage_name": stage_name,
                  "total_tokens": estimate_tokens(assembled),
                  "tier_breakdown": breakdown},
            source="ContextAssembler",
        ))
        
        return HandlerResult(action="continue", metadata={"context": assembled})
    
    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + f"\n[...truncated at {limit} chars, original {len(text)}]"
```

---

## 7. Lightweight Tools

### 7.1 UIOverview

```python
async def ui_overview_tool() -> dict:
    """
    Top-level UI awareness. No screenshots, no coordinates.
    Target: ≤ 1,500 tokens.
    """
    windows = enumerate_windows()
    focused = get_focused_window()
    
    elements = []
    if focused:
        for elem in get_top_level_elements(focused.handle, max_depth=2):
            elements.append({
                "type": elem.control_type,
                "name": elem.name[:50],
                "enabled": elem.is_enabled,
            })
            if len(elements) >= 30:
                break
    
    return {
        "windows": [{"title": w.title, "rect": w.rect, "focused": w == focused} for w in windows],
        "focused_window_elements": elements,
        "element_count_total": get_total_element_count(focused) if focused else 0,
        "showing_top": len(elements),
    }
```

### 7.2 WindowList

```python
async def window_list_tool() -> dict:
    """Lightest UI tool. Just window titles. Target: ≤ 300 tokens."""
    windows = enumerate_windows()
    return {
        "windows": [{"title": w.title, "rect": w.rect, "focused": w.is_focused} for w in windows]
    }
```

---

## 8. Enforcement Guarantees

### 8.1 No Public Side-Effect Functions

| Action | How It Happens | Direct Function? |
|--------|---------------|-----------------|
| Call MCP tool | bus.emit("tool_call.request") → chain → ToolExecutor | ❌ |
| Call LLM | bus.emit("llm_call.request") → chain → LLMExecutor | ❌ |
| Start stage | bus.emit("stage.transition_request") → chain → StageRunner | ❌ |
| Assemble context | bus.emit("context.assembly_request") → ContextAssembler | ❌ |

### 8.2 Three Enforcement Layers

| Layer | Mechanism | Detects |
|-------|-----------|---------|
| Architectural | No public execute function exists | Prevents direct calls |
| Runtime | InstrumentedMCPClient + BypassDetector | Detects unregistered MCP calls |
| Audit | Chain-hash AuditTrail | Detects tampered/deleted records |

### 8.3 StageTransitionHandler

```python
class StageTransitionHandler:
    """Validates: previous stage = StageResult, context assembled via bus."""
    
    def __init__(self, bus: EventBus):
        bus.on("stage.transition_request", self._check, "StageTransitionHandler")
    
    async def _check(self, event: Event) -> HandlerResult:
        prev = event.data.get("previous_stage_result")
        if prev and not isinstance(prev, StageResult):
            return HandlerResult(action="halt",
                reason="Previous stage output is not StageResult — raw messages leak detected")
        
        if not event.data.get("context_assembled_by_bus"):
            return HandlerResult(action="halt",
                reason="Context not assembled through bus — bypass detected")
        
        return HandlerResult(action="continue")
```

---

## 9. Monitoring

### 9.1 Correlation ID Format

```
m-20260326-001/s-analyst/tc-001     # mission / stage / tool-call-sequence
m-20260326-001/s-analyst/llm-002    # mission / stage / llm-call-sequence
```

### 9.2 Console Timeline (Real-Time)

```
══════════════════════════════════════════════════════════════
 MISSION: m-20260326-001 | Create login page | RUNNING
══════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────
 ▶ STAGE product_owner
   📥 Input: 581 tok
   📤 Complete: artifact 1,200 tok | consumed 2,800 tok | tools: 0
   💰 Budget: 2,800 / 300,000 (0.9%)

────────────────────────────────────────────────────────
 ▶ STAGE analyst
   📥 Input: 1,840 tok
   🔧 UIOverview → 1,200 tok [225ms] ✅
   🔧 FileSystem.read → 2,100 tok [180ms] ✅
   📤 Complete: artifact 2,400 tok | consumed 5,440 tok | tools: 2
   💰 Budget: 8,240 / 300,000 (2.7%)

────────────────────────────────────────────────────────
 ▶ STAGE developer
   📥 Input: 4,881 tok
   🔧 FileSystem.read → 3,200 tok [150ms] ✅
   🔧 Snapshot → 62,000 tok [1,800ms]
   ⚠️  BUDGET GATE: tool_response 62,000 > 50,000
   ⏸️  WAITING FOR OPERATOR [1] Approve [2] Abort [3] Truncate
   ✅ OPERATOR: approved (8s)
   🔧 Terminal → 5,100 tok [2,400ms] ✅
   📤 Complete: artifact 4,500 tok | consumed 56,200 tok | tools: 3
   💰 Budget: 73,570 / 300,000 (24.5%)

══════════════════════════════════════════════════════════════
 MISSION COMPLETE | Total: 73,570 tok | 5 stages | 6 tools
══════════════════════════════════════════════════════════════
```

### 9.3 Audit Trail Log Format

```jsonl
{"seq":1,"ts":"2026-03-26T14:30:00Z","event_type":"mission.start","correlation_id":"m-001","source":"AgentRunner","handler_decisions":[{"handler":"TokenLogger","action":"continue"},{"handler":"ReportCollector","action":"continue"}],"checksum":"a3f2b1c9e7d4f601"}
{"seq":2,"ts":"2026-03-26T14:30:00Z","event_type":"stage.start","correlation_id":"m-001/s-product_owner","source":"AgentRunner","handler_decisions":[{"handler":"TokenLogger","action":"continue"}],"checksum":"b7e4c2d8f1a3e502"}
```

**Integrity check:** `python -m app.audit verify logs/audit-trail.jsonl`

---

## 10. Configuration

```python
TOKEN_GOVERNANCE = {
    "enabled": True,
    "budget": {
        "tool_response_soft": 10_000,
        "tool_response_hard": 50_000,
        "stage_input_soft": 50_000,
        "stage_input_hard": 80_000,
        "stage_cumulative_soft": 100_000,
        "stage_cumulative_hard": 150_000,
        "mission_total_hard": 300_000,
    },
    "tier_limits": {"A": 5000, "B": 2000, "C": 500},
    "role_permissions": {
        "product_owner": ["FileSystem.read", "WindowList"],
        "analyst": ["FileSystem.read", "UIOverview", "WindowList"],
        "architect": ["FileSystem.read", "UIOverview", "WindowList"],
        "developer": ["FileSystem.read", "FileSystem.write", "Snapshot", "UIOverview", "WindowList", "Terminal"],
        "pm": ["FileSystem.read"],
    },
    "observability": {
        "log_path": "logs/token-usage.jsonl",
        "audit_path": "logs/audit-trail.jsonl",
        "report_path": "missions/{mission_id}/token-report.json",
        "console_output": True,
    },
    "anomaly_rules": {
        "stage_pct_threshold": 0.50,
        "tool_multiplier_threshold": 5,
        "max_truncations_per_stage": 3,
        "max_approvals_per_mission": 3,
    },
}
```

---

## 11. Expected Token Flow (Post-Implementation)

| Stage | Input | Tools | Tool Tokens | Stage Total | Cumulative |
|-------|-------|-------|------------|------------|-----------|
| PO | 581 | 0 | 0 | 2,800 | 2,800 |
| Analyst | 1,840 | 2 | 3,300 | 5,440 | 8,240 |
| Architect | 3,480 | 1 | 1,150 | 4,930 | 13,170 |
| PM | 5,100 | 0 | 0 | 4,200 | 17,370 |
| Developer | **4,881** | 3 | 8,500 | 56,200 | 73,570 |

**Developer input: 219,531 → 4,881 tokens (97.8% reduction).**

---

## 12. Validation Tests (30 total)

### EventBus Core (1-3)
1. Events dispatched in registration order
2. `halt` stops remaining handlers
3. Event history records all events

### Handlers (4-12)
4. AuditTrail writes chain-hash entries
5. AuditTrail integrity check passes after 100 events
6. AuditTrail tamper detected when line modified
7. TokenLogger writes to jsonl
8. ToolPermission blocks Snapshot for analyst
9. ToolPermission allows UIOverview for analyst
10. BudgetEnforcer truncates at soft limit
11. BudgetEnforcer blocks at hard limit
12. BudgetEnforcer pauses at stage_input_hard

### Enforcement (13-19)
13. ApprovalGate waits and resumes on approve
14. ApprovalGate aborts on operator abort
15. No `execute_tool()` in any module public API
16. No `llm_call()` in any module public API
17. Direct MCP call → bypass_detected event
18. Stage without context assembly → halted
19. Event object is immutable (frozen dataclass)

### Integration (20-24)
20. UIOverview response ≤ 1,500 tokens
21. WindowList response ≤ 300 tokens
22. Stage boundary strips tool history
23. Tiered assembly respects A/B/C limits
24. Correlation ID grep traces full lifecycle

### E2E (25-30)
25. Complex mission 1: Developer input ≤ 30K
26. Complex mission 2: completes successfully
27. Complex mission 3: mission report generated
28. Simple mission 1: no regression
29. Simple mission 2: same quality
30. Simple mission 3: feature flag off → old behavior

---

## 13. Trade-offs

| Gain | Cost |
|------|------|
| Token overflow eliminated | Upstream tool response data lost at boundary |
| Operator has full visibility | Every mission generates report (small overhead) |
| Budget enforcement prevents runaway costs | Legitimate large calls need approval (friction) |
| Each concern independently testable | EventBus = ~200 lines infrastructure |
| New handler = new file, no existing code touched | Handler order matters — wrong order = wrong behavior |
| Bypass architecturally impossible | InstrumentedMCPClient adds wrapper overhead |

---

## 14. Rollback

- `TOKEN_GOVERNANCE.enabled = false` → all handlers disabled, pre-D-102 behavior
- Individual handler disable → emits `handler.disabled` event → audit records

---

## 15. File Layout

```
backend/app/
├── events/
│   ├── __init__.py
│   ├── bus.py              # EventBus
│   ├── types.py            # Event, HandlerResult
│   └── catalog.py          # Event type constants
├── handlers/
│   ├── __init__.py
│   ├── audit_trail.py      # #1
│   ├── token_logger.py     # #2
│   ├── bypass_detector.py  # #3
│   ├── tool_permissions.py # #4
│   ├── budget_enforcer.py  # #5
│   ├── approval_gate.py    # #6
│   ├── tool_executor.py    # #7
│   ├── llm_executor.py     # #8
│   ├── context_assembler.py # #9 (handler wrapper)
│   ├── stage_transition.py # #10
│   ├── report_collector.py # #11
│   ├── anomaly_detector.py # #12
│   └── metrics_exporter.py # #13
├── pipeline/
│   ├── __init__.py
│   ├── runner.py           # AgentRunner (event-driven)
│   ├── stage_result.py     # StageResult + extraction
│   └── context_assembler.py # Core assembly logic
└── tools/
    ├── __init__.py
    ├── ui_overview.py
    ├── window_list.py
    └── registry.py         # Tool registration
```
