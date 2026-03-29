# Sprint 33 — Governance Fix: Project V2 Contract Hardening

**Date:** 2026-03-28
**Phase:** 7
**Model:** A
**Owner:** AKCA
**Prepared by:** Claude (Architect)
**Review chain:** GPT sustainability review (HOLD) → Claude architect review → GPT re-review (HOLD, 6 patches) → This revision

---

# Part 1: Revised Decision Drafts

---

## D-123: Project Item Contract v1

**ID:** D-123
**Title:** Project V2 Item Contract — Canonical Truth Definition
**Status:** proposed → pending operator freeze
**Phase:** Sprint 33

### Context

Project V2 board has 57 items across 6 custom fields. Field doluluk: Status 100%, Sprint 72%, Type/Track/Task ID/PR Link 4% each. Only Status has a reliable automation writer (status-sync.yml). GPT sustainability review identified 7 blocking findings. Claude review added 3 more. Both reviewers agree: the field contract is too broad and unenforceable.

### Decision

#### Canonical Item Contract (validator enforces)

| Truth | Source | Writer | Scope | Enforcement |
|-------|--------|--------|-------|-------------|
| **Project Status** | Project V2 field | `status-sync.yml` (PR events) | All items | Blank = FAIL |
| **Sprint identity** | Project V2 `Sprint` text field | `issue-from-plan.yml` sets at creation; validator checks format | Sprint tasks | Regex `^\d+$`; blank on sprint-labeled item = FAIL |
| **Priority** | GitHub label (`priority:P1/P2/P3`) | `backlog-import.py` for backlog; `issue-from-plan.yml` for sprint tasks | Backlog items (mandatory), sprint tasks (optional) | Backlog item without priority label = FAIL |
| **Task ID** | Issue title pattern `[SN-N.M]` | `issue-from-plan.yml` generates title | Sprint tasks only | Sprint-labeled item without `[SN-N.M]` title = FAIL |
| **Issue State** | GitHub issue open/closed | Operator or automation at closure | All items | Done + open = FAIL; closed sprint + open issue = FAIL |
| **Milestone** | GitHub milestone | `issue-from-plan.yml` assigns | Sprint tasks | Sprint task without milestone = WARN (v1), FAIL (v2) |

#### Non-canonical (not enforced, not closure truth)

| Field | Disposition | Rationale |
|-------|------------|-----------|
| **Type** (project field) | Keep as-is, non-canonical | API cannot reliably add options; labels (`backlog`, `sprint`, `gate`, `process`) serve type role |
| **Track** | Keep as-is, optional | 2/57 populated; useful for future swimlane but not proven |
| **PR Link** | Keep as-is, display only | Derived from GitHub closing refs; manual field is not closure truth |

#### Write Authority Rule

Every canonical truth must have an identified automation writer. A truth with no automation writer cannot be in the canonical contract. If a new field is proposed, the proposal must name the writer before the field enters the contract.

#### Sprint Identity — Two-Phase Approach

- **v1 (Sprint 33):** Sprint text field stays. Validator enforces `^\d+$` regex. `issue-from-plan.yml` sets value at creation. Milestone also assigned as belt-and-suspenders.
- **v2 (future, requires separate decision):** If milestone-based filtering, views, and reporting prove equivalent to Sprint field, Sprint text field may be retired. This requires evidence from at least 2 sprints of dual-mode operation.

Milestone-only transition is NOT frozen in this decision. It is a future option contingent on proven parity.

#### Sprint 0 / Backlog Model

`Sprint 0` convention stays for backlog items. Backlog items have Sprint = 0 (or blank, validator accepts both for backlog-labeled items). Sprint/backlog separation: `backlog` label = backlog item, `sprint` label = sprint task. Both can coexist on board without conflict.

### Trade-off

| Accepted | Deferred |
|----------|----------|
| Enforceable contract with 5 canonical truths | Full field normalization across all 57 items |
| Type/Track/PR Link kept but non-canonical | Type field cleanup (separate migration if ever needed) |
| Sprint text field retained (regex-validated) | Milestone-only transition (future evidence-gated) |

### Impacted Files

