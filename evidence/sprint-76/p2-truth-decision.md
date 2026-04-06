# D-147 — EventBus Operational Status

**Status:** frozen
**Sprint:** 76
**Date:** 2026-04-06

## Decision

EventBus is classified as **internal test/development infrastructure**, NOT a production control plane.

## Evidence

1. `controller.py` calls `run_agent_with_config()` without `event_bus` parameter
2. `oc_agent_runner_lib.py` accepts `event_bus=None` — all emission guarded by `if event_bus:`
3. No EventBus instantiation in `api/server.py` or any startup path
4. Handler registration exists only in test fixtures
5. `project_handler.py` SSE broadcast added in S75 but never wired to a running EventBus

## Implications

- EventBus code is valid infrastructure for future production wiring
- Current governance handlers (audit, tracing, metrics) are NOT executed through EventBus in production
- OTel tracing/metrics operate independently via `tracing.py`/`meters.py` — not through EventBus
- STATE.md, ENFORCEMENT-CHAIN.md claims of "operational EventBus" are overstated

## Action Required

- Qualify all "operational EventBus" claims in governed docs
- Do NOT remove EventBus code — it's valid for future Phase 11+ wiring
- Future wiring sprint can upgrade status to production with startup evidence
