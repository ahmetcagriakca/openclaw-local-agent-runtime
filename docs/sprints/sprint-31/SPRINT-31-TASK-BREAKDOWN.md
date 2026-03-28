# Sprint 31 — Task Breakdown

**Sprint:** 31
**Phase:** 7
**Title:** Backlog-to-Project-to-Sprint Pipeline
**Model:** A

**Goal:** Establish the complete lifecycle: backlog items as GitHub issues → Project V2 board → sprint planning → sprint execution → closure sync. Kill dual-truth (BACKLOG.md vs GitHub).

---

## Track 1: Decision + Import

**31.1 — D-122 Backlog-to-Project-to-Sprint Contract**

Freeze the authority model for backlog management.

**Branch:** `sprint-31/t31.1-backlog-contract`

**Key decisions:**
- Canonical backlog = GitHub issues (not BACKLOG.md)
- BACKLOG.md = generated report only
- Backlog issue != sprint issue (1 backlog → 0..N sprint tasks)
- Sprint container = milestone
- Sprint authority = plan.yaml at freeze time

**Acceptance:** D-122 frozen, no ambiguity in authority model

---

**31.2 — Backlog import tool + initial import**

Import all 35 BACKLOG.md items as GitHub issues. Idempotent — rerun updates, doesn't duplicate.

**Branch:** `sprint-31/t31.2-backlog-import`
**Depends on:** 31.1

**Implementation:**
1. Create `tools/backlog-import.py` — parse BACKLOG.md, create/update GitHub issues
2. Label scheme: `backlog` + `priority:P1`/`priority:P2`/`priority:P3` + domain labels
3. Issue title format: `[B-NNN] Item description`
4. Issue body: description, notes, category, priority
5. Idempotent: detect existing by `[B-NNN]` title prefix
6. Run import → 35 issues created on GitHub
7. Add all to Project V2 board

**Acceptance:** 35 backlog issues on GitHub, all on Project V2, no duplicates on rerun

---

## Gates

**31.G1 — Mid Review Gate**

After Track 1. Branch-exempt.

---

## Track 2: Project + Sprint Wiring

**31.3 — Project V2 field/view normalization**

Configure Project V2 with proper fields and views.

**Branch:** `sprint-31/t31.3-project-fields`
**Depends on:** 31.G1

**Implementation:**
1. Add/configure Project V2 fields: Status (Backlog/Planned/InProgress/Review/Done/Blocked), Priority (P1/P2/P3), Type (Backlog/SprintTask)
2. Create view: "Backlog" — filter by label:backlog, grouped by Priority
3. Create view: "Active Sprint" — filter by current sprint milestone
4. Update project-auto-add.yml to set initial field values

**Acceptance:** Two views working, fields populated for imported items

---

**31.4 — Sprint planning bridge (plan.yaml backlog linkage)**

Update issue-from-plan workflow to link sprint tasks to backlog issues.

**Branch:** `sprint-31/t31.4-sprint-bridge`
**Depends on:** 31.G1

**Implementation:**
1. Add optional `backlog_ref` field to plan.yaml task schema
2. Update issue-from-plan.yml: if backlog_ref present, add "Relates to #N" to sprint issue body
3. Update issue-from-plan.yml: add comment on backlog issue referencing sprint task
4. Test with sample plan.yaml entry

**Acceptance:** Sprint task issues link to backlog issues bidirectionally

---

**31.5 — BACKLOG.md generator + closure sync**

Make BACKLOG.md a generated file from GitHub issues. Define closure sync rules.

**Branch:** `sprint-31/t31.5-backlog-generator`
**Depends on:** 31.G1

**Implementation:**
1. Create `tools/generate-backlog.py` — query GitHub issues with `backlog` label, generate BACKLOG.md
2. Add header: "Auto-generated from GitHub issues. Do not edit directly."
3. Closure sync rule: sprint task closed → check if all linked sprint tasks done → if yes, close backlog issue
4. Reopen policy: regression/false closure only, not new scope

**Acceptance:** BACKLOG.md regenerated from GitHub, matches issue state

---

**31.G2 — Final Review Gate**
**31.RETRO — Retrospective**
**31.CLOSURE — Sprint Closure**

---

## Decisions to Freeze

| ID | Topic | When |
|----|-------|------|
| D-122 | Backlog-to-Project-to-Sprint contract | Before 31.2 |

## Output Files

| Task | Output |
|------|--------|
| 31.1 | `docs/decisions/D-122-backlog-project-sprint.md` |
| 31.2 | `tools/backlog-import.py`, 35 GitHub issues |
| 31.3 | Project V2 fields + views |
| 31.4 | Updated `issue-from-plan.yml` with backlog_ref |
| 31.5 | `tools/generate-backlog.py`, updated BACKLOG.md |
