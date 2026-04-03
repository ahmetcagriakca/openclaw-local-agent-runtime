# Next Steps — Vezir Platform

**Last updated:** 2026-04-04
**Current:** Phase 7 active. Sprint 49 closed. Sprint 50 pending.

---

## Sprint 49 — Policy Engine + Operational Hygiene (CLOSED)

**Model:** A (full closure) | **Class:** Product + Operational Hygiene
**Scope:** B-107 policy engine implementation (D-133), B-026 DLQ retention policy, B-119 alert namespace scoping
**Tests:** 788 backend + 217 frontend + 13 Playwright = 1018 total (0 TS errors) (D-131)
**Issues:** #286, #287, #288
**New files:** `agent/mission/policy_engine.py`, `agent/api/policy_api.py`, `config/policies/*.yaml` (5 files), 3 test files
**Modified:** `controller.py` (pre-stage hook), `dlq_store.py` (retention), `alert_engine.py` (user_id scoping), `server.py` (policy router)
**Review:** GPT PASS + Claude Chat GO

## Sprint 48 — Debt-First Hybrid (CLOSED)

**Model:** A (full closure) | **Class:** Governance + Runtime Contract + Data Normalization
**Scope:** Cleanup gate (open-items, D-131, doc path audit, decision merge), runtime contract (B-013 policyContext, B-014 timeout), normalizer consolidation, OTel attribute contract, preflight alignment, D-133 policy engine contract
**Tests:** 736 backend + 217 frontend + 13 Playwright = 966 total (0 TS errors) (D-131)
**Issues:** #276-#284
**Decisions:** D-131 (test reporting), D-133 (policy engine contract), D-132 deferred

## Sprint 47 — Frontend Quality & UX Hardening (CLOSED)

**Model:** A (implementation) | **Class:** Governance/Quality
**Scope:** 12 issues — accessibility, responsive, state badge, templates, toast, stale cleanup, telemetry, format utils, URL sync, health API
**Tests:** 705 backend + 217 frontend + 13 Playwright = 935 total (0 TS errors) (D-131)
**Issues:** #264-#275

## Sprint 46 — B-105 Cost Dashboard + B-108 Agent Health (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Cost/outcome dashboard API (3 endpoints), Agent health/capability API (4 endpoints), 2 new frontend pages, sidebar nav
**Tests:** +23 backend (705 total), +20 frontend (215 total)
**Issues:** #160, #163

## Sprint 45 — B-104 Template Parameter UI (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Frontend template UI — API client, TemplatesPage, ParameterForm, RunTemplateModal
**Commits:** `ac4c90c`
**Tests:** +27 frontend (195 total)
**Issue:** #259

## Sprint 44 — CI/CD & Repo Quality (CLOSED)

**Model:** A (implementation) | **Class:** Governance/Quality
**Scope:** CI fix, security findings, coverage, PR template, dependabot
**Commits:** `ca6ebac`, `db0249e`, `101e2ef`, `3c9dcdf`, `1e99524`, `5d3ef32`, `68e4dcc`, `2026ebe`, `6f8350d`, `c967198`, `d671ea8`, `805f853`, `42b73b2`, `52549b4`, `2d4e37c`

## Sprint 43 — Tech Debt Eritme (CLOSED)

**Model:** A (implementation) | **Class:** Governance/Quality
**Scope:** Pydantic V2 compat, bare pass cleanup, frontend tests, branch prune, CONTEXT_ISOLATION flag
**Commits:** `bd8e591`, `64c3de8`, `05bb074`, `7cc272c`
**Tests:** +99 new (863 total: 682+168+13)
**Issue:** #234
**Review:** GPT conversation `69c9984b`

## Sprint 42 — Runner Resilience (B-106) (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** DLQ, exponential backoff, circuit breaker, poison pill detection, auto-resume
**Commits:** `cae2bfa`, `4ab8ceb`, `6ca6af5`
**Tests:** +51 new (669 total)
**Review:** PASS (2nd round) — GPT conversation `69c97bad`

## Sprint 41 — Integrity Hardening / Source-of-Truth Stabilization (CLOSED)

**Model:** A (implementation) | **Class:** Governance
**Scope:** D-071 atomic write remediation, DECISIONS.md index repair, closure drift checker
**Review:** PASS — `docs/ai/reviews/S41-REVIEW.md`
**Commits:** `685acaf`, `1e69d84`, `f39562a`, `e36d192`

## Sprint 40 — Multi-user Isolation + Auth Boundaries (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Backend isolation (D-102), multi-user auth boundary (D-104/D-108), frontend isolation tests
**Review:** PASS (2nd round) — `docs/ai/reviews/S40-REVIEW.md`
**Commits:** `855613f`

## Sprint 39 — Approval Inbox + Live E2E + CI + Benchmark (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** B-102 approval inbox, live mission E2E, Playwright CI, benchmark gate D-109
**Review:** PASS (2nd round) — `docs/ai/reviews/S39-REVIEW.md`
**Commits:** `9b23d4a`, `5cf3817`, `38364b2`, `d1e01ac`, `1628642`

## Sprint 38 — Telegram Fix + Scheduled Missions + Presets (CLOSED)

**Model:** A (implementation) | **Class:** Product
**Scope:** Telegram bridge fix, B-101 scheduled execution, B-103 presets/quick-run
**Review:** PASS (2nd round) — `docs/ai/reviews/S38-REVIEW.md`
**Tests:** +69 new (21 telegram + 34 schedules + 14 presets)

## Carry-Forward

| Item | Source | Status |
|------|--------|--------|
| PROJECT_TOKEN rotation | S23 retro | AKCA-owned |
| Frontend Vitest component tests | S16 | Ongoing quality lane |
| CONTEXT_ISOLATION feature flag | D-102 | Unassigned |
| D-102 validation criteria 3-8 | D-102 | Unassigned |
| Alert namespace scoping | S16 | Done (S49, B-119) |
| Multi-user auth | D-104/D-108 | Unassigned |
| Jaeger deployment | S16 | Unassigned |
| UIOverview + WindowList tools | D-102 | Unassigned |
| Docker dev environment | S14B | Unassigned |
| Backend physical restructure | S14A/14B | Unassigned |

## Decision Debt

- D-021→D-058 extraction (AKCA-assigned, non-blocking)
