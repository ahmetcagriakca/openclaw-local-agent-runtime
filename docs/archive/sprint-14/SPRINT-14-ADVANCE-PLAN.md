# Sprint 14 — Phase 5.5-B: Structural Hardening + Event-Driven Architecture

**Status:** Advance planning (NOT kickoff-ready)
**Depends on:** Sprint 13 closure
**Estimated scope:** Large — may split into 14A/14B if operator decides

---

## Source: Sprint 13 Deferrals

Everything removed from Sprint 13 v5→v6 per operator directive (2026-03-26).

| # | Item | Original Sprint 13 Task | Category |
|---|------|------------------------|----------|
| F1 | EventBus core: Event (frozen), HandlerResult, EventBus class | 13.0.1 | Architecture |
| F2 | Event catalog: 28 event types with schemas | 13.0.2 | Architecture |
| F3 | Correlation ID system | 13.0.3 | Architecture |
| F4 | AuditTrail handler: chain-hash immutable log | 13.0.5 | Architecture |
| F5 | Extract inline TokenLogger → handler class | 13.0.6 | Architecture |
| F6 | InstrumentedMCPClient + BypassDetector | 13.0.7 | Architecture |
| F7 | Extract inline BudgetEnforcer → handler class | 13.0.9 | Architecture |
| F8 | Extract inline ToolPermissions → handler class | 13.0.8 | Architecture |
| F9 | ApprovalGate handler: operator pause/resume/abort | 13.0.10 | Architecture |
| F10 | ToolExecutor handler: gated execution (only way to call MCP) | 13.0.11 | Architecture |
| F11 | LLMExecutor handler: gated execution (only way to call LLM) | 13.0.12 | Architecture |
| F12 | ReportCollector handler: extract inline report logic | 13.0.13 | Architecture |
| F13 | AnomalyDetector handler | 13.0.14 | Architecture |
| F14 | MetricsExporter handler | 13.0.15 | Architecture |
| F15 | StageTransitionHandler: validates context via bus | 13.0.18 | Architecture |
| F16 | ContextAssembler as bus handler | 13.0.19 | Architecture |
| F17 | AgentRunner refactor: inline → bus.emit() | 13.0.20 | Architecture |
| F18 | Console real-time timeline | — | Monitoring |
| F19 | Backend flat → layered (app/core, api/v1, models, schemas, services, middleware) | 13.6-13.8 | Structure |
| F20 | create_app() factory + Pydantic BaseSettings + lifespan | 13.7 | Structure |
| F21 | API versioning: /api/v1/ prefix | 13.8 | Structure |
| F22 | RFC 7807 error response standard | 13.6 (P3) | Structure |
| F23 | models/ vs schemas/ separation | 13.8 | Structure |
| F24 | Frontend flat → feature-based (features/, components/ui/, api/, hooks/, types/) | 13.10-13.11 | Structure |
| F25 | Frontend API client layer (zero fetch() in feature components) | 13.12 | Structure |
| F26 | Frontend ErrorBoundary | 13.12 | Structure |
| F27 | Frontend @/ path alias + vite proxy config | 13.12 | Structure |
| F28 | Frontend barrel exports per feature | 13.11 | Structure |
| F29 | Math Service → monorepo structure (backend/services/math/) | 13.9 | Structure |
| F30 | Telegram Bot → monorepo structure (backend/services/telegram/) | 13.9 | Structure |
| F31 | CONTRIBUTING.md | 13.16 | Monorepo |
| F32 | .editorconfig | 13.16 | Monorepo |
| F33 | Dev scripts: dev-backend, dev-frontend, dev-all, lint-all, test-all | 13.15 | Monorepo |
| F34 | Root README overhaul | 13.16 | Monorepo |
| F35 | Sprint README backfill (sprint-7 through sprint-12) | 13.16 | Monorepo |
| F36 | Report templates (5 files) | 13.16 | Monorepo |
| F37 | Shared docs: COMMON-PITFALLS.md, VERIFICATION-PATTERNS.md | 13.16 | Monorepo |
| F38 | config/ports.md (updated for 8001/8003/3000/9000) | 13.16 | Monorepo |
| F39 | config/env.example annotated | 13.16 | Monorepo |
| F40 | Dockerfile.dev (backend + frontend) | 13.18 | Tooling |
| F41 | docker-compose.dev.yml (4 services) | 13.18 | Tooling |
| F42 | Pre-commit hooks (ruff + mypy + tsc) | 13.13 | Tooling |
| F43 | pytest --cov (backend coverage measurement) | 13.17 | Tooling |
| F44 | vitest --coverage (frontend coverage measurement) | 13.13 | Tooling |
| F45 | Backend test restructure: unit/ + integration/ + e2e/ | 13.17 | Tooling |
| F46 | pyproject.toml (mypy + ruff config) | 13.17 | Tooling |
| F47 | scripts/generate-types.sh (OpenAPI → frontend types diff check) | 13.12 | Tooling |
| F48 | D-103 rework limiter (must freeze before implementation) | 13.3 | Decision |
| F49 | Legacy dashboard code removal (D-097 commitment) | 13.4 | Cleanup |

