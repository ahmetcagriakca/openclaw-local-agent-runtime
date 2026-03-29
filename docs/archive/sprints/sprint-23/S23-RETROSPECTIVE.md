# Sprint 23 Retrospective — Governance Debt Closure + CI Hygiene

**Date:** 2026-03-28
**Model:** A
**GPT Review Rounds:** Pre-sprint 2 (HOLD→PASS), G1 1 (PASS), G2 5 (HOLD×4→PASS)

---

## What Went Well

1. **Governance debt cleared.** S20 partial deliverables (status-sync, pr-validator) fully completed.
2. **Chat bridge operational.** Claude Code ↔ ChatGPT programmatic review loop worked end-to-end.
3. **GPT review discipline paid off.** GPT caught priority inversion (benchmark over debt) and runtime evidence gaps.
4. **Live acceptance matrix.** All 3 status transitions verified on real Project V2 board.
5. **Stale refs zeroed.** 4→0 with documented fixes.

## What Went Wrong

1. **Cursor's initial scope was wrong priority.** Benchmark + Playwright over governance debt — GPT correctly flagged this.
2. **status-sync needed 3 hotfixes.** Original code had: (a) missing --repo flag, (b) bracket escaping in search, (c) GITHUB_TOKEN project scope limitation. Should have been caught in implementation.
3. **GPT cache/repeat responses.** GPT occasionally returned cached responses instead of reading new evidence — required "DIKKAT" prefix messages.
4. **G2 took 5 rounds.** Evidence requirements were strict but fair — each round revealed a real gap.

## What to Change

1. **Pre-implementation checklist for workflows:** test `gh` commands locally before committing.
2. **PROJECT_TOKEN should be documented** in CLAUDE.md or shared governance.
3. **GPT Custom GPT context may need refresh** — consider shorter, more targeted review messages.

## Findings for S24

| Finding | Type | Priority |
|---------|------|----------|
| closed unmerged → Todo needs PROJECT_TOKEN (gh secret rotation policy) | ops | low |
| `gh issue list --search` is fragile with special chars | tech-debt | low |
| GPT review rounds could be reduced with upfront evidence template | process | medium |

## Metrics

| Metric | Value |
|--------|-------|
| Implementation tasks | 3 |
| Hotfix PRs | 3 (#106, #108, #109) |
| Total PRs merged | 7 (#102-#106, #108-#110) |
| GPT review rounds | 8 total (2 pre-sprint + 1 G1 + 5 G2) |
| Tests | 458 backend + 29 frontend PASS |
| Stale refs | 4 → 0 |
