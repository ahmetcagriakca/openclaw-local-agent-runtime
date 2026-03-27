# D-106 — Persistence Model: JSON File Store

**ID:** D-106
**Title:** Persistence Model Selection — JSON File vs SQLite
**Status:** frozen
**Frozen date:** 2026-03-27 (post-hoc regularization — implemented in Sprint 16 without prior formal record)
**Owner:** AKCA
**Sprint:** 16

---

## Context

Sprint 16 introduced a persistence layer for mission history, OTel traces, and metric snapshots. A storage backend needed to be selected. Options considered: JSON file store vs SQLite.

The decision was made implicitly during Sprint 16 implementation and referenced in the Sprint 16 retrospective as "D-106 decision." This document formalizes what was decided and implemented.

---

## Decision

**JSON file store selected.** Each store (`mission_store.py`, `trace_store.py`, `metric_store.py`) writes atomic JSON files using the existing project atomic-write utility.

No ORM, no migrations, no external dependencies beyond the standard library.

---

## Rationale

- Consistent with existing project file-based patterns.
- No schema migration overhead during active development phase.
- Atomic writes prevent partial-write corruption.
- Readable and debuggable without tooling.
- Sufficient for single-operator, single-node runtime scope.

---

## Trade-off

| Accepted | Deferred |
|----------|---------|
| Simple reads/writes for small datasets | Query performance degrades at scale |
| No dependency on SQLite driver | No relational query capability |
| Easy backup (file copy) | No transactions across multiple stores |

Multi-user, multi-node, or high-volume persistence will require a migration decision (D-104 scope, Phase 6).

---

## Impacted Files

| File | Role |
|------|------|
| `agent/persistence/mission_store.py` | Mission history CRUD |
| `agent/persistence/trace_store.py` | OTel trace storage |
| `agent/persistence/metric_store.py` | Metric snapshot storage |
| `agent/persistence/__init__.py` | Module exports |

---

## Validation Method

- `pytest agent/tests/test_sprint16.py` — persistence store tests pass
- File creation and atomic write verified in test suite

---

## Rollback / Reversal Condition

If multi-user or multi-node requirements emerge, replace JSON stores with SQLite or a proper database under a new decision record. All three stores implement a common interface; swap is localized.

---

## Post-Hoc Regularization Note

This decision was implemented in Sprint 16 without a prior formal D-106 record. The advance plan listed D-106 as a dependency decision. The retrospective referenced "D-106 decision" confirming the choice was made. This document closes the governance gap by recording the decision that was already implemented and tested.

No implementation changes required.