---

## Additional Improvements (Not Previously Planned)

| # | Item | Rationale | Category |
|---|------|-----------|----------|
| N1 | Structured logging standard (JSON format, level policy, rotation) | Backend + runtime logging is ad-hoc. JSON logs enable tooling. | Quality |
| N2 | Error handling: frontend API error handling pattern beyond ErrorBoundary | ErrorBoundary catches render errors. API fetch errors need try/catch + toast pattern per feature. | Quality |
| N3 | OpenAPI spec versioning: commit openapi.json, diff on each PR | Currently generated but not tracked. Drift between backend and frontend undetectable. | Quality |
| N4 | Health endpoint contract test | /health returns 11 components now. No test verifies the count or schema. If component added/removed, no alarm. | Quality |
| N5 | Telegram Bot test coverage | telegram_bot.py has zero unit tests. Only manual /health /status testing. | Coverage |
| N6 | WMCP tool inventory test | 18 tools claimed. No automated check that all 18 are registered and respond. | Coverage |
| N7 | Security baseline: remove hardcoded `local-mcp-12345` API key | Known since Phase 2. Still hardcoded. Replace with env var. | Security |
| N8 | Security baseline: remove hardcoded `sourceUserId` | Same vintage. Replace with config. | Security |
| N9 | Dependency audit: check for known vulnerabilities in pip + npm deps | Never done. One `pip audit` + `npm audit` run with fix plan. | Security |
| N10 | Performance regression guard: save Sprint 12 benchmark, compare on Sprint 14 close | Benchmark exists but no comparison mechanism. | Quality |
| N11 | Mission error recovery: graceful failure instead of crash when stage fails | Currently unhandled exceptions may leave mission in bad state. | Reliability |
| N12 | Router.tsx separate file (frontend) | Routes currently mixed into App.tsx. Separate = cleaner. Included in F24 scope. | Structure |

---

## Sizing Analysis

| Category | Items | Estimated Effort |
|----------|-------|-----------------|
| Event-driven architecture (F1-F18) | 18 items | XL — 2 weeks standalone |
| Backend restructure (F19-F23) | 5 items | L — 1 week |
| Frontend restructure (F24-F28) | 5 items | L — 1 week |
| Service integration (F29-F30) | 2 items | M — 2-3 days |
| Monorepo docs (F31-F39) | 9 items | M — 2-3 days |
| Tooling (F40-F47) | 8 items | M-L — 1 week |
| Decision + cleanup (F48-F49) | 2 items | S — 1-2 days |
| New improvements (N1-N12) | 12 items | M — 3-4 days |
| **Total** | **61 items** | **~6-7 weeks** |

**This is too large for one sprint.** Recommend splitting.

---

## Recommended Split

### Option A: Two Sprints (14A + 14B)

**Sprint 14A — Event-Driven + Backend Restructure (~3 weeks)**

| Track | Items | What |
|-------|-------|------|
| Track 0 | F1-F18 | EventBus full architecture: bus, 13 handlers, enforcement, monitoring |
| Track 1 | F19-F23 | Backend layered: app/, create_app(), api/v1/, models+schemas, RFC 7807 |
| Track 2 | F29-F30 | Math + Telegram into monorepo structure |
| Track 3 | F45-F46 | Backend test restructure + pyproject.toml |
| Track 4 | F48-F49 | D-103 freeze + legacy dashboard removal |
| Extras | N4, N5, N6, N7, N8 | Health contract test, Telegram tests, WMCP test, security keys |

