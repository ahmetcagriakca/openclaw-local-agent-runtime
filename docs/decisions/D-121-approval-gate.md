# D-121: Approval Gate Contract

**Phase:** 7 (Sprint 30)
**Status:** Frozen
**Date:** 2026-03-28

---

## Decision

Centralized approval inbox with lifecycle management, expiration, and actor-chain audit.

## Approval Request Lifecycle

```
pending → approved
       → rejected (with reason)
       → expired (auto, configurable timeout)
```

## Approval Request Schema

```json
{
  "approval_id": "apv_uuid",
  "mission_id": "mission_uuid",
  "tool_name": "shell",
  "risk_level": "high",
  "status": "pending",
  "requested_by": "mission-controller",
  "requested_at": "2026-03-28T10:00:00Z",
  "decided_by": null,
  "decided_at": null,
  "decision_reason": null,
  "expires_at": "2026-03-28T10:30:00Z"
}
```

## Actor-Chain Audit

Every approval decision records:
- `requested_by`: system component that created the request
- `decided_by`: authenticated operator who approved/rejected
- `decided_at`: timestamp of decision
- `decision_reason`: optional text reason (required for reject)

## Expiration Policy

- Default timeout: 30 minutes (configurable per mission)
- Expired approvals: mission state → `timed_out`
- Expiration check: periodic (every 60s) or on-demand

## Inbox API

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/approvals/inbox | List pending approvals |
| POST | /api/v1/approvals/{id}/approve | Approve (operator) |
| POST | /api/v1/approvals/{id}/reject | Reject with reason (operator) |
| GET | /api/v1/approvals/{id} | Get approval detail |

## Integration

- Mission state machine: `approval_wait` state triggers approval request
- EventBus: `approval_requested`, `approval_decided` events
- Plugin hook: webhook plugin can notify on `approval_requested`
