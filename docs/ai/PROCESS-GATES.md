# Process Gates — Sprint 12+ Governance

**Date:** 2026-03-26
**Status:** ACTIVE — Effective from Sprint 12 (v4)
**Authority:** Operator (AKCA)
**Patch history:** v3 (Sprint 11), v4 (Sprint 12 — P-01→P-10)

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

All must be checked before any code is written:

| Gate | Owner |
|------|-------|
| Previous sprint `closure_status=closed` | Operator |
| Open decisions max 2 (rest frozen/waived) | Operator + Claude |
| DECISIONS.md delta written | Claude |
| Task breakdown frozen (Implementation Notes + File Manifest sections empty but present) | Claude |
| Exit criteria and evidence checklist ready | Claude |
| `docs/sprints/sprint-{N}/` directory created with `artifacts/` subfolder | Copilot |
| Sprint folder README.md created (P-10) | Copilot |
| `tools/sprint-closure-check.sh` up to date | Copilot |
| Pre-sprint GPT review PASS | GPT |
| Evidence counts from raw command output rule acknowledged (A-04) | All |

---

## 4. Task-Level DONE Definition

A task is DONE only when 5/5 criteria are met:

1. Code committed (`git commit` — 1 task = 1 commit minimum)
2. Related tests passing
3. Evidence produced and saved to `docs/sprints/sprint-{N}/artifacts/`
4. Implementation Notes updated (same day if deviation occurred)
5. File Manifest updated

If any are missing, task is `IN PROGRESS`.

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

Evidence directory: `docs/sprints/sprint-{N}/artifacts/`

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

**Folder separation (P-04):** Narrative docs (`SPRINT-{N}-*.md`) at sprint folder root. Raw outputs and validation artifacts under `artifacts/` subfolder. Never mix narrative and raw at the same level.

No evidence, no closure language. Write `NO EVIDENCE`.

---

## 7. Review Gates

```
Pre-sprint:  GPT review MANDATORY (decisions + plan).
             PASS required before implementation starts.

Mid-sprint:  GPT mid-review + Claude mid-assessment MANDATORY (P-03/P-08).
             {N}.MID-REPORT produced BEFORE review (P-02/P-07).
             Both {N}.MID and {N}.CLAUDE-MID PASS required before second-half tasks.

Final:       Copilot implementation_status=done →
             {N}.REPORT produced proactively (P-02) →
             sprint-closure-check.sh → evidence packet →
             {N}.RETRO produced (P-09) →
             GPT final review + Claude assessment →
             Operator sign-off → closure_status=closed
```

Review tasks appear as explicit tasks in the task breakdown:
- `{N}.MID-REPORT` — Mid-review report draft (prerequisite for mid-review)
- `{N}.MID` — GPT mid-sprint review
- `{N}.CLAUDE-MID` — Claude mid-sprint assessment (parallel with GPT)
- `{N}.REPORT` — Final review report draft (prerequisite for final review)
- `{N}.RETRO` — Sprint retrospective (mandatory, produces at least one actionable output)
- `{N}.FINAL` — GPT final review + Claude assessment
- `{N}.CLOSURE` — Closure summary draft (operator reviews before granting closure)

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
- `sys.exit()` in test file, sprint blocker
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

- Missing retrospective, `closure_status=closed` cannot be set
- Retrospective action items linked to next sprint's kickoff gate
- Same error repeating across 3 consecutive sprints, stop rule must be created and frozen
- `{N}.RETRO` is a mandatory task producing at least one actionable output (P-09)

---

## 14. Handoff Protocol (P-01)

Every completed deliverable ends with a `## Next Step` block:

```markdown
## Next Step
**Produced:** [what this deliverable is]
**Next actor:** [Operator | Copilot | Claude | GPT]
**Action:** [exactly what they should do]
**Blocking:** [yes — nothing else until this is done | no — parallel work can continue]
```

No deliverable sits orphaned. Every output is self-routing.

---

## 15. Mandatory Report Tasks (P-02, P-07)

Sprint task template includes:
- `{N}.MID-REPORT` — Mid-review report draft. Produced proactively when first-half tasks complete.
- `{N}.REPORT` — Final review report draft. Produced proactively when `implementation_status=done`.

Reports are produced before review gates, not on operator request.

---

## 16. Claude Mid-Assessment (P-03, P-08)

