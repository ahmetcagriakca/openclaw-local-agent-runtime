# Sprint 14A — Event-Driven Architecture + Backend Restructure

**Phase:** 5.5-B (Structural Hardening)
**Source:** SPRINT-14-ADVANCE-PLAN.md Option A (Sprint 14A)
**implementation_status:** not_started
**closure_status:** not_started
**Predecessor:** Sprint 13 — closure pending

---

## Goal

Full EventBus architecture with 13 handlers replacing all inline governance
in agent runner. Backend restructured into layered package layout. Security
keys moved to env vars.

## Scope (From Advance Plan)

| Track | Advance Plan Items | What |
|-------|-------------------|------|
| Track 0 | F1-F18 | EventBus: bus, 13 handlers, enforcement, monitoring |
| Track 1 | F19-F23 | Backend layered: app/, create_app(), api/v1/, models+schemas, RFC 7807 |
| Track 2 | F29-F30 | Math + Telegram → monorepo backend/services/ |
| Track 3 | F45-F46 | Backend test restructure + pyproject.toml |
| Track 4 | N7-N8 | Hardcoded API key + sourceUserId → env var |
| Track 5 | N4-N6 | Health contract test, Telegram tests, WMCP inventory test |

## Removed (Completed in Sprint 13)

| Item | Done In |
|------|---------|
| F32 .editorconfig | Sprint 13 |
| F33 Dev scripts | Sprint 13 |
| F38 ports.md | Sprint 13 |
| F48 D-103 rework limiter | Sprint 13 |
| F49 Legacy dashboard removal | Sprint 13 |

## Sprint 13 Outputs That Feed Sprint 14A

| Sprint 13 Output | Sprint 14A Uses It |
|------------------|-------------------|
| extract_stage_result() | EventBus wraps it in StageTransition handler |
| _format_artifact_context() with distance tiers | ContextAssembler handler builds on it |
| Verified inline L3/L4/L5 | Handlers extract from verified implementations |
| Token report ID fix (resolve_file_id) | ReportCollector handler uses corrected resolution |
| D-103 rework limiter | Already works, bus handler wraps it |

## Out of Scope (Sprint 14B)

Per advance plan Option A, deferred to Sprint 14B:

- Frontend feature-based restructure (F24-F28)
- Monorepo docs: CONTRIBUTING.md, README overhaul, sprint backfill (F31, F34-F37, F39)
- Docker + pre-commit (F40-F44)
- Coverage tooling (F43-F44, F47)
- Structured logging, OpenAPI versioning, dep audit, perf guard (N1-N3, N9-N12)

## Decision Dependencies

| Decision | Must Be Before | Status |
|----------|---------------|--------|
| D-102 full EventBus scope confirmed | Kickoff | Frozen (minimal). Full scope needs operator re-confirmation. |
| D-104 backend package name | Task 14.18 | Not yet proposed. `app/` recommended. |
| D-105 frontend state management | Sprint 14B | Not yet proposed. |

## Risk Assessment (From Advance Plan)

| Risk | Mitigation |
|------|-----------|
| EventBus refactor breaks inline governance | Feature flag. L3/L4/L5 verified in Sprint 13. Rollback = flag off. |
| Backend restructure breaks 225 tests | pytest before AND after every move. Atomic commits. |
| Sprint 14A too large (27 tasks) | Mid-gate between EventBus (Track 0) and backend restructure (Track 1-5). |

## Exit Criteria

1. EventBus dispatches all governance events — zero inline governance in agent runner
2. 13 handlers registered and tested
3. Bypass detector catches direct MCP calls that skip bus
4. create_app() factory with BaseSettings
5. All routes under /api/v1/ routers
6. Backend tests pass in new directory structure
7. ruff + mypy clean
8. 3 complex + 3 simple missions complete on EventBus
9. Security keys in env vars, not hardcoded

---

*Sprint 14A — Vezir Platform*
*Source: SPRINT-14-ADVANCE-PLAN.md Option A*