| File | Change |
|------|--------|
| `tools/project-validator.py` | New — enforces this contract |
| `tools/sprint-closure-check.sh` | Patch — call project-validator |
| `docs/shared/PROJECT-SETUP.md` | Update — canonical vs non-canonical fields |
| `docs/ai/DECISIONS.md` | Add D-123 |

### Validation

- project-validator.py runs on all 57 items
- All canonical truths checked per scope rules
- 0 false positives on S32 items (fully compliant)
- Known failures on legacy items handled by D-124

### Rollback

If regex validation on Sprint field causes friction, relax to WARN for 1 sprint, then re-evaluate. Non-canonical fields can be promoted with a new decision if proven valuable.

---

## D-124: Legacy Normalization Boundary

**ID:** D-124
**Title:** Legacy Item Normalization Policy
**Status:** proposed → pending operator freeze
**Phase:** Sprint 33

### Context

16 issues from S20/S23/S24 exist on the Project V2 board without Sprint field values. These predate the D-122 contract (Sprint 31). Full backfill of all fields is expensive and yields no operational value.

### Decision

#### Normalization Scope

Legacy items (pre-S31 contract) receive minimum normalization:

1. **Sprint field backfill:** Set Sprint = correct number (20, 23, or 24) based on milestone or issue creation context
2. **Milestone assignment:** Create milestones for S20, S23, S24 if missing; assign to respective issues
3. **Status correction:** Verify issue state matches Project Status; fix mismatches
4. **Close resolved issues:** #100 and any other resolved-but-open items

Legacy items DO NOT require: Task ID backfill, Type/Track/PR Link population, or any field that did not exist at creation time.

#### Item Classification (Validator Taxonomy)

Every item on the board must fall into exactly one class. Unknown is not legacy.

| Class | Detection Rule | Validator Behavior |
|-------|---------------|-------------------|
| **Backlog** | Has `backlog` label | Enforce: Status, Priority label, Issue State |
| **Sprint task (current contract)** | Has `sprint` label AND milestone ≥ S31 | Enforce: full canonical contract |
| **Legacy sprint task** | Has `sprint` label AND milestone < S31 (or Sprint field < 31) | Enforce: Status, Sprint field, Issue State. WARN on missing Task ID. |
| **Normalized legacy** | Has milestone for S20/S23/S24 AND Sprint field set (after normalization) | Same as legacy sprint task |
| **Unclassified** | None of the above | **FAIL — manual review required** |

**Critical rule:** `Unclassified` is always FAIL, never SKIP. If an item cannot be classified, it is a board integrity problem that must be resolved before the validator can pass. This prevents new broken items from silently entering the board under a legacy exception.

#### Normalization Execution

```bash
# Step 1: Create missing milestones
gh api repos/{owner}/{repo}/milestones -f title="Sprint 20" -f state=closed
gh api repos/{owner}/{repo}/milestones -f title="Sprint 23" -f state=closed
gh api repos/{owner}/{repo}/milestones -f title="Sprint 24" -f state=closed

# Step 2: Assign milestones to 16 legacy items (per-issue)
# Step 3: Set Sprint field via project GraphQL mutation
# Step 4: Close #100 and other resolved-but-open items
# Step 5: Run project-validator.py — expect 0 unclassified
```

### Trade-off

| Accepted | Deferred |
|----------|----------|
| Minimum normalization (Sprint + Status + Issue State) | Full field backfill for legacy |
| Explicit classification taxonomy | Type/Track cleanup on legacy |
| Unclassified = FAIL (no silent bypass) | Historical completeness |

### Impacted Files

| File | Change |
|------|--------|
| `tools/project-validator.py` | Classification taxonomy + legacy rules |
| `docs/shared/PROJECT-SETUP.md` | Legacy normalization policy |
| `docs/ai/DECISIONS.md` | Add D-124 |

### Validation

- 16 legacy items: Sprint field populated, milestone assigned
- #100 closed
- 0 unclassified items on board
- project-validator.py PASS on full board

### Rollback

If legacy normalization causes unexpected issues, revert Sprint field values and milestones. Classification taxonomy in validator is code-level and easily adjustable.

---

## D-125: Closure State Sync Rule

**ID:** D-125
**Title:** Closure State Sync — Triple Consistency + Backlog Evidence Rule
**Status:** proposed → pending operator freeze
**Phase:** Sprint 33

