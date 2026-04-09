# D-150: Capability Routing Transition

**Phase:** Sprint 83 (Phase 10) | **Status:** Frozen
**Date:** 2026-04-09 | **Author:** Claude Code (Opus)

---

## Context

S77 introduced Azure OpenAI as the primary provider (D-148) with `ProviderRoutingPolicy`. The current routing is provider-centric: Azure-first, with fallback chain by provider identity. However, different mission roles and task types have different capability requirements (e.g., long context, code analysis, function calling). The routing policy already has a `capability_manifest` field but it is not task-driven — callers must explicitly pass `required_capabilities`.

## Decision

Transition from provider-identity routing to **capability-based routing**:

1. **Capability Registry** (`agent/providers/capability_registry.py`): Maps task types (role + skill combinations) to required provider capabilities. Single source of truth for what each task needs.

2. **Controller Integration**: `_select_agent_for_role()` resolves required capabilities from the registry before calling `ProviderRoutingPolicy.select()`. No manual `required_capabilities` parameter needed.

3. **Backward Compatibility**: `ProviderRoutingPolicy` API unchanged. If no capabilities resolved (unknown task type), routing falls back to existing Azure-first behavior. All existing tests must pass without modification.

4. **Telemetry**: Capability resolution emits OTel attributes: `capability.required`, `capability.resolved_from`, `capability.match_score`. Visible in existing provider selection telemetry.

5. **Fallback Chain**: When primary lacks a required capability, fallback prefers the provider with the best capability match (not just first available). Ties broken by existing chain order.

## Rules

- R1: Every `_select_agent_for_role()` call resolves capabilities from the registry before routing.
- R2: The registry is configuration-driven (not hardcoded per-call).
- R3: Unknown role/skill pairs get empty capabilities (= existing Azure-first behavior).
- R4: Capability manifest in `ProviderRoutingPolicy` remains the authority on what providers support.
- R5: No breaking changes to `ProviderRoutingPolicy.select()` signature.

## Consequences

- Roles that need `long_context` (analyst, architect) automatically route to capable providers.
- Adding a new capability requirement = one registry entry, not controller code changes.
- Provider additions only need capability manifest update, not routing logic changes.
- Existing tests pass unchanged (R3 guarantees backward compatibility).