`{N}.CLAUDE-MID` runs parallel with GPT mid-review. Claude checks:
- Contract drift from task breakdown
- Living document (Implementation Notes) up to date
- Evidence checklist progress
- Decision compliance (frozen decisions honored)
- Bridge rule (mutation sprints)

Both GPT mid-review and Claude mid-assessment must PASS before second-half tasks.

---

## 17. Frontend Task Splitting (P-04)

When a sprint has frontend work:
- **Shared component task:** Create reusable component (e.g., ConfirmDialog, useMutation) → 1 commit
- **Page integration task(s):** Wire component into specific pages → 1 commit per page or page group

Not: 4 frontend tasks in a single commit.

Stop rule: If commit granularity regresses again (3+ tasks in one commit), create a pre-commit hook. Three sprints of the same violation → automated enforcement.

---

## 18. Evidence Count From Raw Output (P-05)

Test counts come from raw command output only:
- `pytest --co -q | tail -1`
- `npx vitest list | wc -l`

No manual counting. No copy-paste from memory. Source hierarchy: raw output > report narrative.

Closure script auto-parses and reports test counts. If report count differs from script count, script wins.

Stop rule: Test count arithmetic wrong for a third consecutive sprint → closure script auto-fails.

---

## 19. Sprint Folder Structure (P-06)

All new sprints use `docs/sprints/sprint-{N}/` from Sprint 12 onward.

```
docs/sprints/sprint-{N}/
├── README.md                           # Sprint index (P-10)
├── SPRINT-{N}-TASK-BREAKDOWN.md
├── SPRINT-{N}-KICKOFF-GATE.md
├── SPRINT-{N}-MID-REVIEW.md
├── SPRINT-{N}-FINAL-REVIEW.md
├── SPRINT-{N}-RETROSPECTIVE.md
├── SPRINT-{N}-CLOSURE-SUMMARY.md
└── artifacts/                          # Raw outputs only
    ├── closure-check-output.txt
    ├── contract-evidence.txt
    └── ...
```

Narrative docs (`SPRINT-{N}-*.md`) at folder root. Raw outputs under `artifacts/`. Never mixed.

Sprint 11 existing files stay in `evidence/sprint-11/` — full migration in Sprint 13 (P-10).

---

## 20. Sprint Folder README (P-10)

Every sprint folder has a `README.md`:

```markdown
# Sprint {N} — [Title]
**Status:** implementation_status / closure_status
**Goal:** [one sentence]

## Files
| File | Purpose |
|------|---------|
| SPRINT-{N}-TASK-BREAKDOWN.md | Plan + results |
| artifacts/ | Raw evidence outputs |

## Open Decisions
- [list or "none"]

## Closure Prerequisites
- [list]
```

---

## 21. Migration Model (P-10)

**Sprint 12 (Containment):**
- All NEW sprint material goes to `docs/sprints/sprint-12/` + `artifacts/`
- Existing Sprint 7-11 files stay where they are
- No silent moves during Sprint 12
- closure-check.sh updated to read from new path for Sprint 12+

**Sprint 13 (Full Migration):**
- Task 0: produce migration map table (current/target/action/impact)
- No file moves without migration map approved
- Every moved file: grep for old path, update references
- Verify closure script works after migration

---

## 22. Sprint Task Template (Sprint 12+)

Standard sprint task list includes these mandatory tasks:

```
| Task | Description | Side | Dependency |
|------|-------------|------|------------|
| {N}.0 | DECISIONS.md debt + doc cleanup | Docs | — |
| {N}.1→{N}.X | Implementation tasks | Backend/Frontend | ... |
| {N}.MID-REPORT | Mid-review report draft | Copilot | First-half tasks |
| {N}.MID | GPT mid-review | GPT | {N}.MID-REPORT |
| {N}.CLAUDE-MID | Claude mid-assessment | Claude | {N}.MID-REPORT |
| {N}.X+1→{N}.Y | Second-half tasks | Backend/Frontend | {N}.MID + {N}.CLAUDE-MID |
| {N}.REPORT | Final review report draft | Copilot | All impl tasks |
| {N}.RETRO | Sprint retrospective draft | Copilot | After operator drill / pre-final |
| {N}.FINAL | GPT final + Claude assessment | GPT+Claude | {N}.REPORT + {N}.RETRO |
| {N}.CLOSURE | Closure summary draft | Copilot | After {N}.FINAL PASS |
```

---

*Process Gates — OpenClaw Local Agent Runtime*
*Effective: Sprint 12+ (v4)*
*Owner: Operator (AKCA)*