### Context

Sprint 32 delivered B-005 (#154) and B-012 (#153) but backlog issues remain open. #100 is resolved but open. Pattern: sprint closure does not propagate to issue/board state.

### Decision

#### Triple Consistency Rule

For every sprint task in a closed sprint, ALL THREE must be true simultaneously:

1. **Issue state** = closed
2. **Project Status** = Done
3. **Sprint identity** = correct sprint number (field or milestone)

Any single mismatch = validator FAIL. No exceptions.

#### Backlog Closure Rule

A backlog issue may be closed when ALL of:

1. All linked sprint tasks are Done + closed
2. At least one merged PR references the backlog issue (evidence of code delivery)
3. Relevant tests pass (CI green on merge commit)
4. Operator confirms acceptance (explicit comment or sprint closure sign-off covers linked items)

If conditions 1-3 are met but operator has not reviewed, backlog issue stays open with status note. Validator flags as WARN ("eligible for closure, pending operator review").

Backlog issues are NEVER auto-closed by automation. Operator or delegated operator (GPT) makes the close decision.

#### Forbidden States

| State | Rule |
|-------|------|
| Resolved but open | FAIL — close the issue or revert resolution |
| Done on board but open as issue | FAIL — close issue or revert Status |
| Closed issue but not Done on board | FAIL — set Status to Done or reopen issue |
| Sprint task in closed sprint but issue open | FAIL — close issue |
| Backlog issue closed without merged PR evidence | FAIL — reopen or provide evidence |

#### Enforcement

- `project-validator.py` checks all consistency rules
- Validator runs at: sprint closure (mandatory gate), next sprint kickoff (belt-and-suspenders)
- Backlog closure check: validator lists "eligible for closure" items at sprint end

### Trade-off

| Accepted | Deferred |
|----------|----------|
| Triple consistency is hard gate | Automated backlog closure |
| Backlog closure requires operator judgment | Full cross-sprint dependency tracking |
| Evidence = merged PR + CI green | Acceptance testing framework |

### Impacted Files

| File | Change |
|------|--------|
| `tools/project-validator.py` | Triple consistency + backlog closure checks |
| `tools/sprint-closure-check.sh` | Call project-validator as sub-check |
| `docs/ai/DECISIONS.md` | Add D-125 |

### Validation

- Run validator on S32: expect #153 and #154 flagged (done but open)
- Fix: close both, verify Done status
- Re-run: expect PASS
- Run on #100: expect flagged (resolved but open)

### Rollback

Process rule — no code to roll back. If triple consistency proves too strict, relax individual checks to WARN with explicit waiver doc.

---

# Part 2: Sprint 33 Task Breakdown

---

## Sprint 33 — Project V2 Contract Hardening

**Sprint:** 33
**Phase:** 7
**Title:** Project V2 Contract Hardening
**Model:** A
**Goal:** Freeze canonical item contract, normalize legacy items, build validator, integrate into closure gate. No field removal, no UI config changes, no product features.

---

### Task 33.1 — Decision freeze: D-123 / D-124 / D-125

Freeze all three decisions in DECISIONS.md. Create formal records under `docs/decisions/`.

**Branch:** `sprint-33/t33.1-decision-freeze`
**Depends on:** Operator approval of this document

**Deliverables:**
- `docs/decisions/D-123-project-item-contract.md`
- `docs/decisions/D-124-legacy-normalization.md`
- `docs/decisions/D-125-closure-state-sync.md`
- `docs/ai/DECISIONS.md` index updated

**Acceptance:**
1. D-123/D-124/D-125 status = frozen in DECISIONS.md
2. Each decision has formal record file
3. No open questions remaining in decision text

---

### Task 33.2 — Legacy normalization + drift closure

Execute the normalization defined in D-124.

**Branch:** `sprint-33/t33.2-legacy-normalize`
**Depends on:** 33.1

**Implementation:**
1. Create milestones: Sprint 20, Sprint 23, Sprint 24 (state: closed)
2. Assign milestones to 16 legacy items
3. Set Sprint field via GraphQL mutation for 16 items
4. Close #100 (resolved but open)
5. Close #153 and #154 (B-005/B-012 delivered in S32)
6. Regenerate BACKLOG.md (`python tools/generate-backlog.py`)
7. Verify: 0 unclassified items, 0 state drift

**Acceptance:**
1. 16 legacy items have Sprint field + milestone
2. #100, #153, #154 closed
3. BACKLOG.md reflects 35 open / 4 closed
4. `gh issue list --label backlog --state open --json number | jq length` = 35

**Verification:**
```bash
# Check legacy items
gh api graphql -f query='...' # (query Sprint field for S20/S23/S24 items)

# Check closure
gh issue view 100 --json state --jq .state  # expect CLOSED
gh issue view 153 --json state --jq .state  # expect CLOSED
gh issue view 154 --json state --jq .state  # expect CLOSED

# Regenerate + verify
python tools/generate-backlog.py
grep -c "Open" docs/ai/BACKLOG.md
```

---

### Task 33.3 — project-validator.py

Build the validator defined in D-123/D-124/D-125.

**Branch:** `sprint-33/t33.3-project-validator`
**Depends on:** 33.1

**Implementation:**
1. Create `tools/project-validator.py`
2. Item classification: backlog / sprint-task / legacy-sprint / normalized-legacy / unclassified
3. Canonical truth checks per D-123:
   - Status blank → FAIL
   - Sprint-labeled item without Sprint field → FAIL
   - Sprint field format invalid (not `^\d+$`) → FAIL
   - Backlog item without priority label → FAIL
   - Sprint task without `[SN-N.M]` title → FAIL (S31+), WARN (legacy)
   - Sprint task without milestone → WARN (v1)
   - Unclassified item → FAIL
4. State sync checks per D-125:
   - Done + open issue → FAIL
   - Closed sprint + open issue → FAIL
   - Closed issue + not Done → FAIL
   - Backlog eligible for closure → WARN (info)
5. Output: `VALID` or `NOT VALID` with failure list
6. Exit code: 0 = valid, 1 = not valid
7. JSON output option for CI consumption

**Fail taxonomy (per GPT P6):**

| Code | Description | Severity |
|------|-------------|----------|
| `BLANK_STATUS` | Project Status empty | FAIL |
| `INVALID_SPRINT_FORMAT` | Sprint field not `^\d+$` | FAIL |
| `MISSING_SPRINT` | Sprint-labeled item, no Sprint value | FAIL |
| `MISSING_PRIORITY` | Backlog item without priority label | FAIL |
| `MISSING_TASK_ID` | S31+ sprint task without `[SN-N.M]` title | FAIL |
| `LEGACY_MISSING_TASK_ID` | Pre-S31 sprint task without pattern | WARN |
| `MISSING_MILESTONE` | Sprint task without milestone | WARN |
| `DONE_BUT_OPEN` | Status=Done, issue open | FAIL |
| `CLOSED_SPRINT_OPEN_ISSUE` | Closed sprint, issue open | FAIL |
| `CLOSED_NOT_DONE` | Issue closed, Status≠Done | FAIL |
| `UNCLASSIFIED` | Cannot determine item class | FAIL |
| `BACKLOG_CLOSURE_ELIGIBLE` | All linked tasks done, PR merged | INFO |

**Acceptance:**
1. Validator runs on full board (57 items)
2. S32 items: 0 failures (after 33.2 normalization)
3. Legacy items: 0 FAIL, acceptable WARNs
4. Backlog items: 0 FAIL
5. At least 1 test for each fail code

**Verification:**
```bash
python tools/project-validator.py
python tools/project-validator.py --json
python -m pytest tests/test_project_validator.py -v
```

---

### 33.G1 — Mid Review Gate

After 33.1 + 33.2 + 33.3. Branch-exempt.

**Checks:**
- D-123/D-124/D-125 frozen
- Legacy normalization complete (0 unclassified)
- Validator runs without crash, produces correct output
- Writer matrix in D-123 matches actual automation code

---

### Task 33.4 — sprint-closure-check.sh integration

Integrate project-validator into the existing closure gate.

**Branch:** `sprint-33/t33.4-closure-integration`
**Depends on:** 33.G1

**Implementation:**
1. Add `project-validator.py` call to `sprint-closure-check.sh`
2. Validator FAIL → closure check FAIL (mandatory)
3. Validator WARN → closure check logs but does not fail
4. Update PROJECT-SETUP.md with canonical vs non-canonical field documentation

**Acceptance:**
1. `sprint-closure-check.sh 33` calls project-validator
2. Validator FAIL blocks closure
3. PROJECT-SETUP.md updated

**Verification:**
```bash
bash tools/sprint-closure-check.sh 33
```

---

### Task 33.5 — Writer matrix documentation + DECISIONS.md update

Document the write authority matrix as permanent reference.

**Branch:** `sprint-33/t33.5-writer-matrix`
**Depends on:** 33.G1

**Implementation:**
1. Add writer matrix table to `docs/shared/PROJECT-SETUP.md`
2. Update `docs/ai/DECISIONS.md` with D-123/D-124/D-125 summaries
3. Update `docs/ai/STATE.md` with Sprint 33 entry + decision count (125)
4. Update `docs/ai/handoffs/current.md`

**Acceptance:**
1. Writer matrix in PROJECT-SETUP.md
2. DECISIONS.md index has D-123/D-124/D-125
3. STATE.md current

---

### 33.G2 — Final Review Gate

Full evidence: validator output + closure-check output + legacy normalization proof + decision records.

### 33.RETRO — Retrospective

Key questions: Is the validator catching real drift? Is the classification taxonomy complete? Is Sprint text field + milestone dual-mode causing friction?

### 33.CLOSURE — Sprint Closure

---

## Evidence Checklist

| # | Evidence | Command / Location |
|---|----------|--------------------|
| 1 | D-123 frozen | `docs/decisions/D-123-project-item-contract.md` |
| 2 | D-124 frozen | `docs/decisions/D-124-legacy-normalization.md` |
| 3 | D-125 frozen | `docs/decisions/D-125-closure-state-sync.md` |
| 4 | Legacy normalization | `gh issue list` showing Sprint/milestone on S20/S23/S24 items |
| 5 | #100 closed | `gh issue view 100 --json state` |
| 6 | #153 closed | `gh issue view 153 --json state` |
| 7 | #154 closed | `gh issue view 154 --json state` |
| 8 | BACKLOG.md regenerated | `docs/ai/BACKLOG.md` header timestamp |
| 9 | Validator output (full board) | `python tools/project-validator.py` |
| 10 | Validator tests pass | `python -m pytest tests/test_project_validator.py -v` |
| 11 | Closure check integration | `bash tools/sprint-closure-check.sh 33` |
| 12 | Backend tests unchanged | `cd agent && python -m pytest tests/ --co -q \| tail -1` |
| 13 | Frontend tests unchanged | `cd frontend && npx vitest run` |
| 14 | Writer matrix documented | `docs/shared/PROJECT-SETUP.md` |
| 15 | STATE.md updated | `docs/ai/STATE.md` |

---

## Anti-Scope-Creep

- NO Sprint text field removal (future decision, evidence-gated)
- NO Type field removal from Project V2 (non-canonical, stays as-is)
- NO UI configuration changes to Project field options
- NO product features
- NO new backlog items
- NO code changes outside tools/ and docs/

---

## Decisions to Freeze

| ID | Topic | When |
|----|-------|------|
| D-123 | Project Item Contract v1 | Task 33.1 (before any implementation) |
| D-124 | Legacy Normalization Boundary | Task 33.1 |
| D-125 | Closure State Sync Rule | Task 33.1 |

---

## Carry-Forward

| Item | Target |
|------|--------|
| Sprint field → milestone-only migration | Future (requires 2-sprint evidence) |
| Type field cleanup / label migration | Future (if operational need arises) |
| Scheduled mission execution (D-120) | Sprint 34 |
| Template polish (B-103/B-104) | Sprint 34 |
| Approval inbox UI (B-102) | Sprint 34+ |

---

## Output Files

| Task | Output |
|------|--------|
| 33.1 | `docs/decisions/D-123-*`, `D-124-*`, `D-125-*`, DECISIONS.md |
| 33.2 | Milestones, Sprint field values, closed issues, BACKLOG.md |
| 33.3 | `tools/project-validator.py`, `tests/test_project_validator.py` |
| 33.4 | `tools/sprint-closure-check.sh` (patched) |
| 33.5 | `docs/shared/PROJECT-SETUP.md`, STATE.md, handoff |
