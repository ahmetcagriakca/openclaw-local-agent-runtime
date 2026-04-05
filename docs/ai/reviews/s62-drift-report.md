# S62 Decision Drift Report

**Sprint:** 62 | **Date:** 2026-04-05 | **Backlog item:** B-135

## Scan Summary

| Metric | Value |
|--------|-------|
| Total decisions scanned | 135 (D-001 through D-135) |
| Drift cases detected | 2 |
| Resolutions applied | 2 |

## Drift Analysis

### D-098: API-level E2E with httpx + pytest — browser E2E deferred

| Field | Detail |
|-------|--------|
| Original sprint | Sprint 12 (Phase 5D) |
| Original status | Frozen |
| Decision | Browser-level E2E (Playwright/Cypress) deferred to Phase 6 |
| Drift evidence | Playwright E2E implemented in Sprint 39 |
| Supporting files | `frontend/playwright.config.ts`, `frontend/tests/*.spec.ts`, `.github/workflows/playwright.yml` |
| Cross-reference | D-131 (Sprint 48) canonizes Playwright in test count (1530 total) |
| Resolution | Status updated to **Superseded (S39)** |

### D-082: Type Generation — Manual TS Types from Frozen Pydantic Schemas

| Field | Detail |
|-------|--------|
| Original sprint | Sprint 9 (Phase 5A-2) |
| Original status | Frozen |
| Decision | No auto code-gen tools (openapi-typescript, etc.) |
| Drift evidence | openapi-typescript auto-generation implemented in Sprint 25 |
| Supporting files | `frontend/src/api/generated.ts`, `frontend/package.json` (`generate:api` script) |
| Cross-reference | Manual types retained in `frontend/src/types/api.ts` for domain enums |
| Resolution | Status updated to **Superseded (S25)** |

## Tooling

New drift detection tool created: `tools/verify_decision_drift.py`
- Parses all decisions from DECISIONS.md
- Counts by status (Frozen, Superseded, Deferred)
- Flags frozen decisions containing drift keywords (deferred, manual, no auto, etc.)
- No external dependencies

## Verdict

Both drift cases resolved. DECISIONS.md updated with status change and explanatory notes. No further action required.
