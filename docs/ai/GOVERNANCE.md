# Governance — Vezir Platform

**Effective:** Sprint 12+ (consolidated Sprint 18, D-112)
**Owner:** Operator (AKCA)

---

## 1. Source Hierarchy

When sources conflict, precedence order:

1. Repo code (actual behavior)
2. Raw evidence outputs (test/curl/grep output)
3. Frozen decisions (D-XXX in DECISIONS.md)
4. Sprint task breakdown
5. Sprint report narrative
6. Chat summary / stale snapshot (reference only)

---

## 2. Sprint Status Model

Every sprint carries two mandatory fields:

| Field | Values | Who Sets It |
|-------|--------|-------------|
| `implementation_status` | `not_started` / `in_progress` / `done` | Claude |
| `closure_status` | `not_started` / `evidence_pending` / `review_pending` / `closed` | `closed` only by Operator |

**Banned terms:** COMPLETE, CODE-COMPLETE, PARTIAL. Use the two-axis model only.

---

## 3. Closure Models (D-105)

| Model | Evidence | Gates | Waivers |
|-------|----------|-------|---------|
| **A** (full) | Sprint-time only | All executed | None unless pre-approved |
| **B** (lightweight) | Retroactive acceptable | Gate waivers documented | Allowed with record |

Operator selects model at kickoff. Max 2 consecutive Model B sprints.

---

## 4. Sprint Kickoff Gate

All checked before code is written:

- [ ] Previous sprint `closure_status=closed`
- [ ] Open decisions max 2
- [ ] Task breakdown frozen with evidence checklist
- [ ] GPT pre-sprint review PASS

---

## 5. Review Gates

```
Pre-sprint:   GPT review MANDATORY → PASS → implementation starts
Mid-sprint:   GPT mid-review → PASS → second-half tasks start
Final:        GPT final review → PASS → eligible for operator close
```

Review verdicts stored in `docs/ai/reviews/S{N}-REVIEW.md`.
Verdict definitions: PASS (eligible for close), HOLD (patches required), FAIL (re-scope).

---

## 6. Task DONE Definition

A task is DONE when 5/5:

1. Code committed (1 task = 1 commit minimum)
2. Related tests passing
3. Evidence produced
4. Implementation Notes updated (same day)
5. File Manifest updated

---

## 7. Evidence Standard

Evidence directory: `docs/sprints/sprint-{N}/artifacts/`

Mandatory: `closure-check-output.txt` (pytest + vitest + tsc + lint).
Sprint-specific: as defined in kickoff doc.

Test counts from raw command output only. No manual counting.

---

## 8. Commit Rule

```
1 task = minimum 1 commit
Format: "Sprint N Task X.Y: <description>"
Push at sprint end
Mega-commit (3+ unrelated tasks in one commit) forbidden
```

---

## 9. Test Hygiene

- `collect_ignore` forbidden
- `sys.exit()` in test file = sprint blocker
- Real test count = `pytest --co -q | tail -1`
- Hidden test = governance violation

---

## 10. Retrospective Gate

- Missing retrospective → `closure_status=closed` cannot be set
- Same error repeating across 3 consecutive sprints → stop rule created

---

## 11. Archive Rule (D-113)

- Active sprints in `docs/sprints/`: last closed + current only
- Historical sprints → `docs/archive/sprints/`
- Superseded process docs → `docs/archive/process-history/`
- One truth per topic. Duplicates archived or deleted.

---

## 12. Proposal Format

Every substantial proposal:

1. Current State — reference STATE.md
2. Goal
3. Assumptions / Constraints
4. Proposed Changes — concrete file/code changes
5. Risks
6. Validation Plan

---

## 13. Cross-Review Protocol

- GPT comments: never ignored, never treated as truth without verification
- Every comment: applied, rejected with reason, or deferred with tracking
- Applied fixes reference review round (e.g., "GPT-1 fix applied")

---

## 14. Reopening Frozen Decisions

Requires: identify which decision, provide evidence, get operator approval, update DECISIONS.md. No silent drift. No temporary exceptions.

---

## 15. Technical Standards

- Scripts, logs, commands: English/ASCII only
- All persistent state in repo files, not chat history
- Atomic writes: temp → fsync → os.replace()

---

## 16. Sprint Closure Checklist (Mandatory, Autonomous)

Every sprint closure MUST execute ALL steps below without waiting for operator reminders.
Skipping any step = governance violation. No step is optional.

```
 1. Tests pass          — pytest + vitest + tsc (all green)
 2. Lint pass           — ruff check . (0 errors)
 3. SDK sync            — python tools/export_openapi.py && cd frontend && npm run generate:api
 4. Git commit + push   — all files staged, pushed to main
 5. CI green            — gh run list, wait for success
 6. Issues close        — gh issue close for all sprint issues
 7. Milestone close     — gh api milestones PATCH state=closed
 8. Board sync          — Project V2: Sprint field + Status=Done for all items
 9. STATE.md            — sprint count, phase, test evidence row
10. NEXT.md             — new sprint entry at top
11. Handoff current.md  — full session handoff with deliverables + GPT memo
12. open-items.md       — carry-forward resolved items, next sprint candidates
13. BACKLOG.md          — python tools/generate-backlog.py (regenerate from GitHub)
14. Review file         — docs/ai/reviews/S{N}-REVIEW.md (verdict + evidence)
15. Closure evidence    — docs/sprints/evidence/sprint-{N}/closure-check-output.txt
16. README badges       — test counts + phase current? fix if stale
17. Claude memory       — update project status memory
18. GPT memo            — send session memo to GPT Vezir (browser or text)
```

All 18 steps executed in one pass. Never ask operator "shall I do X?" — just do it.

---

*Governance — Vezir Platform*
*Consolidated from PROCESS-GATES.md + PROTOCOL.md (D-112)*