Rationale: EventBus refactors the backend pipeline. Backend restructure moves the files. Do both in the same sprint so files only move once. Security keys are quick wins.

**Sprint 14B — Frontend Restructure + Tooling + Monorepo (~3 weeks)**

| Track | Items | What |
|-------|-------|------|
| Track 0 | F24-F28 | Frontend feature-based: features/, components/ui/, api/, @/ alias, barrel exports |
| Track 1 | F31-F39 | Monorepo: CONTRIBUTING.md, .editorconfig, dev scripts, README, backfill, templates, ports, env |
| Track 2 | F40-F44, F47 | Docker, pre-commit, coverage (backend+frontend), type sync |
| Track 3 | F35-F37 | Sprint README backfill, report templates, shared docs |
| Extras | N1-N3, N9-N12 | Structured logging, error handling, OpenAPI versioning, dep audit, perf guard, error recovery, router.tsx |

Rationale: Frontend restructure is independent of backend. Tooling (Docker, pre-commit) benefits from both backend and frontend being in final structure. Monorepo docs reflect final state.

### Option B: Three Smaller Sprints (14/15/16)

| Sprint | Focus | Duration |
|--------|-------|----------|
| 14 | EventBus + enforcement + D-103 + legacy removal + security keys | ~2 weeks |
| 15 | Backend + frontend restructure + service integration | ~2 weeks |
| 16 | Tooling + monorepo + docs + coverage + Docker + remaining | ~2 weeks |

Smaller batches, more gates, less risk per sprint. Better if Sprint 13 reveals unexpected complexity.

---

## Draft Task Table (Option A: Sprint 14A)

| Task | Description | Size | Deps |
|------|-------------|------|------|
| **14.0** | **EventBus core: Event, HandlerResult, EventBus class, event catalog, correlation IDs** | **M** | **Kickoff** |
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
| 14.MID-REPORT | Mid-review report | S | 14.0-14.8 |
| 14.MID | GPT mid-review | — | 14.MID-REPORT |
| 14.15 | Freeze D-103 + implement rework limiter as bus handler | M | 14.0 |
| 14.16 | Legacy dashboard code removal (D-097) | M | Kickoff |
| 14.17 | Remove hardcoded API key + sourceUserId → env var config | S | Kickoff |
| 14.18 | Create backend/app/ package: core/, api/v1/, models/, schemas/, services/, middleware/, events/, handlers/, pipeline/ | L | 14.11 |
| 14.19 | create_app() factory + BaseSettings + lifespan + RFC 7807 exceptions | M | 14.18 |
| 14.20 | Migrate routes → api/v1/, logic → services/, types → models/+schemas/ | L | 14.19 |
| 14.21 | Math Service + Telegram Bot → monorepo backend/services/ | M | 14.20 |
| 14.22 | Backend test restructure: unit/ + integration/ + e2e/ + pyproject.toml | M | 14.20 |
| 14.23 | Health endpoint contract test + Telegram Bot unit tests + WMCP tool inventory test | M | 14.21 |
| 14.REPORT | Final review report | S | 14.23 |
| 14.RETRO | Sprint retrospective | S | 14.REPORT |
| 14.FINAL | GPT final + Claude assessment | — | 14.REPORT + 14.RETRO |
| 14.CLOSURE | Closure summary | S | 14.FINAL PASS |

**Implementation: 24 | Process: 7 | Total: 31 tasks**

Note: This is advance planning. Final task count may change based on Sprint 13 outcomes.

---

## Draft Task Table (Option A: Sprint 14B)

