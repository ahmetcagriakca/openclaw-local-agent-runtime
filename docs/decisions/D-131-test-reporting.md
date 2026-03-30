# D-131: Test Count Reporting Contract

**Status:** Frozen
**Sprint:** 48 (T-2)
**Date:** 2026-03-30

## Decision

Canonical test total includes all three test components:

```
Format: XXX backend + YYY frontend + ZZZ Playwright = NNN total
```

### Rules

1. **Three components always reported:** backend (pytest), frontend (vitest), Playwright (playwright)
2. **All canonical documents** use this format: handoff `current.md`, `STATE.md`, `NEXT.md`, `CLAUDE.md`
3. **Sprint closure evidence** includes three separate output lines: pytest, vitest, playwright
4. **Counts from raw command output only** — no manual counting (consistent with Governance Rule 7)

### Current Baseline (Sprint 47)

705 backend + 217 frontend + 13 Playwright = 935 total

## Rationale

Handoff reported 935 (BE+FE+Playwright) while NEXT.md reported 922 (BE+FE only). CLAUDE.md had a stale count. Inconsistent reporting across documents creates confusion about system state.

## Validation

All canonical documents updated to use the three-component format in the same commit as this decision.
