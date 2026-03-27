# Governance — Vezir Platform (Shared Rules)

**Effective:** Sprint 19+
**Owner:** Operator (AKCA)

---

## 1. Reviews Are Advisory

GPT and Claude reviews are advisory — they never close work. A PASS verdict means "eligible for operator close", not "closed".

## 2. Operator Authority

Operator is the sole freeze/close authority. No tool, no review verdict, no automation can set `closure_status=closed`.

## 3. Task Breakdown = Source of Truth

`SPRINT-N-TASK-BREAKDOWN.md` is the canonical source of truth for scope, acceptance criteria, and tasks. If `plan.yaml` conflicts with the task breakdown, the task breakdown wins and automation stops.

## 4. plan.yaml = Automation Index

`plan.yaml` is an automation index only. It drives issue creation and validation but is not authoritative for scope decisions.

## 5. Branch-Per-Task Is Mandatory

Every implementation task gets its own branch following the naming convention in `BRANCH-CONTRACT.md`. No direct commits to `main`.

## 6. Manual Merge After Gate PASS

Merging to `main` is manual, performed after gate PASS. Operator authority required.

## 7. PR-Per-Task Deferred

PR-per-task workflow is deferred until operator decides after retrospective.

## 8. Gate Tasks Are Branch-Exempt

Gate tasks (G1, G2, RETRO, CLOSURE) produce review/verdict text only. If a gate finding requires code/config/workflow changes, that becomes a new remediation task with its own branch.

## 9. Closure Validates Merged State Only

No loose branch closure. All task branches must be merged to main before sprint can close. Unmerged branches block closure.
