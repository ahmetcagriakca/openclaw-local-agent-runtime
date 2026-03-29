# Sprint 39 Kickoff — Product Sprint

**Date:** 2026-03-29
**Phase:** 7
**Model:** A (implementation)
**Class:** Product
**Operator:** GPT (Vezir)
**Implementer:** Claude (Architect)

---

## Scope

| Task | Title | Exit Criteria |
|------|-------|---------------|
| 39.1 | B-102 Full approval inbox UI | Operator can list/detail/approve/reject from UI |
| 39.2 | Live mission E2E | Create → queue/approval → execute → result path verified |
| 39.3 | Playwright live API test in CI | GitHub Actions deterministic pass/fail gate |
| 39.4 | Benchmark regression gate D-109 | Threshold set, fail behavior deterministic, raw compare output |

## Priority Order (GPT)

1. B-102 — product face incomplete without approval inbox
2. Live mission E2E — proves B-102 real behavior
3. Playwright CI — makes live path a permanent gate
4. Benchmark D-109 — regression safety after features land

## Gates

### Mid Review
- B-102 approval flow must work before Live E2E starts
- No Playwright CI polish before Live E2E evidence exists

### Final Review (G2)
- `pytest` green
- `vitest` green
- `npx playwright test` green
- `npm run build` successful
- `npm run lint` clean
- `npx tsc --noEmit` clean
- Closure packet complete with mutation drill
- Retrospective committed

## Explicit Deferrals

- PROJECT_TOKEN rotation → AKCA owner action (not sprint task)
- Frontend Vitest component tests → ongoing quality lane
- CONTEXT_ISOLATION, alert scoping, Jaeger, auth, Docker, restructure → not in scope

## Evidence Checklist

- `pytest-output.txt`
- `vitest-output.txt`
- `playwright-output.txt`
- `e2e-output.txt`
- `tsc-output.txt`
- `lint-output.txt`
- `build-output.txt`
- `validator-output.txt`
- `closure-check-output.txt`
- `file-manifest.txt`
- `review-summary.md`
- `grep-evidence.txt`
- `live-checks.txt`
- `mutation-drill.txt` (REAL evidence required — product sprint)
- Explicit `NO EVIDENCE` where applicable
