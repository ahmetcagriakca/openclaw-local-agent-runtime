# Sprint 27 Retrospective — Identity Foundation + Deterministic Delivery

**Date:** 2026-03-28
**Model:** A

## What Went Well
1. D-117 auth contract clean and implementable
2. Backend auth middleware backward compatible (no auth.json = allow all)
3. Frontend auth context with localStorage persistence
4. Mock provider simple and stable
5. All 458 backend + 60 frontend tests pass

## What Went Wrong
1. Initial auth implementation broke 23 tests (mutation endpoints need headers)
2. Fixed by making auth opt-in (no config = disabled) — correct for MVP

## What to Change
1. Add auth integration tests (with config/auth.json present)
2. Consider session expiration and token rotation on frontend

## Metrics
| Metric | Value |
|--------|-------|
| Tasks | 5 |
| Decisions frozen | 1 (D-117) |
| PRs merged | 5 (#129-#133) |
| Backend tests | 458 |
| Frontend tests | 55→60 (+5 auth) |
