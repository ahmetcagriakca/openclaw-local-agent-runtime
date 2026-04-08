# D-147 — EventBus Operational Status

**Status:** frozen (amended S81)
**Sprint:** 76 (original), 81 (production wiring)
**Date:** 2026-04-06 (original), 2026-04-08 (amended)

## Decision

EventBus is classified as **operational production infrastructure** with feature-flag control.

## Amendment (S81)

Sprint 81 wired EventBus to `server.py` lifespan startup:
- `EVENTBUS_ENABLED` env var (default: `true`) controls activation
- AuditTrailHandler registered as global handler (priority 0, chain-hash audit log)
- ProjectHandler registered for all `project.*` event types (SSE broadcast + rollup invalidation)
- Graceful shutdown: `event_bus.clear()` on app teardown
- 27 new tests (16 production handler + 11 integration)

## Evidence (S76 — original)

1. `controller.py` calls `run_agent_with_config()` without `event_bus` parameter
2. `oc_agent_runner_lib.py` accepts `event_bus=None` — all emission guarded by `if event_bus:`
3. ~~No EventBus instantiation in `api/server.py` or any startup path~~ → Fixed S81
4. ~~Handler registration exists only in test fixtures~~ → Fixed S81
5. ~~`project_handler.py` SSE broadcast added in S75 but never wired~~ → Fixed S81

## Evidence (S81 — production wiring)

1. `api/server.py` lifespan Step 8: EventBus instantiation + handler registration
2. AuditTrailHandler writes chain-hash JSONL to `logs/audit-trail.jsonl`
3. ProjectHandler SSE broadcast verified (16 unit tests)
4. Integration tests: full event flow + graceful degradation (11 tests)
5. Feature flag: `EVENTBUS_ENABLED=false` skips all wiring cleanly

## Implications

- EventBus is now operational for audit + project SSE in production
- Controller → runner EventBus pass-through remains unwired (future sprint)
- OTel tracing/metrics still operate independently — not through EventBus
- Feature flag allows instant rollback without code change
