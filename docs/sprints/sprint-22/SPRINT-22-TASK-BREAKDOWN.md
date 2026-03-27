# Sprint 22 — Task Breakdown

**Sprint:** 22
**Phase:** 6
**Title:** Automation Hardening / Operationalization
**Model:** A
**Goal:** Harden existing automation: archive execution, stale ref tuning, Playwright E2E baseline.

---

## Track 1: Automation Hardening

**22.1 — Archive execution automation**
Script: `tools/execute-archive.py`. Reads archive manifest JSON (from `generate-archive-manifest.py`), executes `git mv` for each file, produces execution report. Dry-run by default, `--execute` to actually move. Acceptance: script created, dry-run tested with real manifest (20 files listed), --execute mode available. Full archive execution deferred to operator decision on which sprints to archive.

**22.2 — Stale ref checker tuning**
Update `tools/check-stale-refs.py`: exclude `docs/ai/reviews/` (historical docs with expected generic refs), exclude inline code mentions without path separators, add `--strict` vs `--relaxed` mode. Acceptance: false positive count drops significantly, real stale refs still caught.

## Track 2: E2E Testing

**22.3 — Playwright E2E baseline**
Install Playwright, create `tests/e2e/` directory, write baseline smoke test config and test files. Add `playwright.config.ts`. Acceptance: Playwright installed, config created, smoke test files written and compilable. Live API test run deferred — requires Vezir API running on :8003. Depends on mid-gate PASS.

## Gates

**22.G1 — Mid Review Gate**
After Track 1 complete. Review: archive execution tested, stale ref tuning verified.

**22.G2 — Final Review Gate**
After all tracks complete. Full evidence review.

**22.RETRO — Retrospective**
Did hardening reduce friction? Is Playwright viable for this project?

**22.CLOSURE — Sprint Closure**
All branches merged. All evidence present. Operator sign-off.
