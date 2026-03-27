# D-107 — Alert Engine Architecture

**ID:** D-107
**Title:** Alert Engine Design — Rule-Based Threshold Evaluation
**Status:** frozen
**Frozen date:** 2026-03-27 (post-hoc regularization — implemented in Sprint 16 without prior formal record)
**Owner:** AKCA
**Sprint:** 16

---

## Context

Sprint 16 introduced an alert system for the Vezir platform. An architecture needed to be chosen for rule evaluation, storage, and notification dispatch. The advance plan listed D-107 as a dependency decision. The decision was made implicitly during implementation.

---

## Decision

**Rule-based threshold evaluation engine** with the following design:

- Configurable rules (9 default + CRUD API for operator-defined rules)
- Threshold-based evaluation: each rule defines a metric, comparator, and threshold
- Separate notifier layer (`alert_notifier.py`) responsible only for Telegram dispatch
- Alert history stored in the same JSON file store pattern (D-106)
- CRUD API for full operator control over rule lifecycle

---

## Rationale

- Operator-tunable without code changes (threshold CRUD).
- Single evaluation path: no complex CEP or stream processing needed at this stage.
- Telegram notification is the only required channel in Phase 5.5 scope.
- Extensible: additional notification channels can be added to notifier without touching engine.

---

## Trade-off

| Accepted | Deferred |
|----------|---------|
| Simple, auditable evaluation logic | No complex event correlation |
| Operator-tunable at runtime | No stream-based windowing |
| Single notification channel (Telegram) | Multi-channel notification |
| Rules fire per-evaluation-cycle | Deduplication / cool-down period not implemented |

---

## Known Limitation (Carry-Forward)

Alert rules A-004 and A-005 use an `"any"` condition that fires on any event, regardless of namespace. This causes false positives on unrelated events. Carry-forward item P-16.2: scope `"any"` rules to relevant event namespaces in Phase 6.

---

## Impacted Files

| File | Role |
|------|------|
| `agent/observability/alert_engine.py` | Rule evaluation engine |
| `agent/observability/alert_notifier.py` | Telegram dispatch |
| `agent/api/alerts_api.py` | Alert rules CRUD + active/history endpoints |

---

## Validation Method

- `pytest agent/tests/test_sprint16.py` — alert engine and API tests pass
- 9 default rules verified via test suite

---

## Rollback / Reversal Condition

If CEP or stream-based alerting is required, replace threshold evaluator with a stream processor. CRUD API and notifier interfaces remain stable.

---

## Post-Hoc Regularization Note

This decision was implemented in Sprint 16 without a prior formal D-107 record. Advance plan listed D-107 as a dependency. This document closes the governance gap.

No implementation changes required.
