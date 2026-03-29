# Sprint 35 Retrospective — Security Hardening Baseline

**Date:** 2026-03-29
**Phase:** 7 | **Model:** A | **Class:** Product

---

## What Went Well
1. **D-128 decision-first approach** — Risk classification contract frozen before implementation, zero drift.
2. **Clean test matrix** — 17 risk tests + 15 confinement tests, all pass.
3. **Filesystem guard cross-platform** — Works on Windows with Unix-path skip for CI.

## What Didn't Go Well
1. **GPT kickoff took 4+ rounds** — Security sprints need more upfront contract precision.
2. **Chatbridge degraded** — sendButton selector broken, browser session instability.

## Action Items
| # | Item | Target |
|---|------|--------|
| 1 | Chatbridge selector fix | S36+ |
| 2 | Pre-validated kickoff template for security sprints | Process |

## Metrics
| Metric | Value |
|--------|-------|
| Tasks | 3/3 DONE |
| Decision | D-128 frozen |
| Backend tests | 497 (495 pass + 2 skip) |
| Frontend | 75/75 PASS |
| Playwright | 7/7 PASS |
| Closure-check | ELIGIBLE, 0 failures |
| Total | 611 |
