# Sprint 33 — Claude Code Execution Brief

**Sprint:** 33
**Phase:** 7
**Model:** A
**Operator approval:** 2026-03-28 — PASS (GPT pre-sprint PASS, operator approved)
**Execution sequence:** 33.1 → 33.2 → 33.3 → G1 → 33.4 → 33.5 → G2 → RETRO → CLOSURE

---

## Context

Sprint 33 is a governance-fix sprint. No product features, no UI changes, no code outside `tools/` and `docs/`. Goal: freeze Project V2 canonical contract, normalize legacy board items, build validator, integrate into closure gate.

## Decisions to Freeze (Task 33.1)

### D-123: Project Item Contract v1

Canonical truths (validator enforces):

| Truth | Source | Writer | Scope | Enforcement |
|-------|--------|--------|-------|-------------|
| Project Status | Project V2 field | `status-sync.yml` (PR events); `project-auto-add.yml` sets initial on creation | All items | Blank = FAIL |
| Sprint identity | Project V2 `Sprint` text field | `issue-from-plan.yml` sets at creation | Sprint tasks | Regex `^\d+$`; blank on sprint-labeled = FAIL |
| Priority | GitHub label (`priority:P1/P2/P3`) | `backlog-import.py` for backlog; `issue-from-plan.yml` for sprint | Backlog mandatory, sprint optional | Backlog without priority label = FAIL |
| Task ID | Issue title pattern `[SN-N.M]` | `issue-from-plan.yml` generates | Sprint tasks only | S31+ without pattern = FAIL |
| Issue State | GitHub open/closed | Operator at closure | All items | Done+open = FAIL |
| Milestone | GitHub milestone | `issue-from-plan.yml` assigns | Sprint tasks | Missing = WARN (v1) |

Non-canonical: Type (project field), Track, PR Link — keep as-is, not enforced.

Sprint field stays (v1). Milestone-only = future decision requiring 2-sprint evidence.
Sprint 0 = backlog convention, stays.

### D-124: Legacy Normalization Boundary

Classification taxonomy:

| Class | Rule | Validator |
|-------|------|-----------|
| Backlog | `backlog` label | Enforce: Status, Priority, Issue State |
| Sprint task (S31+) | `sprint` label + milestone ≥ S31 | Full contract |
| Legacy sprint (pre-S31) | `sprint` label + milestone < S31 | Status, Sprint, Issue State. WARN on Task ID |
| Normalized legacy | After backfill (S20/S23/S24) | Same as legacy sprint |
| Unclassified | None of above | **FAIL — never SKIP** |

Normalization: Sprint field + milestone + status fix + close resolved-but-open. No Task ID/Type/Track/PR Link backfill.

### D-125: Closure State Sync Rule

Triple consistency (all FAIL):
1. Issue closed + Status ≠ Done → FAIL
2. Status = Done + issue open → FAIL
3. Closed sprint + issue open → FAIL

Backlog closure requires ALL:
1. All linked sprint tasks done + closed
2. Merged PR referencing backlog issue
3. CI green on merge commit
4. Operator confirms acceptance

`BACKLOG_CLOSURE_ELIGIBLE` = machine-readable JSON output listing eligible items. Never auto-close.

---

## Task Execution

### 33.1 — Decision freeze
**Branch:** `sprint-33/t33.1-decision-freeze`

```bash
# Create decision records
mkdir -p docs/decisions
# Write D-123, D-124, D-125 formal records (from Part 1 of SPRINT-33-FULL-PACKAGE.md)
# Update docs/ai/DECISIONS.md index with D-123/D-124/D-125 summaries
# Commit: "D-123/D-124/D-125: project item contract, legacy normalization, closure sync"
```

### 33.2 — Legacy normalization + drift closure
**Branch:** `sprint-33/t33.2-legacy-normalize`
**Depends on:** 33.1 merged

```bash
# 1. Create closed milestones
gh api repos/{owner}/{repo}/milestones -f title="Sprint 20" -f state=closed
gh api repos/{owner}/{repo}/milestones -f title="Sprint 23" -f state=closed
gh api repos/{owner}/{repo}/milestones -f title="Sprint 24" -f state=closed

# 2. For each of 16 legacy items: assign milestone + set Sprint field via GraphQL
# IMPORTANT: Save raw GraphQL outputs to evidence/sprint-33/ (not placeholders)

# 3. Close drift issues
gh issue close 100 --comment "Resolved in S23, closing per D-125"
gh issue close 153 --comment "B-012 delivered in S32 (idempotency), closing per D-125"
gh issue close 154 --comment "B-005 delivered in S32 (throttling), closing per D-125"

# 4. Regenerate backlog
python tools/generate-backlog.py

# 5. Verify
gh issue list --label backlog --state open --json number | jq length  # expect 35
gh issue view 100 --json state  # CLOSED
gh issue view 153 --json state  # CLOSED
gh issue view 154 --json state  # CLOSED

# Commit: "chore: legacy normalization + close #100/#153/#154 per D-124/D-125"
```

