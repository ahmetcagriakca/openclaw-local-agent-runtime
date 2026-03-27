# Sprint 16 — Retrospective

**Sprint:** 16 — Presentation Layer + CI/CD Foundation (Phase 5.5 Closure)
**Date:** 2026-03-27

---

## What Went Well

1. **5 tracks executed in single session** — Dashboard API, alert system, frontend monitoring, CI/CD pipelines, and foundation items all delivered without inter-track blocking.
2. **Persistence layer simple and effective** — JSON file store (D-106 decision) matches project style. No ORM, no migrations, no complexity. Atomic writes via existing utility.
3. **Alert engine extensible from day one** — 9 default rules + CRUD API means operator can tune thresholds without code changes.
4. **CI/CD from zero to three workflows** — ci.yml (test+lint), benchmark.yml (regression gate), evidence.yml (auto-collect). GitHub Actions ready for first push.
5. **39 tests all pass on first run** — Only 2 minor fixes needed (CSRF for POST test, alert ordering assertion). No design rework.
6. **Frontend TypeScript zero errors** — MonitoringPage + 5 hooks integrated cleanly with existing React architecture.

## What Could Be Better

1. **CSRF middleware blocks TestClient POST** — Forgot that CSRF middleware requires Origin header. Had to add `headers={"Origin": "http://localhost:3000"}` to POST test. Should document this pattern.
2. **Alert rules A-004/A-005 fire on any event** — "any" condition rules (bypass, audit) fire even on unrelated events. Future improvement: restrict "any" rules to their specific event namespace.
3. **No live E2E with running services** — All tests use TestClient / in-memory stores. Didn't test against actual running API + Telegram bot. Acceptable for this sprint but needs attention in Phase 6.
4. **Frontend monitoring page not tested with Vitest** — Component tests would be valuable. Currently only TypeScript compilation verified.

## Metrics

| Metric | Sprint 15 | Sprint 16 | Delta |
|--------|-----------|-----------|-------|
| Backend tests | 419 | 458 | +39 |
| API endpoints | ~20 | ~35 | +15 |
| New Python files | 5 | 12 | +12 (persistence, alerts, auth, API) |
| New TS/TSX files | 0 | 7 | +7 (monitoring feature) |
| GitHub Actions | 0 | 3 | +3 |
| Alert rules | 0 | 9 | +9 |

## Actionable Outputs

- **P-16.1:** Document CSRF Origin header requirement for TestClient POST tests.
- **P-16.2:** Alert engine "any" condition rules should be scoped to relevant event namespaces in future iteration.
- **P-16.3:** Add frontend component tests (Vitest + React Testing Library) in Phase 6.

---

*Sprint 16 Retrospective — Vezir Platform*
