# Process Gates — Sprint 11+ Governance

**Date:** 2026-03-25
**Status:** ACTIVE — Effective from Sprint 11
**Authority:** Operator (AKCA)

---

## 1. Sprint Status Model

Every sprint report carries two mandatory fields:

| Field | Values | Who Sets It |
|-------|--------|-------------|
| `implementation_status` | `not_started` · `in_progress` · `done` | Copilot |
| `closure_status` | `not_started` · `evidence_pending` · `review_pending` · `closed` | `closed` only by Operator |

**Single canonical model. No other status terminology allowed.**

**Banned terms:** `COMPLETE`, `CODE-COMPLETE`, `PARTIAL`, `PARTIAL+`. None of these appear in sprint documents. Status is always expressed via two axes:
- "Code is done" = `implementation_status=done, closure_status=evidence_pending`
- "Sprint is closed" = `implementation_status=done, closure_status=closed`

Copilot can reach at most `implementation_status=done` + `closure_status=review_pending`. `closure_status=closed` requires operator sign-off only.

---

## 2. Single Source of Truth Hierarchy

When sources conflict, precedence order:

```
1. Repo code (actual behavior)
2. Raw evidence outputs (test/curl/grep output)
3. DECISIONS.md (frozen decisions)
4. Sprint task breakdown (plan + implementation notes)
5. Sprint report (narrative)
6. Chat summary / stale snapshot (reference only, no authority)
```

No interpretation against this hierarchy. Old snapshots are never decision inputs.

---

## 3. Sprint Kickoff Gate

All must be ✅ before any code is written:

| Gate | Owner |
|------|-------|
| Previous sprint `closure_status=closed` | Operator |
| Open decisions max 2 (rest frozen/waived) | Operator + Claude |
| DECISIONS.md delta written | Claude |
| Task breakdown frozen (Implementation Notes + File Manifest sections empty but present) | Claude |
| Exit criteria and evidence checklist ready | Claude |
| `evidence/sprint-{N}/` directory created | Copilot |
| `tools/sprint-closure-check.sh` up to date | Copilot |
| Pre-sprint GPT review PASS | GPT |

---

## 4. Task-Level DONE Definition

A task is DONE only when 5/5 criteria are met:

1. Code committed (`git commit` — 1 task = 1 commit minimum)
2. Related tests passing
3. Evidence produced and saved to `evidence/sprint-{N}/`
4. Implementation Notes updated (same day if deviation occurred)
5. File Manifest updated

If any are missing → task is `IN PROGRESS`.

---

## 5. Commit Rule

```
1 task = minimum 1 commit
Format: "Sprint N Task X.Y: <description>"
Push at sprint end
Mega-commit (files from 3+ unrelated tasks in one commit) forbidden
```

---

## 6. Evidence Standard

Evidence directory: `evidence/sprint-{N}/`

Mandatory files (produced by sprint-closure-check.sh):

| File | Content |
|------|---------|
| `closure-check-output.txt` | pytest + vitest + tsc + lint + build + validator output (single file) |
| `contract-evidence.txt` | grep contract checks + curl/live verification |

Sprint-specific additional files:
- Sprint 10+: SSE raw output stored as section within `contract-evidence.txt` (no separate file)
- Sprint 11+: `mutation-drill.txt` (produced by operator drill, verified by script)
- Sprint 12: `e2e-output.txt` + `lighthouse.txt` (produced by sprint work, verified by script)

**Produced vs Verified:**
- Script **produces**: `closure-check-output.txt`, `contract-evidence.txt`
- Script **verifies existence + PASS**: `mutation-drill.txt`, `e2e-output.txt`, `lighthouse.txt`

No evidence → no closure language. Write `NO EVIDENCE`.

---

## 7. Review Gates

```
Pre-sprint:  GPT review MANDATORY (decisions + plan).
             PASS required before implementation starts.

Mid-sprint:  GPT mid-review MANDATORY.
             {N}.MID PASS required before second-half tasks begin.

Final:       Copilot implementation_status=done →
             sprint-closure-check.sh → evidence packet →
             GPT final review → Claude assessment →
             Retrospective produced →
             Operator sign-off → closure_status=closed
```

Review tasks appear as explicit tasks in the task breakdown:
- `{N}.MID` — GPT mid-sprint review
- `{N}.FINAL` — GPT final review + Claude assessment

---

## 8. Documents Updated at Sprint Closure

| Document | What Changes |
|----------|-------------|
| SPRINT-N-TASK-BREAKDOWN.md | Results section added (exit criteria + test count + known issues + retrospective) |
| docs/ai/STATE.md | Active phase updated (1 line) |
| docs/ai/NEXT.md | Roadmap update |
| Phase report (Sprint 12 only — phase closure) | SLIM format: summary + exit criteria + known issues |

Separate SESSION-HANDOFF.md, CLOSURE-PASS.md, CLOSURE-ASSESSMENT.md are NOT produced.

Sprint 11: No separate phase report — task breakdown Results section is sufficient.
Sprint 12: Phase closure report exists — Phase 5 closure.

---

## 9. Stale Document Quarantine

After closure, old copies are moved to `archive/stale/` or prefixed with `STALE — DO NOT USE FOR CLOSURE`. Two different closure truths for the same sprint cannot coexist in the active repo.

---

## 10. Test Hygiene

- `collect_ignore` forbidden
- `sys.exit()` in test file → sprint blocker
- Real test count = `pytest --co -q | tail -1`
- Hidden test = governance violation

---

## 11. Living Document Rule

Every task breakdown carries two mandatory sections:

```markdown
## Implementation Notes
| Planned | Actual | Reason |
|---------|--------|--------|

## File Manifest (Updated at closure)
| File | Type | Task |
|------|------|------|
```

Every reasonable deviation is recorded the same day. Discovering drift at closure time is forbidden.

---

## 12. Mutation Bridge Rule

For mutation sprints (Sprint 11+):

**API mutation endpoint only writes atomic request artifact; runtime/controller remains sole executor.**

Language "through controller/service" is not used. Aligned with D-001, D-062, D-063.
Direct service call from API layer is a sprint-stop condition.

---

## 13. Retrospective Gate

- Missing retrospective → `closure_status=closed` cannot be set
- Retrospective action items linked to next sprint's kickoff gate
- Same error repeating across 3 consecutive sprints → stop rule must be created and frozen

---

*Process Gates — OpenClaw Local Agent Runtime*
*Effective: Sprint 11+*
*Owner: Operator (AKCA)*
