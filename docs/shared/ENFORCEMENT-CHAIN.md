# Enforcement Chain — Vezir Platform

**Effective:** Sprint 67+ (B-145)
**Owner:** Operator (AKCA)

---

## Overview

Every tool call in the Vezir platform passes through a layered enforcement chain before execution. Each layer performs a specific check and can **deny** the request — if an earlier layer denies, later layers are never reached.

```
Request → Auth Middleware (D-117)
  → Tool Gateway (D-024, role-scoped allow/deny)
    → Working Set Enforcer (D-053, filesystem boundary)
      → Risk Engine (D-128, 4-level classification)
        → Policy Engine (D-133, YAML rule evaluation)
          → Execute (tool call via MCP/WMCP)
            → Audit Trail (D-129, hash-chain)
```

---

## Layer Details

### 1. Auth Middleware

| Property | Value |
|----------|-------|
| **What it checks** | API key validity and operator role on mutation endpoints. GET requests pass through (read-only public). |
| **Fail behavior** | `deny` — HTTP 401 (missing/invalid key) or 403 (wrong role) |
| **Bypass possible?** | NO for governed paths. When auth is not configured (no keys in `auth.json`), mutations are allowed. |
| **Decision records** | D-117 (auth foundation) |
| **Key files** | `agent/auth/middleware.py` — `require_operator()`, `get_current_user()` |
|  | `agent/auth/keys.py` — `validate_key()`, `is_auth_enabled()` |

---

### 2. Tool Gateway (Role-Scoped Permissions)

| Property | Value |
|----------|-------|
| **What it checks** | Whether the requested tool is in the allowed set for the current specialist role. Each of the 9 roles has a defined tool allowlist; `None` means all tools allowed. |
| **Fail behavior** | `halt` — `HandlerResult.block()` stops event propagation with denial message |
| **Bypass possible?** | NO. Even `remote-operator` goes through the check (returns `None` = all allowed). |
| **Decision records** | D-024 (tool governance) |
| **Key files** | `agent/events/handlers/tool_permissions.py` — `ToolPermissionsHandler` |
|  | `agent/mission/specialists.py` — `SPECIALIST_TOOL_POLICIES`, `get_specialist_tools()` |
|  | `agent/mission/role_registry.py` — `get_allowed_tools()` |

---

### 3. Working Set Enforcer (Filesystem Boundary)

| Property | Value |
|----------|-------|
| **What it checks** | Filesystem tool calls against the working set boundary: forbidden zones, read/write scope, directory scope, mutation surface authorization (system/code), and budget limits. |
| **Fail behavior** | `deny` — returns `EnforcementResult(allowed=False)` with policy reason. Emits telemetry event. |
| **Bypass possible?** | NO. Non-filesystem tools pass through; all filesystem tools are checked. |
| **Decision records** | D-053 (working set), D-049 (path resolution), D-045 (mutation surface), D-055 (surface mismatch) |
| **Key files** | `agent/context/working_set_enforcer.py` — `enforce_working_set()` |
|  | `agent/context/working_set.py` — `WorkingSet` (scope definition) |
|  | `agent/context/path_resolver.py` — `resolve_canonical()`, `is_path_forbidden()` |
|  | `agent/context/expansion_broker.py` — dynamic scope expansion |
|  | `agent/context/policy_telemetry.py` — `emit_policy_event()` |

---

### 4. Risk Engine (4-Level Classification)

| Property | Value |
|----------|-------|
| **What it checks** | Tool risk level (low/medium/high/critical/blocked) via static tool-name mapping. Blocked command patterns checked against PowerShell commands. Unknown tools default to `high` (fail-safe). |
| **Fail behavior** | `escalate` (high/critical → require approval) or `reject` (blocked → immediate deny) |
| **Bypass possible?** | NO. Blocked patterns are unconditional. High/critical tools require explicit approval. |
| **Decision records** | D-128 (risk classification) |
| **Key files** | `agent/services/risk_engine.py` — `RiskEngine.classify()`, `classify_mission()` |
|  | `agent/services/risk_engine.py` — `TOOL_RISK_MAP`, `BLOCKED_PATTERNS`, `RISK_ACTIONS` |

---

### 5. Policy Engine (YAML Rule Evaluation)

