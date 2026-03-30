# open-items.md — Active State Tracker

**Last updated:** 2026-03-30
**Updated by:** Claude (Architect)

---

## Active Blockers

| # | Item | Owner | Sprint |
|---|------|-------|--------|
| — | *(none)* | — | — |

---

## Carry-Forward (Phase 7)

| Item | Source | Decision |
|------|--------|----------|
| ~~Telegram bridge fix~~ | ~~S33+ deferred~~ | ✅ S38 task 38.1 DONE |
| ~~B-101 Scheduled mission execution~~ | ~~Backlog P1~~ | ✅ S38 task 38.2 DONE |
| ~~B-103 Mission presets / quick-run~~ | ~~Backlog P1~~ | ✅ S38 task 38.3 DONE |
| ~~B-102 Full approval inbox UI~~ | ~~Backlog P1~~ | ✅ S39 task 39.1 DONE |
| ~~Live mission E2E~~ | ~~S14A waiver~~ | ✅ S39 task 39.2 DONE |
| ~~Playwright live API test in CI~~ | ~~S22 retro~~ | ✅ S39 task 39.3 DONE |
| ~~Benchmark regression gate D-109~~ | ~~S22 retro~~ | ✅ S39 task 39.4 DONE |
| PROJECT_TOKEN rotation/docs | S23 retro | AKCA-owned, non-blocking |
| Backend physical restructure | S14A/14B | Unassigned |
| Docker dev environment | S14B | Unassigned |
| UIOverview + WindowList tools | D-102 | Unassigned |
| ~~Feature flag CONTEXT_ISOLATION_ENABLED~~ | ~~D-102~~ | ✅ S43 task 43.5 DONE |
| D-102 validation criteria 3-8 | D-102 amendment | Unassigned |
| ~~Frontend Vitest component tests~~ | ~~S16 P-16.3~~ | ✅ S43 (+86), S46 (+20), S47 (+2) = 217 total |
| Alert "any" rule namespace scoping | S16 P-16.2 | Unassigned |
| Jaeger deployment | S16 deferred | Unassigned |
| Multi-user auth | D-104 / D-108 | Unassigned |
| ~~Stale running missions~~ | ~~S47 audit~~ | ✅ S47 — normalizer stale detector (>1h → timed_out) |
| ~~WMCP hard-fail on missions~~ | ~~S47 root cause~~ | ✅ S46 fix — graceful MCP degradation |

---

## Decision Debt

| Item | Since | Priority |
|------|-------|---------|
| D-021→D-058 extraction to DECISIONS.md (38 Phase 4 decisions) | Sprint 8 kickoff | AKCA-assigned, non-blocking |

---

## Completed This Phase

| Sprint | Scope | Status |
|--------|-------|--------|
| Sprint 42 | B-106 Runner Resilience (DLQ, backoff, circuit breaker, auto-resume) | CLOSED (G2 PASS) |
| Sprint 43 | Tech Debt Eritme (Pydantic, bare pass, frontend tests, feature flag) | CLOSED |
| Sprint 44 | CI/CD & Repo Quality | CLOSED |
| Sprint 45 | B-104 Template Parameter UI (last P1) | CLOSED |
| Sprint 46 | B-105 Cost Dashboard + B-108 Agent Health View + 4 bugfixes | CLOSED |
| Sprint 47 | Frontend Quality & UX Hardening (12 issues: a11y, responsive, toast, stale, format) | CLOSED |

## Next Sprint

**Sprint 48 — Phase 7**
- Status: NOT STARTED
- P2 candidates: B-026 DLQ retention, B-013 Richer policyContext, B-107 Policy engine, B-109 CLI scaffolding, B-014 timeoutSeconds
