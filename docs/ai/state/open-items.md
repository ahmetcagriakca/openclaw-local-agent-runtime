# open-items.md — Active State Tracker

**Last updated:** 2026-03-28
**Updated by:** Claude (Architect)

---

## Active Blockers

| # | Item | Owner | Sprint |
|---|------|-------|--------|
| — | *(none — D-104 frozen in commit 3c60a23, 2026-03-27)* | — | — |

---

## Carry-Forward (Phase 6)

| Item | Source | Decision |
|------|--------|----------|
| ~~status-sync full project-field mutation~~ | ~~S20 partial~~ | ✅ S23 task 23.1 DONE |
| ~~pr-validator body required sections~~ | ~~S20 partial~~ | ✅ S23 task 23.2 DONE |
| ~~4 stale refs (DECISIONS.md + handoffs/README.md)~~ | ~~S22 retro~~ | ✅ S23 task 23.3 DONE |
| PROJECT_TOKEN rotation/docs | S23 retro | S24 carry-forward |
| Benchmark regression gate (D-109) | S22 retro / GPT | S24 carry-forward |
| Playwright live API test in CI | S22 retro | S24 carry-forward |
| Dependabot moderate vuln (1) | default branch | S24 carry-forward, owner AKCA |
| Archive --execute on closed sprints | S21 | TBD, operator decision |
| Backend physical restructure | S14A/14B | Unassigned |
| Docker dev environment | S14B | Unassigned |
| Live mission E2E | S14A WAIVER | Unassigned |
| UIOverview + WindowList tools | D-102 | Unassigned |
| Feature flag CONTEXT_ISOLATION_ENABLED | D-102 | Unassigned |
| D-102 validation criteria 3-8 | D-102 amendment | Unassigned |
| Live API + Telegram E2E | S16 WAIVER-1 | Phase 6 |
| Frontend Vitest component tests | S16 P-16.3 | Phase 6 |
| Alert "any" rule namespace scoping | S16 P-16.2 | Phase 6 |
| Jaeger deployment | S16 deferred | Phase 6 |
| Multi-user auth | D-104 / D-108 | Phase 6 |

---

## Active Hard Rules

1. No Phase 6 implementation until Phase 5.5 closure report committed ✅ DONE (d01a3aa)
2. D-105 must be frozen before Sprint 17 kickoff ✅ DONE (frozen 2026-03-27)
3. Sprint 17 = Model A (active — D-105 constraint satisfied)
4. Max 2 consecutive Model B sprints — counter reset by Sprint 17 Model A

---

## Decision Debt

| Item | Since | Priority |
|------|-------|---------|
| D-021→D-058 extraction to DECISIONS.md (38 Phase 4 decisions) | Sprint 8 kickoff | AKCA-assigned, non-blocking |
| ~~D-104 patches 6-8 apply + freeze~~ | ~~S16 session~~ | ✅ DONE — frozen in commit 3c60a23 |

---

## Next Sprint

**Sprint 23 — Phase 6**
- Status: implementation `done`, closure_status `review_pending`
- GPT: Pre-sprint PASS (2 rounds), G1 PASS, G2 PASS (5 rounds)
- RETRO complete
- Awaiting operator `closure_status=closed`

**Sprint 24 — Phase 6**
- Status: NOT STARTED
- Candidates: Benchmark regression gate (D-109), Playwright CI, Dependabot fix
