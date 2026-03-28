# Sprint 23 — Task Breakdown

**Sprint:** 23  
**Phase:** 6  
**Title:** Regression Guards & Live E2E CI  
**Model:** A  

**Goal:** Close S22 documentation debt, turn D-109’s deferred benchmark regression into an enforced gate, and run Playwright smoke against a real API in GitHub Actions.

---

## Track 1: Docs + Benchmark Gate

**23.1 — Stale documentation reference remediation**  
Remediate remaining stale references called out in S22 retrospective (targets include `docs/ai/DECISIONS.md` and `docs/ai/handoffs/README.md`). Run `tools/check-stale-refs.py` before/after; any intentional historical pointer must be recorded as a waiver line in this breakdown or in the file with an explicit comment.  
**Acceptance:** Stale count for repo default scan at zero or waivers documented; evidence snippet in sprint artifacts.

**23.2 — Benchmark regression baseline gate**  
Implement checked-in JSON baseline (per-endpoint or aggregate medians from `tools/benchmark_api.py` output) and a compare step that fails CI when latency regresses beyond an agreed tolerance (document threshold in kickoff). Wire into `.github/workflows/benchmark.yml` or a dedicated step. Aligns with D-109 follow-up (“Phase 6’da ayrı sprint”).  
**Acceptance:** Baseline file committed; `benchmark` workflow fails on deliberate regression test or documented dry-run evidence; no hardcoded fake summaries.

## Gates

**23.G1 — Mid Review Gate**  
After Track 1. Review: stale refs closed or waived; regression gate logic reviewed (flaky tolerance, Ubuntu variance). Branch-exempt.

## Track 2: E2E CI

**23.3 — Playwright API smoke in GitHub Actions**  
Add CI job: Python deps, start `uvicorn api.server:app` from `agent/` on `127.0.0.1:8003` (ensure `logs/`, missions/approvals paths valid for CI), install Playwright browsers, run `tests/e2e/`. Use `&` + `sleep`/health poll or `wait-on`-style loop before tests.  
**Acceptance:** Job green on clean tree; documented failure modes; depends on **23.G1** PASS for sequencing. Branch: `sprint-23/t23.3-playwright-ci`.

**23.G2 — Final Review Gate**  
Full evidence: pytest + vitest + tsc + ruff + benchmark + playwright job; sprint artifact index. Branch-exempt.

**23.RETRO — Retrospective**  
Answer: Is the regression gate noisy or stable? Is Playwright CI worth the runtime cost? What to defer to S24 (e.g. OpenAPI → TS SDK)?

**23.CLOSURE — Sprint Closure**  
All implementation task branches merged to `main`; evidence under `docs/sprints/sprint-23/artifacts/`; operator sets `closure_status=closed`.
