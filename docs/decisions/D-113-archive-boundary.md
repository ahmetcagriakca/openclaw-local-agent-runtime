# D-113 — Archive Boundary

**ID:** D-113
**Title:** Archive Boundary — Active vs Historical Separation
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** Claude (Sprint 18 docs cleanup)

---

## Context

Active and historical documents were mixed in the same directories, making it unclear which files were current and which were legacy artifacts.

---

## Decision

- **Archive path:** `docs/archive/` sub-structured by type:
  - `sprints/` — closed sprint artifacts
  - `phase-reports/` — completed phase reports
  - `process-history/` — superseded process documents
  - `debt-plans/` — completed debt reduction plans
  - `review-packets/` — historical review evidence
- **Active sprints:** `docs/sprints/` contains last closed + current sprint only.
- **Exceptions:** PHASE-5.5-CLOSURE-REPORT.md and Sprint 15/16 reports remain in active docs (still referenced).
- **Rule:** Old phase reports archived unless actively referenced by current governance.

---

## Validation

- `docs/archive/` directory exists with sub-structure.
- Active `docs/sprints/` contains only last closed + current.
- No stale sprint artifacts in active directories.

---

## References

- Sprint 18: Docs cleanup scope
- D-110: Documentation Model Hierarchy
