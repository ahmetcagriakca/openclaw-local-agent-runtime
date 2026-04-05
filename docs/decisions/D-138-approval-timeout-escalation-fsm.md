# D-138: Approval Timeout=Deny Semantics + Escalation FSM

**Phase:** Sprint 61 | **Status:** Frozen | **Date:** 2026-04-05

## Context

Vezir claims governed, fail-closed execution with operator control. Approval lifecycle must be deterministic: timeout must never act as implicit approval, expired tokens must never be reused, and every state transition must be auditable.

## Decision

### Canonical Approval States

```
PENDING → APPROVED    (operator approve)
PENDING → DENIED      (operator reject)
PENDING → EXPIRED     (timeout, fail-closed — D-138 doctrine: timeout=deny)
PENDING → ESCALATED   (configurable escalation trigger)
ESCALATED → APPROVED  (elevated-authority approve)
ESCALATED → DENIED    (elevated-authority reject)
ESCALATED → EXPIRED   (escalation timeout)
```

Terminal states: APPROVED, DENIED, EXPIRED. No transitions out of terminal states.

### Non-Negotiable Doctrines

1. **Timeout = Deny.** An expired approval is equivalent to denial. No mission may proceed on an expired approval.
2. **No reuse.** Expired or denied approval records cannot be reused, replayed, or re-approved.
3. **Audit on every transition.** Every state change emits `approval_decided` policy event.
4. **Invalid transitions fail closed.** Attempting to approve an expired record returns False.
5. **Mission behavior is deterministic.** After deny/expire: mission transitions WAITING_APPROVAL → FAILED.
6. **Runtime truth.** Approval semantics are enforced in ApprovalStore, not only in UI.
7. **Persist on decide.** Approval decisions are persisted to disk, not only in-memory.

### Timeout Model

| Context | Default Timeout | Source |
|---------|----------------|--------|
| ApprovalStore (mission runtime) | 60 seconds | Constructor parameter |
| ApprovalExpiry (periodic check) | 30 minutes | D-121 |
| Mutation signal TTL | 60 seconds | D-096 |

### Escalation Model

- Trigger: configurable (e.g., risk=critical, time-in-pending > threshold)
- Effect: approval status → `escalated`, re-enters decision cycle with elevated context
- Escalation timeout: same as original timeout from `expiresAt`
- Escalation audit: emits `approval_decided` with `decision=escalated`

### State Transition Table

| From | To | Trigger | Audit Event | Mission Effect |
|------|----|---------|-------------|----------------|
| pending | approved | operator approve | approval_decided(approved) | WAITING_APPROVAL → RUNNING |
| pending | denied | operator reject | approval_decided(denied) | WAITING_APPROVAL → FAILED |
| pending | expired | timeout exceeded | approval_decided(expired) | WAITING_APPROVAL → FAILED |
| pending | escalated | escalation trigger | approval_decided(escalated) | remains WAITING_APPROVAL |
| escalated | approved | elevated approve | approval_decided(approved) | WAITING_APPROVAL → RUNNING |
| escalated | denied | elevated reject | approval_decided(denied) | WAITING_APPROVAL → FAILED |
| escalated | expired | timeout exceeded | approval_decided(expired) | WAITING_APPROVAL → FAILED |
| approved | * | BLOCKED | — | — |
| denied | * | BLOCKED | — | — |
| expired | * | BLOCKED | — | — |

### Bypass Prevention

- `approve()` on expired record: auto-expire first, return False
- `approve()` on denied record: return False (terminal)
- `approve()` on non-existent record: return False
- Duplicate pending with same paramsHash: return existing (idempotent)
- Direct file manipulation: ignored by in-memory store (runtime truth)

## Consequences

- All approval decisions now persisted to disk on state change
- Expired approvals cannot be "recovered" — new request required
- Escalation is additive, not disruptive — pending semantics preserved
- Mission controller must check approval status before resuming

## References

- D-012: Approval model (definition-level preapproval)
- D-063: Approval via service layer
- D-092: Telegram approval deprecation
- D-096: Mutation response lifecycle
- D-121: Approval gate contract (30min timeout)
