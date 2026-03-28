# D-124: Legacy Item Normalization Policy

**ID:** D-124
**Status:** Frozen
**Phase:** 7 / Sprint 33
**Date:** 2026-03-28

---

## Context

16 issues from S20/S23/S24 exist on the Project V2 board without Sprint field values. These predate the D-122 contract (Sprint 31). Full backfill of all fields is expensive and yields no operational value.

## Decision

### Normalization Scope

Legacy items (pre-S31 contract) receive minimum normalization:

1. **Sprint field backfill:** Set Sprint = correct number (20, 23, or 24) based on milestone or issue creation context
2. **Milestone assignment:** Create milestones for S20, S23, S24 if missing; assign to respective issues
3. **Status correction:** Verify issue state matches Project Status; fix mismatches
4. **Close resolved issues:** #100 and any other resolved-but-open items

Legacy items DO NOT require: Task ID backfill, Type/Track/PR Link population, or any field that did not exist at creation time.

### Item Classification (Validator Taxonomy)

Every item on the board must fall into exactly one class. Unknown is not legacy.

| Class | Detection Rule | Validator Behavior |
|-------|---------------|-------------------|
| **Backlog** | Has `backlog` label | Enforce: Status, Priority label, Issue State |
| **Sprint task (current contract)** | Has `sprint` label AND milestone >= S31 | Enforce: full canonical contract |
| **Legacy sprint task** | Has `sprint` label AND milestone < S31 (or Sprint field < 31) | Enforce: Status, Sprint field, Issue State. WARN on missing Task ID. |
| **Normalized legacy** | Has milestone for S20/S23/S24 AND Sprint field set (after normalization) | Same as legacy sprint task |
| **Unclassified** | None of the above | **FAIL — manual review required** |

**Critical rule:** `Unclassified` is always FAIL, never SKIP. If an item cannot be classified, it is a board integrity problem that must be resolved before the validator can pass.

### Normalization Execution

1. Create missing milestones (Sprint 20, Sprint 23, Sprint 24 — state: closed)
2. Assign milestones to 16 legacy items
3. Set Sprint field via project GraphQL mutation
4. Close #100 and other resolved-but-open items
5. Run project-validator.py — expect 0 unclassified

## Trade-off

| Accepted | Deferred |
|----------|----------|
| Minimum normalization (Sprint + Status + Issue State) | Full field backfill for legacy |
| Explicit classification taxonomy | Type/Track cleanup on legacy |
| Unclassified = FAIL (no silent bypass) | Historical completeness |

## Impacted Files

- `tools/project-validator.py` — Classification taxonomy + legacy rules
- `docs/shared/PROJECT-SETUP.md` — Legacy normalization policy

## Validation

- 16 legacy items: Sprint field populated, milestone assigned
- #100 closed
- 0 unclassified items on board
- project-validator.py PASS on full board

## Rollback

If legacy normalization causes unexpected issues, revert Sprint field values and milestones. Classification taxonomy in validator is code-level and easily adjustable.
