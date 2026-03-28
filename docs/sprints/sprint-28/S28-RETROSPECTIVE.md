# Sprint 28 Retrospective — Auth Hardening + Observability

**Date:** 2026-03-28
**Model:** A

## What Went Well
1. Auth integration tests caught global state leaking between test modules — fixed with teardown
2. Token expiration clean implementation (backward compatible)
3. LoginPage tests comprehensive (7 tests)
4. Jaeger/Grafana compose setup simple and clean
5. 465 backend + 67 frontend tests

## What Went Wrong
1. Auth test global state leaked to other tests — needed explicit teardown_module
2. Jaeger/Grafana not tested locally (no Docker on current Windows without WSL)

## Metrics
| Metric | Value |
|--------|-------|
| Tasks | 5 |
| PRs merged | 5 (#134-#138) |
| Backend tests | 458→465 (+7 auth) |
| Frontend tests | 60→67 (+7 login) |
