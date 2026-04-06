# Sprint 38 Kickoff — Product Sprint

**Date:** 2026-03-29
**Phase:** 7
**Model:** A (implementation)
**Class:** Product
**Operator:** GPT (Vezir)
**Implementer:** Claude (Architect)

---

## Pre-Kickoff Blockers (Resolved)

- [x] D-111→D-114 formal decision records created
- [ ] PROJECT_TOKEN rotation (AKCA-owned, non-blocking for implementation)

## Scope

| Task | Title | Exit Criteria |
|------|-------|---------------|
| 38.1 | Telegram bridge fix | Bridge e2e works, regression test added |
| 38.2 | B-101 Scheduled mission execution | Create schedule → persist → execute → observable result |
| 38.3 | B-103 Mission presets / quick-run | Preset select → param fill → run path works |

## Priority Rationale (GPT)

1. Telegram bridge is a carry-forward defect since S33 — broken bridge while adding product surface is bad sequencing
2. B-101 is highest-value product item — without scheduled execution, rest is partial UX
3. B-103 follows naturally — presets + quick-run directly increase usage on execution path

## Gates

### Mid Review
- Playwright contract for new flows must be stable before second-half work
- No B-103 polishing before 38.1 bridge fix proven

### Final Review (G2)
- `pytest` green
- `vitest` green
- `npx playwright test` green
- `npm run build` successful
- `npm run lint` clean
- `npx tsc --noEmit` clean
- Closure packet complete
- Retrospective committed

## Explicit Deferrals

- B-102 Full approval inbox UI → Sprint 39
- Playwright live API test in CI → Sprint 39
- Live mission E2E → Sprint 39
- Benchmark regression gate D-109 → Sprint 39
- Frontend Vitest component tests → ongoing quality lane
- CONTEXT_ISOLATION, alert scoping, Jaeger, auth, Docker, restructure → not in scope

## Decisions

- No new decisions expected. If API contract changes needed for scheduled execution, propose D-131.

## Evidence Checklist

- `pytest-output.txt`
- `vitest-output.txt`
- `playwright-output.txt`
- `tsc-output.txt`
- `lint-output.txt`
- `build-output.txt`
- `validator-output.txt`
- `closure-check-output.txt`
- `file-manifest.txt`
- `review-summary.md`
- `grep-evidence.txt`
- `live-checks.txt`
- Explicit `NO EVIDENCE` where applicable