| Property | Value |
|----------|-------|
| **What it checks** | Config-driven YAML rules evaluated pre-stage. Rules sorted by priority (lower = higher). First match wins. Supports: dependency state, risk level, timeout, budget, token budget, caller source, environment, resource tags, side effect scope. |
| **Fail behavior** | `deny` (fail-closed default) / `escalate` / `degrade` — depends on matched rule. No rules loaded or no match = deny. |
| **Bypass possible?** | NO. Fail-closed: if all rules fail to load, deny. If no rule matches, deny. |
| **Decision records** | D-133 (policy engine contract) |
| **Key files** | `agent/mission/policy_engine.py` — `PolicyEngine.evaluate()`, `PolicyRule`, `PolicyDecision` |
|  | `config/policies/*.yaml` — rule definitions |
|  | `agent/api/policy_api.py` — policy read/write API |

---

### 6. Execute (Tool Call via MCP/WMCP)

| Property | Value |
|----------|-------|
| **What it checks** | Passes through all prior layers. Dispatches the actual tool call to the appropriate provider (MCP server, WMCP proxy, or built-in handler). |
| **Fail behavior** | `log` — tool execution errors are captured, logged, and returned to the mission controller. Errors do not bypass audit. |
| **Bypass possible?** | NO. Only reachable after all prior layers approve. |
| **Decision records** | D-001 (single execution owner), D-004 (bridge = stateless translation) |
| **Key files** | `agent/oc_agent_runner_lib.py` — tool call dispatch loop |
|  | `agent/services/tool_catalog.py` — `get_tool_governance()`, tool metadata |
|  | `bridge/oc-bridge.ps1` — PowerShell bridge to Windows MCP |

---

### 7. Audit Trail (Hash-Chain Immutable Log)

| Property | Value |
|----------|-------|
| **What it checks** | Does not check — records. Global handler at priority=0, sees ALL events (including denials from earlier layers). Appends to JSONL with SHA-256 chain hash for tamper detection. |
| **Fail behavior** | `log` — never halts. Write failures are logged but do not block execution. |
| **Bypass possible?** | NO. Priority 0 global handler runs before all type-specific handlers. |
| **Decision records** | D-129 (audit integrity, hash-chain) |
| **Key files** | `agent/events/handlers/audit_trail.py` — `AuditTrailHandler` (EventBus handler, test/dev only — D-147) |
|  | `agent/persistence/audit_integrity.py` — `append_entry()`, `verify_chain()` (D-129 contract) |
|  | `logs/audit-trail.jsonl` — append-only audit log |
|  | `logs/audit/audit.jsonl` — D-129 integrity-verified audit log |

---

## Layer Interaction Rules

1. **Earlier layer deny = later layers never reached.** Auth deny (401/403) means the request never reaches the Tool Gateway. Tool Gateway block means Working Set Enforcer never runs.

2. **EventBus handlers are internal/test infrastructure (D-147).** The EventBus dispatches events to registered handlers in priority order, but is NOT wired to production startup. Controller does not pass EventBus to runner. Handler registration exists only in test fixtures. Future sprint may upgrade to production status.

3. **Audit Trail handler (priority=0) sees ALL events in test context.** When EventBus is wired (tests/future production), it observes every event. In current production, audit logging operates independently via direct file writes.

4. **Policy telemetry is emitted at each enforcement point.** The Working Set Enforcer, Risk Engine, and Policy Engine all emit telemetry events (`policy_denied`, `budget_exhausted`, `mutation_surface_mismatch`, etc.) that feed the Audit Trail and observability stack.

5. **Fail-safe defaults across the chain:**
   - Auth: deny if invalid credentials
   - Tool Gateway: block if tool not in role allowlist
   - Working Set: deny if path not in scope
   - Risk Engine: unknown tools = high risk (require approval)
   - Policy Engine: no rules loaded or no match = deny (fail-closed)

---

## Known Gaps / Future Improvements

| Gap | Notes |
|-----|-------|
| Auth is optional | When no API keys are configured (`auth.json` empty), mutations bypass auth layer. Production deployments should always configure keys. |
| No rate limiting in chain | API throttling (B-005) exists at the HTTP layer but is not part of this enforcement sequence. |
| Working Set expansion | Expansion broker allows dynamic scope widening per role budget. This is by design but could be tightened. |
| Policy Engine rule coverage | Not all edge cases have explicit rules; relies on fail-closed default deny. |
| Audit Trail write failure | If JSONL write fails, execution continues (log-only). Could add alerting on write failures. |

---

*Enforcement Chain — Vezir Platform*
*Sprint 67 — B-145 (D-117, D-024, D-053, D-128, D-133, D-001, D-129)*