### 33.3 — project-validator.py
**Branch:** `sprint-33/t33.3-project-validator`
**Depends on:** 33.1 merged

Create `tools/project-validator.py` with:
- Item classification (5 classes per D-124)
- Canonical truth checks per D-123
- State sync checks per D-125
- Fail taxonomy (12 codes — see SPRINT-33-FULL-PACKAGE.md Task 33.3)
- `BACKLOG_CLOSURE_ELIGIBLE` as JSON array in output
- `MISSING_MILESTONE` = WARN only (v1, do NOT tighten to FAIL)
- Exit 0 = VALID, Exit 1 = NOT VALID
- `--json` flag for machine-readable output
- Tests in `tests/test_project_validator.py`

```bash
python tools/project-validator.py           # human-readable
python tools/project-validator.py --json    # machine-readable
python -m pytest tests/test_project_validator.py -v
# Commit: "feat: project-validator.py per D-123/D-124/D-125"
```

### 33.G1 — Mid Review Gate
**Checks:**
- [ ] D-123/D-124/D-125 frozen in DECISIONS.md
- [ ] 16 legacy items normalized (Sprint field + milestone)
- [ ] #100, #153, #154 closed
- [ ] Validator runs, correct output on full board
- [ ] Writer matrix matches automation code

### 33.4 — sprint-closure-check.sh integration
**Branch:** `sprint-33/t33.4-closure-integration`
**Depends on:** G1 pass

Patch `tools/sprint-closure-check.sh`:
- Call `python tools/project-validator.py`
- FAIL → closure check FAIL (mandatory)
- WARN → log, don't fail

```bash
bash tools/sprint-closure-check.sh 33
# Commit: "feat: integrate project-validator into closure gate"
```

### 33.5 — Writer matrix + docs
**Branch:** `sprint-33/t33.5-writer-matrix`
**Depends on:** G1 pass

Update:
- `docs/shared/PROJECT-SETUP.md` — writer matrix table, canonical vs non-canonical
- `docs/ai/DECISIONS.md` — D-123/D-124/D-125 index
- `docs/ai/STATE.md` — Sprint 33 entry, decision count = 125
- `docs/ai/handoffs/current.md` — session update

```bash
# Commit: "docs: writer matrix, PROJECT-SETUP, STATE, DECISIONS update"
```

### 33.G2 — Final Review Gate
### 33.RETRO — Retrospective
### 33.CLOSURE — Sprint Closure

---

## Evidence Collection

Save ALL evidence to sprint artifacts directory. Raw outputs, not descriptions.

| # | File | Source |
|---|------|--------|
| 1 | `D-123-record.md` | Decision record |
| 2 | `D-124-record.md` | Decision record |
| 3 | `D-125-record.md` | Decision record |
| 4 | `legacy-normalization-output.txt` | Raw GraphQL mutation outputs |
| 5 | `issue-closure-evidence.txt` | `gh issue view` for #100/#153/#154 |
| 6 | `backlog-regen-output.txt` | `python tools/generate-backlog.py` output |
| 7 | `validator-full-board.txt` | `python tools/project-validator.py` |
| 8 | `validator-full-board.json` | `python tools/project-validator.py --json` |
| 9 | `validator-tests.txt` | `pytest tests/test_project_validator.py -v` |
| 10 | `closure-check-output.txt` | `bash tools/sprint-closure-check.sh 33` |
| 11 | `pytest-output.txt` | `cd agent && python -m pytest tests/ -v` |
| 12 | `vitest-output.txt` | `cd frontend && npx vitest run` |

---

## Hard Rules

1. No field removal from Project V2 UI
2. No product features
3. No code outside `tools/` and `docs/`
4. `MISSING_MILESTONE` stays WARN, not FAIL
5. Evidence = raw outputs saved to file, not placeholders
6. `Unclassified` item = always FAIL, never SKIP
7. Backlog issues never auto-closed
8. `closure_status=closed` is operator-only
