# Sprint 14A — Task Breakdown

**Source:** SPRINT-14-ADVANCE-PLAN.md Option A (archived to docs/archive/sprint-14/)
**Date:** 2026-03-26
**Phase:** 5.5-B — Event-Driven Architecture + Backend Restructure
**implementation_status:** done
**closure_status:** closed (operator sign-off: 2026-03-26)
**Owner:** AKCA (operator)

---

## Items Completed in Sprint 13 (Removed from Scope)

These advance plan items were completed during Sprint 13 and are excluded:

| Item | Description | Done In |
|------|-------------|---------|
| F32 | .editorconfig | Sprint 13 (13.16-EX) |
| F33 | Dev scripts: test-all, dev-backend, dev-frontend | Sprint 13 (13.14-EX) |
| F38 | Port registry (docs/PORTS.md) | Sprint 13 (13.16-EX) |
| F48 | D-103 rework limiter | Sprint 13 (13.3-EX, frozen) |
| F49 | Legacy dashboard code removal (D-097) | Sprint 13 (13.4-EX) |

---

## Task Table (From Advance Plan 14A Draft)

### Track 0: EventBus Architecture (F1-F18)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| **14.0** | **EventBus core: Event (frozen), HandlerResult, EventBus class, event catalog, correlation IDs** | **M** | **Kickoff** |
| 14.1 | AuditTrail handler: chain-hash immutable log | M | 14.0 |
| 14.2 | Extract inline TokenLogger → handler class | S | 14.0 |
| 14.3 | InstrumentedMCPClient + BypassDetector handler | M | 14.0 |
| 14.4 | Extract inline ToolPermissions → handler class | S | 14.0 |
| 14.5 | Extract inline BudgetEnforcer → handler class (4-tier) | M | 14.0 |
| 14.6 | ApprovalGate handler: operator pause/resume/abort | M | 14.5 |
| 14.7 | ToolExecutor handler: gated MCP execution (on cleared event) | M | 14.4, 14.5 |
| 14.8 | LLMExecutor handler: gated LLM execution (on cleared event) | M | 14.5 |
| 14.9 | ReportCollector + AnomalyDetector + MetricsExporter handlers | M | 14.0 |
| 14.10 | StageTransitionHandler + ContextAssembler as handler | S | 14.0 |
| 14.11 | AgentRunner refactor: replace all inline governance with bus.emit() | L | 14.1-14.10 |
| 14.12 | Console real-time timeline (operator-facing) | S | 14.2 |
| 14.13 | EventBus enforcement tests (10 tests from D-102 addendum) | M | 14.11 |
| 14.14 | E2E validation: 3 complex + 3 simple missions on EventBus | M | 14.11 |

### Mid-Review Gate

| Task | Description | Deps |
|------|-------------|------|
| 14.MID-REPORT | Mid-review report | 14.0-14.8 |
| 14.MID | GPT mid-review | 14.MID-REPORT |

Both PASS → Track 1-5 begin.

### Track 1: Backend Restructure (F19-F23)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| 14.18 | Create backend/app/ package: core/, api/v1/, models/, schemas/, services/, middleware/, events/, handlers/, pipeline/ | L | 14.11 |
| 14.19 | create_app() factory + BaseSettings + lifespan + RFC 7807 exceptions | M | 14.18 |
| 14.20 | Migrate routes → api/v1/, logic → services/, types → models/+schemas/ | L | 14.19 |

### Track 2: Service Integration (F29-F30)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| 14.21 | Math Service + Telegram Bot → monorepo backend/services/ | M | 14.20 |

### Track 3: Backend Tooling (F45-F46)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| 14.22 | Backend test restructure: unit/ + integration/ + e2e/ + pyproject.toml | M | 14.20 |

### Track 4: Security Quick Wins (N7-N8)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| 14.17 | Remove hardcoded API key + sourceUserId → env var config | S | Kickoff |

### Track 5: Quality (N4-N6)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| 14.23 | Health endpoint contract test + Telegram Bot unit tests + WMCP tool inventory test | M | 14.21 |

### Track 6: Closure

| Task | Description | Deps |
|------|-------------|------|
| 14.REPORT | Final review report | 14.23 |
| 14.RETRO | Sprint retrospective | 14.REPORT |
| 14.FINAL | GPT final + Claude assessment | 14.REPORT + 14.RETRO |
| 14.CLOSURE | Closure summary | 14.FINAL PASS |

**Implementation: 21 | Process: 6 | Total: 27 tasks**
(Reduced from advance plan's 31 — 5 items completed in Sprint 13)

---

## Decision Dependencies

| Decision | Must Be Before | Status |
|----------|---------------|--------|
| D-102 full EventBus scope confirmed | Kickoff | Frozen (minimal). Full scope needs operator re-confirmation. |
| D-104 backend package name (`app/`) | Task 14.18 | Not yet proposed |

---

## Evidence Checklist

Per advance plan — adapted for reduced scope.

---

*Sprint 14A Task Breakdown — Vezir Platform*
*Source: SPRINT-14-ADVANCE-PLAN.md Option A*
