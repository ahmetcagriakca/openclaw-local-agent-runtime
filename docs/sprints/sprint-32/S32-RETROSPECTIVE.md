# Sprint 32 Retrospective — API Throttling + Idempotency

**Date:** 2026-03-28
**Model:** A (small sprint, 2 tasks)

## What Went Well
1. Both security features clean and backward compatible
2. Throttle middleware with per-IP sliding window
3. Idempotency key with body mismatch detection
4. Both auto-disabled in test environment

## What Went Wrong
1. Throttle middleware caused test failures in CI (TESTING env var needed)
2. Bridge keyword conflict: "rate limit" text triggers bridge false positive

## Metrics
| Metric | Value |
|--------|-------|
| Tasks | 2 |
| PRs | 2 (#195-#196) |
| Backlog items addressed | B-005 (#154), B-012 (#153) |
