# D-112 — Governance Consolidation

**ID:** D-112
**Title:** Governance Consolidation — PROCESS-GATES + PROTOCOL → GOVERNANCE.md
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** Claude (Sprint 18 governance simplification)

---

## Context

Two governance documents existed with overlapping content:
- `PROCESS-GATES.md` (368 lines) — gate model, evidence rules, closure process
- `PROTOCOL.md` (93 lines) — sprint status model, cross-review protocol

Combined they were 461 lines with duplication, patch history, and sprint-specific rules that no longer applied.

---

## Decision

- **Merge** PROCESS-GATES.md + PROTOCOL.md into single `docs/ai/GOVERNANCE.md` (~150-200 lines).
- **Keep:** Source hierarchy, sprint status model, gate model, done/evidence/closure/archive rules, test hygiene, retrospective gate, proposal format, cross-review protocol.
- **Drop:** Patch history (P-01→P-10), migration model, sprint-specific rules.
- **Effective:** Sprint 12+.

---

## Validation

- `docs/ai/GOVERNANCE.md` exists and contains all kept sections.
- PROCESS-GATES.md and PROTOCOL.md archived or removed.
- No broken references to old file paths.

---

## References

- Sprint 18: Governance simplification scope
- D-110: Documentation Model Hierarchy
