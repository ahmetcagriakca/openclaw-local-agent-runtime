# D-114 — Handoff Model

**ID:** D-114
**Title:** Handoff Model — Keep current.md Path
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** Claude (Sprint 18 docs cleanup)

---

## Context

The handoff document path `docs/ai/handoffs/current.md` is depended upon by `sprint-plan.py` and other tooling. Alternative paths or renaming would break existing automation.

---

## Decision

- **Keep** `docs/ai/handoffs/current.md` as the handoff file path.
- **Archive** stale handoff snapshots (not overwrite).
- **Role:** Handoff is supplementary to STATE.md/NEXT.md (per D-110). It captures session context, not system truth.
- **Tooling dependency:** `sprint-plan.py` reads this path directly.

---

## Validation

- `docs/ai/handoffs/current.md` exists and is maintained each session.
- No tooling references alternative handoff paths.
- Stale snapshots archived, not deleted.

---

## References

- D-110: Documentation Model Hierarchy
- Sprint 18: Docs cleanup scope
