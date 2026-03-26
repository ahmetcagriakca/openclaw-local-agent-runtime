# Process Patch v4 — Sprint 12+ Improvements

**Date:** 2026-03-26
**Source:** Claude retro (R-01→R-05) + User-originated handoff directive
**Status:** Apply to PROCESS-GATES.md and project instructions before Sprint 12

---

## Patch 1: Handoff Protocol (NEW — Section 14 in PROCESS-GATES)

### Rule: Every completed deliverable ends with an explicit handoff block.

When any actor (Claude, Copilot, GPT) completes a task or deliverable, the output must end with a `## Next Step` block containing:

1. **What was produced** (1 line)
2. **Who acts next** (name: Operator / Copilot / Claude / GPT)
3. **Exact action** (what they do with it)
4. **Blocking?** (yes/no — can other work continue in parallel?)

### Format

```markdown
## Next Step
**Produced:** [what this deliverable is]
**Next actor:** [Operator | Copilot | Claude | GPT]
**Action:** [exactly what they should do]
**Blocking:** [yes — nothing else until this is done | no — parallel work can continue]
```

### Examples by Actor

**Claude produces a task breakdown:**
```
## Next Step
**Produced:** SPRINT-12-TASK-BREAKDOWN.md
**Next actor:** Operator
**Action:** Send to GPT for pre-sprint review. Paste the full document.
**Blocking:** Yes — no implementation before GPT PASS.
```

**Copilot reaches mid-review point:**
```
## Next Step
**Produced:** Tasks 12.1→12.6 complete. Mid-review report draft at docs/sprints/sprint-12/SPRINT-12-MID-REVIEW.md
**Next actor:** Operator
**Action:** Send SPRINT-12-MID-REVIEW.md to GPT for mid-sprint review.
**Blocking:** Yes — no second-half tasks before GPT mid-review PASS.
```

**Copilot reaches implementation_status=done:**
```
## Next Step
**Produced:** All tasks done. Report draft + evidence at docs/sprints/sprint-12/
**Next actor:** Operator
**Action:** Send SPRINT-12-FINAL-REVIEW.md to GPT for final review.
**Blocking:** Yes — no closure without GPT final + Claude assessment.
```

**GPT completes a review:**
```
## Next Step
**Produced:** GPT review — PASS with 2 non-blocking notes
**Next actor:** Operator
**Action:** Forward this review to Claude for assessment. If PASS, proceed to operator sign-off.
**Blocking:** No — non-blocking notes can be fixed in parallel.
```

**Claude completes assessment:**
```
## Next Step
**Produced:** Claude assessment — PASS, 0 blocking
**Next actor:** Operator
**Action:** Grant closure_status=closed. Then start Sprint N+1 kickoff.
**Blocking:** Yes — operator sign-off required before next sprint.
```

### Why This Matters

Without handoff blocks:
- Operator must remember who does what next
- Deliverables sit idle waiting for someone to notice
- GPT review gets delayed because nobody told operator to send it
- Copilot finishes mid-point but doesn't trigger the review

With handoff blocks:
- Every output is self-routing
- Operator just follows the `Next Step` instruction
- No deliverable sits orphaned

---

## Patch 2: Explicit Report Task (R-04 fix)

### Rule: `{N}.REPORT` is a mandatory task in every sprint.

Add to task list between last implementation task and `{N}.FINAL`:

```
| {N}.REPORT | Draft final review report | S | Copilot | All impl tasks |
```

**Trigger:** When `implementation_status=done`, Copilot produces the report draft immediately — not when operator asks.

**Report draft goes to:** `docs/sprints/sprint-{N}/SPRINT-{N}-FINAL-REVIEW.md`

**Handoff:**
```
## Next Step
**Produced:** SPRINT-{N}-FINAL-REVIEW.md draft
**Next actor:** Operator
**Action:** Send to GPT for final review.
**Blocking:** Yes — GPT review requires this report.
```

### Same for mid-review:

Copilot produces `SPRINT-{N}-MID-REVIEW.md` when first-half tasks complete. Handoff block tells operator to send to GPT.

---

## Patch 3: Claude Mid-Assessment Task (R-02 fix)

### Rule: `{N}.CLAUDE-MID` exists alongside `{N}.MID` (GPT).

Claude is not passive during sprints. Add:

```
| {N}.CLAUDE-MID | Claude mid-sprint assessment | — | Claude | Same dependency as {N}.MID |
```

**What Claude checks at mid-sprint:**
- Contract drift from task breakdown
- Living document (Implementation Notes) up to date
- Evidence checklist progress
- Decision compliance (frozen decisions honored)
- Bridge rule (mutation sprints)

**Can run in parallel with GPT mid-review.** Both must PASS before second-half tasks.

**Handoff:**
```
## Next Step
**Produced:** Claude mid-assessment — [PASS/FAIL]
**Next actor:** Operator
**Action:** If both GPT mid-review and Claude mid-assessment PASS, authorize second-half tasks to Copilot.
**Blocking:** Yes — both gates must pass.
```

---

