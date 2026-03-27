# open-items.md — Active State Tracker

**Last updated:** 2026-03-27
**Updated by:** Claude (Architect)

---

## Active Blockers

| # | Item | Owner | Sprint |
|---|------|-------|--------|
| 1 | D-104 patches 6-8 apply + freeze | AKCA / Claude Code | Pre-S17 |

---

## Carry-Forward (Phase 6)

| Item | Source | Decision |
|------|--------|----------|
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
3. Sprint 17 must use Model A or explicitly declare Model B at kickoff
4. Max 2 consecutive Model B sprints — Sprint 17 is first Model B eligible post-reset

---

## Decision Debt

| Item | Since | Priority |
|------|-------|---------|
| D-021→D-058 extraction to DECISIONS.md (38 Phase 4 decisions) | Sprint 8 kickoff | AKCA-assigned, non-blocking |
| D-104 patches 6-8 apply + freeze | S16 session | Low urgency |

---

## Next Sprint

**Sprint 17 — Phase 6**
- Status: NOT STARTED
- Kickoff gate: OPEN
- Required before kickoff: D-104 patch status decision
- Carry-forward assignment needed before scope is frozen