| Task | Description | Size |
|------|-------------|------|
| 14B.0 | Frontend feature structure: features/, components/ui/, api/, hooks/, types/, layouts/, lib/ | L |
| 14B.1 | Migrate components → features/ (dashboard, roles, approvals, missions) + barrel exports | L |
| 14B.2 | API client layer + ErrorBoundary + @/ alias + vite proxy + router.tsx | M |
| 14B.3 | Frontend error handling pattern: API fetch errors → toast per feature | S |
| 14B.4 | Frontend test restructure + vitest --coverage | M |
| 14B.5 | Lighthouse regression check | S |
| 14B.MID | Mid-review gate | — |
| 14B.6 | Dev scripts: dev-backend, dev-frontend, dev-all, lint-all, test-all | M |
| 14B.7 | scripts/generate-types.sh (OpenAPI → frontend type diff check) | S |
| 14B.8 | Pre-commit hooks: ruff + mypy + tsc | S |
| 14B.9 | Dockerfile.dev (backend + frontend) + docker-compose.dev.yml (4 services) | M |
| 14B.10 | Root README overhaul + CONTRIBUTING.md + .editorconfig + config/ports.md + config/env.example | M |
| 14B.11 | Sprint README backfill (7→13) + report templates (5) + shared docs (2) | M |
| 14B.12 | Structured logging standard: JSON format, level policy | M |
| 14B.13 | OpenAPI spec versioning: commit openapi.json, add diff check to CI | S |
| 14B.14 | Dependency audit: pip audit + npm audit + fix plan | S |
| 14B.15 | Performance regression: compare Sprint 14B benchmark vs Sprint 12 baseline | S |
| 14B.16 | Mission error recovery: graceful stage failure handling | M |
| 14B.REPORT | Final review report | S |
| 14B.RETRO | Retrospective | S |
| 14B.FINAL | GPT final + Claude assessment | — |
| 14B.CLOSURE | Closure summary | S |

**Implementation: 17 | Process: 5 | Total: 22 tasks**

---

## Decision Dependencies

| Decision | Must Be Before | Current Status |
|----------|---------------|---------------|
| D-102 EventBus scope confirmed | Sprint 14A kickoff | Frozen (minimum). Full scope needs operator re-confirmation for Sprint 14A. |
| D-103 rework limiter | Sprint 14A Task 14.15 | Proposed. Must freeze at Sprint 14A kickoff or remove from sprint. |
| D-104 backend package name | Sprint 14A Task 14.18 | Not yet proposed. `app/` recommended (industry standard). |
| D-105 frontend state management | Sprint 14B Task 14B.0 | Not yet proposed. Keep React hooks (no new deps) recommended. |

---

## Sprint 13 Outputs That Feed Sprint 14

| Sprint 13 Output | Sprint 14 Uses It |
|-----------------|-------------------|
| extract_stage_result() function | EventBus wraps it in StageResult handler |
| assemble_context_tiered() function | EventBus wraps it in ContextAssembler handler |
| Existing inline L3/L4/L5 verified working | Handlers extract from these verified implementations |
| UIOverview + WindowList tools | Already registered, no changes needed |
| Token report ID fix | ReportCollector handler builds on corrected ID resolution |
| WSL naming settled | Backend restructure uses correct paths |
| Stale docs archived | Monorepo docs start from clean baseline |

---

## Risk Assessment

| Risk | Sprint | Mitigation |
|------|--------|-----------|
| EventBus refactor breaks existing inline governance | 14A | Feature flag. L3/L4/L5 verified in Sprint 13. Rollback = flag off. |
| Backend restructure breaks 233 tests | 14A | pytest before AND after every move. Atomic commits. |
| Frontend restructure breaks 29 tests + build | 14B | npm run build + tsc --noEmit after every move. |
| Docker config diverges from local dev | 14B | Same ports. Tested as acceptance criterion. |
| Sprint 14A too large (31 tasks) | 14A | Split: EventBus first half, backend second half, with mid-gate between. |
| D-103 still not frozen at Sprint 14A kickoff | 14A | Remove from sprint (same rule as Sprint 13). |

---

## Timeline Estimate

| Sprint | Duration | Focus |
|--------|----------|-------|
| Sprint 13 | ~2 weeks | D-102 minimum fix + bugs + cleanup |
| Sprint 14A | ~3 weeks | EventBus + backend restructure + security |
| Sprint 14B | ~3 weeks | Frontend restructure + tooling + monorepo + Docker |
| Phase 6 | After 14B | New features, browser E2E, CI/CD pipeline, full security hardening |

---

## Next Step

**Produced:** Sprint 14 advance plan (61 deferred + new items, sizing, split options, draft task tables)
**Next actor:** Operator
**Action:** Review. No action needed now — this is advance planning. Sprint 13 must complete first. Key decision before Sprint 14: Option A (2 sprints) vs Option B (3 sprints).
**Blocking:** No — Sprint 13 independent.