## Patch 4: Frontend Task Splitting Rule (R-01 fix)

### Rule: Frontend tasks split into "shared component" and "page integration."

When a sprint has frontend work:
- **Shared component task:** Create reusable component (ConfirmDialog, useMutation, etc.) → 1 commit
- **Page integration task(s):** Wire component into specific pages → 1 commit per page or page group

**Example for Sprint 11 (what it should have been):**
```
11.7  ConfirmDialog + useMutation (shared)     → commit A
11.8  ApprovalsPage integration                  → commit B
11.9  MissionDetailPage integration              → commit C
11.10 Feedback polish (toast, spinner states)    → commit D
```

Not: `11.7+11.8+11.9+11.10 → single commit`

---

## Patch 5: Automated Test Count in Closure Script (R-03 fix)

### Rule: Closure script parses and reports test count from raw output.

Add to `sprint-closure-check.sh`:

```bash
# After pytest run:
BACKEND_COUNT=$(python -m pytest tests/ --co -q 2>/dev/null | tail -1 | grep -oP '\d+')
log "Backend test count (collected): $BACKEND_COUNT"

# After vitest run:
FRONTEND_COUNT=$(npx vitest list 2>/dev/null | wc -l)
log "Frontend test count (collected): $FRONTEND_COUNT"

TOTAL=$((BACKEND_COUNT + FRONTEND_COUNT))
log "Total test count: $TOTAL (backend $BACKEND_COUNT + frontend $FRONTEND_COUNT)"
```

**Rule:** Report and closure summary MUST use these numbers. No manual arithmetic. If report says "224" but script says "213", script wins (source hierarchy: raw output > report narrative).

**Stop rule (3rd offense):** If test count arithmetic is wrong for a third consecutive sprint, closure script must auto-fail when report count doesn't match collected count.

---

## Patch 6: Sprint Folder Structure (R-05 fix)

### Rule: All new sprints use `docs/sprints/sprint-{N}/` from Sprint 12 onward.

```
docs/sprints/sprint-12/
├── README.md                           # Sprint index: goal, file list, status, open decisions
├── SPRINT-12-TASK-BREAKDOWN.md
├── SPRINT-12-KICKOFF-GATE.md
├── SPRINT-12-MID-REVIEW.md
├── SPRINT-12-FINAL-REVIEW.md
├── SPRINT-12-RETROSPECTIVE.md
├── SPRINT-12-CLOSURE-SUMMARY.md
└── artifacts/                          # Raw outputs — never mixed with narrative docs
    ├── closure-check-output.txt
    ├── contract-evidence.txt
    ├── e2e-output.txt
    ├── lighthouse.txt
    ├── live-checks.txt
    └── review-final.md
```

**Rule:** Narrative docs (`.md` with SPRINT- prefix) live at sprint folder root. Raw outputs and validation artifacts live under `artifacts/`. Never mix them at the same level.

Sprint 11 existing files stay in `evidence/sprint-11/` — full migration happens in Sprint 13 with an explicit migration map (see A-12).

---

## Updated Sprint Lifecycle with Handoffs

Full lifecycle with handoff blocks at each transition:

```
┌─────────────────────────────────────────────────────┐
│ KICKOFF GATE                                        │
│ Claude produces: task breakdown + kickoff gate       │
│ ► Next: Operator sends to GPT for pre-sprint review │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ GPT PRE-SPRINT REVIEW                               │
│ GPT produces: review verdict                         │
│ ► Next: Operator authorizes Copilot to start impl   │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ FIRST HALF TASKS (Copilot)                          │
│ 1 task = 1 commit, evidence per task                │
│ Copilot produces: mid-review report draft            │
│ ► Next: Operator sends to GPT + Claude for mid-gate │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ MID GATE (GPT + Claude parallel)                    │
│ GPT: contract drift, security, lifecycle             │
│ Claude: living doc, evidence checklist, decisions    │
│ Both produce: review verdicts                        │
│ ► Next: Operator authorizes second-half tasks        │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ SECOND HALF TASKS (Copilot)                         │
│ Frontend, integration, operator drill                │
│ Copilot produces: final review report draft          │
│ ► Next: Operator sends to GPT for final review      │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ CLOSURE SCRIPT (Copilot)                            │
│ sprint-closure-check.sh → evidence files             │
│ ► Next: Operator sends report to GPT final review   │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ FINAL GATE (GPT review + Claude assessment)         │
│ GPT: full review against report + evidence           │
│ Claude: architecture + governance assessment         │
│ Both produce: verdicts                               │
│ ► Next: Operator grants closure_status=closed        │
└──────────────────────┬──────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│ OPERATOR SIGN-OFF                                   │
│ closure_status=closed                                │
│ ► Next: Start Sprint N+1 kickoff                    │
└─────────────────────────────────────────────────────┘
```

---

## Updated Task Template (Sprint 12+)

Standard sprint task list now includes these mandatory tasks:

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

