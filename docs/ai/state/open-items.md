# open-items.md — Active State Tracker

**Last updated:** 2026-04-04
**Updated by:** Claude Code (Session 27 — Sprint 53 closure)

---

## Active Blockers

| # | Item | Owner | Sprint |
|---|------|-------|--------|
| — | *(none)* | — | — |

---

## Carry-Forward (Phase 7)

| Item | Source | Status |
|------|--------|--------|
| PROJECT_TOKEN rotation/docs | S23 retro | AKCA-owned, non-blocking |
| Docker dev environment | D-116 (S26) | Partially resolved: docker-compose operational (D-116, Jaeger included S28). Remaining: production image optimization |
| ~~Alert "any" namespace scoping~~ | S16 P-16.2 | Done: S49 B-119 (#288) |
| Multi-user auth | D-104/D-108/D-117 | Partially resolved: D-117 operational (S27), backend isolation (S40). Remaining: SSO, external auth, full RBAC |

### Retired (Sprint 48 T-1 Reconciliation)

| Item | Source | Reason |
|------|--------|--------|
| Backend physical restructure | S14A/14B | Superseded by D-115 (S26): "no restructure needed" — frozen decision |
| UIOverview + WindowList tools | D-102 | D-102 CONTEXT_ISOLATION closed (S43). Tools exist only in observability test stubs — no production implementation planned |
| D-102 validation criteria 3-8 | D-102 amendment | S40 multi-user isolation addressed remaining criteria. CONTEXT_ISOLATION feature flag done (S43). No open criteria remain. |
| Jaeger deployment | S16 deferred | Resolved: Jaeger in docker-compose.yml (S28). Deployment operational. |
| Telegram bridge fix | S33+ deferred | Done: S38 task 38.1 |
| B-101 Scheduled mission execution | Backlog P1 | Done: S38 task 38.2 |
| B-103 Mission presets / quick-run | Backlog P1 | Done: S38 task 38.3 |
| B-102 Full approval inbox UI | Backlog P1 | Done: S39 task 39.1 |
| Live mission E2E | S14A waiver | Done: S39 task 39.2 |
| Playwright live API test in CI | S22 retro | Done: S39 task 39.3 |
| Benchmark regression gate D-109 | S22 retro | Done: S39 task 39.4 |
| Feature flag CONTEXT_ISOLATION_ENABLED | D-102 | Done: S43 task 43.5 |
| Frontend Vitest component tests | S16 P-16.3 | Done: S43 (+86), S46 (+20), S47 (+2) = 217 total |
| Stale running missions | S47 audit | Done: S47 normalizer stale detector (>1h → timed_out) |
| WMCP hard-fail on missions | S47 root cause | Done: S46 fix — graceful MCP degradation |

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
| Sprint 48 | Debt-First Hybrid (governance + runtime contract + data normalization + OTel) | CLOSED |
| Sprint 49 | Policy Engine + Operational Hygiene (B-107, B-026, B-119) | CLOSED |
| Sprint 50 | API Hardening + DevEx + Governance Debt (policy write API, B-109, D-132, RFC 9457) | CLOSED |
| Sprint 51 | Contract Testing + Data Safety + Artifact Access (B-110, B-022, B-016) | CLOSED |
| Sprint 52 | Recovery + Replay + Seed Demo (B-023, B-111, B-112) | CLOSED |
| Sprint 53 | Docs-as-Product + Policy Context + Timeout Contract (B-113, B-013, B-014) | CLOSED |
| Sprint 54 | Audit Export + Dynamic Source + Heredoc Cleanup (B-115, B-018, B-025) | DEFERRED (not implemented, tasks → S55) |

## Next Sprint

**Sprint 55 — Audit Export + Dynamic Source + Heredoc Cleanup**
- Status: PLANNING (pre-sprint review pending)
- Model: A (full closure)
- Carried from S54 (deferred)
- Tasks: B-115 audit export (#305), B-018 dynamic sourceUserId (#306), B-025 heredoc reduction (#307)
- Milestone: Sprint 55 (#30)
