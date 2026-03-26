# Sprint 14A — Event-Driven Architecture + Backend Restructure

**Phase:** 5.5-B (Structural Hardening)
**Status:** implementation_status=not_started, closure_status=not_started
**Predecessor:** Sprint 13 (Stabilization) — closure pending
**Source:** SPRINT-14-ADVANCE-PLAN.md Option A (Sprint 14A)
**Goal:** Full EventBus architecture with 13 handlers + backend layered restructure.

---

## Scope Summary

Sprint 14A implements the event-driven architecture from D-102 and restructures
the backend into a layered package layout. This is the largest architectural
change since Phase 4.

| Track | Items | Scope |
|-------|-------|-------|
| Track 0 | EventBus core + 13 handlers | F1-F18 from advance plan |
| Track 1 | Backend restructure | F19-F23 from advance plan |
| Track 2 | Service integration | F29-F30 (Math + Telegram → monorepo) |
| Track 3 | Backend tooling | F45-F46 (test restructure + pyproject.toml) |
| Track 4 | Security quick wins | N7-N8 (hardcoded keys → env vars) |
| Track 5 | Quality | N4-N6 (health contract, Telegram tests, WMCP inventory) |

## Already Done in Sprint 13

These items from the advance plan are complete — removed from Sprint 14A scope:

| Item | Done In | Notes |
|------|---------|-------|
| F48 D-103 rework limiter | Sprint 13 | Frozen + implemented |
| F49 Legacy dashboard removal | Sprint 13 | D-097 completed |
| F32 .editorconfig | Sprint 13 | Created |
| F33 Dev scripts | Sprint 13 | test-all.sh, dev-backend.sh, dev-frontend.sh |
| F38 ports.md | Sprint 13 | docs/PORTS.md |
| L1 StageResult isolation | Sprint 13 | stage_result.py |
| L2 Distance-based context tiers | Sprint 13 | controller.py enhanced |
| Token report ID fix | Sprint 13 | normalizer.resolve_file_id() |

## Sprint 13 Outputs That Feed Sprint 14A

| Sprint 13 Output | Sprint 14A Uses It |
|------------------|-------------------|
| extract_stage_result() | EventBus wraps it in StageTransition handler |
| _format_artifact_context() with distance tiers | ContextAssembler handler builds on it |
| Verified inline L3/L4/L5 | Handlers extract from verified implementations |
| Token report ID fix (resolve_file_id) | ReportCollector handler uses corrected resolution |
| D-103 rework limiter | Already works, bus handler wraps it |

## Exit Criteria

1. EventBus dispatches all governance events — zero inline governance in agent runner
2. 13 handlers registered and tested (unit + integration)
3. Bypass detector catches direct MCP calls that skip bus
4. create_app() factory with BaseSettings
5. All routes under /api/v1/ routers
6. Backend tests pass in new directory structure
7. ruff + mypy clean on backend
8. 3 complex + 3 simple missions complete on EventBus
9. Security keys moved to env vars

## Decisions Needed

| Decision | Must Be Before | Status |
|----------|---------------|--------|
| D-102 full EventBus scope confirmed | Kickoff | Frozen (minimal). Full scope needs re-confirmation. |
| D-104 backend package name (`app/` vs `vezir/`) | Task 14.18 | Not yet proposed |

---

*Sprint 14A — Vezir Platform*
*Created: 2026-03-26*