**Notes:**
- `{N}.RETRO` is NOT optional. It must exist as a task and produce at least one actionable output (decision, patch, rule, or carried task).
- `{N}.CLOSURE` is NOT the operator sign-off. It is the summary document that the operator reviews before granting `closure_status=closed`.
- `{N}.REPORT` handoff: "Operator: send to GPT for final review."
- `{N}.CLOSURE` handoff: "Operator: review and grant closure_status=closed."

---

## Summary: What Changes

| # | Change | Source | Applies From |
|---|--------|--------|-------------|
| P-01 | Handoff protocol: every deliverable ends with Next Step block | User directive | Sprint 12 |
| P-02 | `{N}.REPORT` mandatory task (proactive report) | R-04 + User directive | Sprint 12 |
| P-03 | `{N}.CLAUDE-MID` task (Claude not passive) | R-02 | Sprint 12 |
| P-04 | Frontend task splitting: component vs page integration | R-01 | Sprint 12 |
| P-05 | Closure script auto-parses test count | R-03 | Sprint 12 |
| P-06 | `docs/sprints/sprint-{N}/` with `artifacts/` subfolder | R-05 + User directive + GPT patch | Sprint 12 |
| P-07 | `{N}.MID-REPORT` mandatory before mid-review | User directive | Sprint 12 |
| P-08 | `{N}.RETRO` + `{N}.CLOSURE` as explicit tasks | GPT patch | Sprint 12 |
| P-09 | Sprint folder README.md mandatory | GPT A-11 | Sprint 12 |
| P-10 | Migration map before Sprint 13 refactor | GPT A-12 | Sprint 13 Task 0 |

---

## Patch 7: Sprint Folder README Rule (GPT A-11)

Every sprint folder must have a `README.md` containing:

```markdown
# Sprint {N} — [Title]
**Status:** implementation_status / closure_status
**Goal:** [one sentence]

## Files
| File | Purpose |
|------|---------|
| SPRINT-{N}-TASK-BREAKDOWN.md | Plan + results |
| ... | ... |
| artifacts/ | Raw evidence outputs |

## Open Decisions
- [list or "none"]

## Closure Prerequisites
- [list]
```

This is the entry point. Open the folder, read README, know everything.

---

## Patch 8: Migration Model — Containment Then Full Migration

### Sprint 12 (Containment)
- All NEW sprint material goes to `docs/sprints/sprint-12/` + `artifacts/`
- Existing Sprint 7-11 files stay where they are (`evidence/sprint-{N}/`, `docs/ai/`, etc.)
- No silent moves during Sprint 12
- closure-check.sh updated to read from new path for Sprint 12+

### Sprint 13 (Full Migration)
- Task 0: produce migration map table

| Current Path | Target Path | Action | Impact |
|-------------|-------------|--------|--------|
| `evidence/sprint-11/*.txt` | `docs/sprints/sprint-11/artifacts/` | Move | Update closure script path check |
| `evidence/sprint-10/*.txt` | `docs/sprints/sprint-10/artifacts/` | Move | Historical only |
| `docs/ai/PROCESS-GATES.md` | `docs/shared/PROCESS-GATES.md` | Move | Update all references |
| `docs/ai/DECISION-DEBT-BURNDOWN.md` | `docs/shared/` | Move | Update references |
| `docs/ai/SPRINT-12-CLOSURE-GATE.md` | `docs/sprints/sprint-12/` | Move | Sprint-specific |
| Old phase reports | `archive/stale/` or respective sprint folder | Move/Archive | Stale quarantine |

- No file moves without this table approved
- Every moved file: grep for old path, update references
- Verify closure script works after migration

---

## Retrospective Carry-Over Actions (GPT-originated)

| # | Action | Owner | Target | Output |
|---|--------|-------|--------|--------|
| A-10 | Sprint folder hygiene: narrative docs at root, raw outputs under `artifacts/` | Claude | Sprint 12 Task 0 + PROCESS-GATES | Folder rule |
| A-11 | Every sprint folder must have README.md (goal, file list, status, open decisions) | Copilot | Sprint 12 kickoff | Template |
| A-12 | Migration map before Sprint 13 refactor (current/target/action/impact table) | Claude | Sprint 13 Task 0 | Migration table |

---

## `docs/shared/` Promotion Rule (Strengthened per GPT)

A note is promoted to `docs/shared/` only if ALL of:
1. Referenced by 2+ sprints
2. Governance-relevant or architecture-relevant
3. Observed in 2+ retrospectives

Every shared note must carry:
- **Owner** — who maintains it
- **Source sprint** — where it originated
- **Last reviewed** — date of last relevance check
- **Sunset condition** — when to archive it

Review at each phase closure: stale shared notes archived or removed.

---

## Next Step

**Produced:** Process Patch v4 with 7 improvements (handoff protocol, report tasks, Claude mid-assessment, frontend splitting, auto test count, folder structure, mid-report task)
**Next actor:** Operator
**Action:** Review this patch. If approved, send to GPT for validation. Then apply to PROCESS-GATES.md and Sprint 12 task breakdown before kickoff.
**Blocking:** Yes — Sprint 12 kickoff gate should include these rules.
