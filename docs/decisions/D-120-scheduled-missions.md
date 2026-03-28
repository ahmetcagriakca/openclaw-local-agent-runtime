# D-120: Scheduled/Triggered Mission Execution Contract

**Phase:** 7 (Sprint 30 — decision freeze only, implementation S31+)
**Status:** Frozen
**Date:** 2026-03-28

---

## Decision

Cron-based scheduling and event-triggered execution for missions. Implementation deferred to Sprint 31+.

## Scheduling Model

```json
{
  "schedule_id": "sched_uuid",
  "template_id": "tmpl_uuid",
  "cron": "0 9 * * 1-5",
  "timezone": "Europe/Istanbul",
  "parameters": {"repo_url": "https://github.com/..."},
  "enabled": true,
  "last_run": "2026-03-28T09:00:00Z",
  "next_run": "2026-03-29T09:00:00Z"
}
```

## Event-Triggered Model

```json
{
  "trigger_id": "trig_uuid",
  "template_id": "tmpl_uuid",
  "event_source": "webhook",
  "event_filter": {"type": "push", "branch": "main"},
  "parameters_from_event": {"repo_url": "$.repository.url"},
  "enabled": true
}
```

## Execution Queue

- FIFO queue for scheduled missions
- Max concurrent missions: configurable (default 3)
- Queue overflow: reject with 429

## Deferred Items

- Cron parser implementation
- Schedule persistence
- Trigger webhook endpoint
- Queue management API
- UI for schedule management
