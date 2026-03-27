# Sprint 18 Plan — Repo Cleanup (Source-of-Truth Compression)

## Context

Sprint 17 closed. Audit (`docs/vezir_repo_cleanup_audit.md`) identified truth fragmentation: multiple docs claiming canonical status, stale governance docs, historical artifacts mixed with active truth. 166 files under `docs/`, 32 phase reports, 5 old sprint folders — navigation friction and AI context pollution.

Sprint 18 implements the 7 audit decisions. No code changes — docs-only sprint.

---

## Decisions to Freeze (D-111 → D-114)

| ID | Decision |
|----|----------|
| D-111 | CLAUDE.md stays as filename (Claude Code convention), rewritten to ~80-100 lines, stale sections removed |
| D-112 | PROCESS-GATES.md + PROTOCOL.md → `docs/ai/GOVERNANCE.md` (~150-200 lines) |
| D-113 | Archive boundary: `docs/archive/` sub-structured by type; active sprints = last closed + current only |
| D-114 | Handoff model: keep `docs/ai/handoffs/current.md` path (sprint-plan.py depends on it), archive stale snapshots |

---

## Task Breakdown

### Phase A — Freeze + Kickoff

| Task | Description |
|------|-------------|
| **18.0** | Freeze D-111→D-114 in DECISIONS.md, create `docs/sprints/sprint-18/` with kickoff doc |

### Phase B — Consolidate

| Task | Description |
|------|-------------|
| **18.1** | Create `docs/ai/GOVERNANCE.md` — merge PROCESS-GATES.md (368 lines) + PROTOCOL.md (93 lines) → ~150-200 lines. Keep: source hierarchy, sprint status model, gate model, done/evidence/closure/archive rules, test hygiene, retrospective gate, proposal format, cross-review protocol. Drop: patch history (P-01→P-10), migration model, sprint-specific rules |
| **18.2** | Rewrite `CLAUDE.md` — ~80-100 lines. Sections: Project (2-3 lines), Key Files (table), Documentation (canonical doc pointers incl. GOVERNANCE.md), Build & Test (exact commands), Hard Rules (compact list), Do Not. Remove: Current State, Phase 5 Progress, Repo-Native Workflow, Architecture Quick Reference |
| **18.3** | Simplify `docs/ai/NEXT.md` — forward-only. Remove completed sprint dumps + capabilities table. Keep: current phase, Phase 6 roadmap, carry-forward, decision debt status |
| **18.4** | Simplify `docs/ai/BACKLOG.md` — open-only. Remove completed items (B-029→B-057). Keep only genuinely open items |
| **18.5** | Update `docs/ai/STATE.md` — fix doc model references, add GOVERNANCE.md pointer |

**Mid Review Gate** after 18.1-18.5

### Phase C — Move/Archive

| Task | Description |
|------|-------------|
| **18.6** | Archive process docs: `PROCESS-GATES.md`, `PROTOCOL.md` → `docs/archive/process-history/`; `DECISION-DEBT-BURNDOWN.md` → `docs/archive/debt-plans/` |
| **18.7** | Archive old sprint folders: sprint-12 through sprint-16 → `docs/archive/sprints/` (merge with existing archive content). Keep only sprint-17 + sprint-18 in `docs/sprints/` |
| **18.8** | Archive old phase reports: 30 files → `docs/archive/phase-reports/`. Keep only: PHASE-5.5-CLOSURE-REPORT.md, SPRINT-15, SPRINT-16 reports (3 files) |
| **18.9** | Archive review packets (S16/S17) + stale handoff snapshots |

### Phase D — Verify + Fix References

| Task | Description |
|------|-------------|
| **18.10** | Grep entire repo for stale paths (`PROCESS-GATES.md`, `PROTOCOL.md`, `DECISION-DEBT-BURNDOWN`, old sprint paths) in non-archive files. Fix all broken references |
| **18.11** | Update `README.md` — doc links, decision count (110+), replace PROTOCOL.md ref with GOVERNANCE.md |
| **18.12** | Update `CONTRIBUTING.md` — replace PROCESS-GATES.md ref with GOVERNANCE.md |
| **18.13** | Update `.github/copilot-instructions.md` — replace PROCESS-GATES.md ref, update project context, remove historical sprint-specific rules |
| **18.14** | Check `tools/sprint-closure-check.sh` and `tools/sprint-plan.py` for stale doc references |

### Final Gates

| Task | Description |
|------|-------------|
| **18.REPORT** | Sprint report + evidence bundle |
| **18.RETRO** | Retrospective |
| **18.CLOSURE** | Closure summary for operator sign-off |

---

## Critical Files

| File | Action |
|------|--------|
| `CLAUDE.md` | Rewrite |
| `docs/ai/GOVERNANCE.md` | Create (new) |
| `docs/ai/PROCESS-GATES.md` | Read → merge into GOVERNANCE → archive |
| `docs/ai/PROTOCOL.md` | Read → merge into GOVERNANCE → archive |
| `docs/ai/DECISION-DEBT-BURNDOWN.md` | Archive |
| `docs/ai/NEXT.md` | Simplify |
| `docs/ai/BACKLOG.md` | Simplify |
| `docs/ai/STATE.md` | Update references |
| `docs/ai/DECISIONS.md` | Add D-111→D-114 |
| `README.md` | Update doc links |
| `CONTRIBUTING.md` | Update PROCESS-GATES ref |
| `.github/copilot-instructions.md` | Update refs + remove stale rules |
| `tools/sprint-closure-check.sh` | Check for stale refs |

---

## Safety Notes

- **CI workflows** reference zero `docs/` paths — all moves are safe
- **`tools/sprint-plan.py`** reads `docs/ai/handoffs/current.md` — this path is preserved (D-114)
- **`git mv`** for all archive moves to preserve history
- Archive docs keep their internal references frozen (no updates to archived content)
- Tests (458 backend + 29 frontend) should be unaffected but will be verified

---

## Exit Criteria

| Check | Expected |
|-------|----------|
| `docs/ai/` contains: STATE, NEXT, DECISIONS, BACKLOG, GOVERNANCE + handoffs/, reviews/, state/ | No PROCESS-GATES, PROTOCOL, DEBT-BURNDOWN |
| `wc -l CLAUDE.md` | < 120 |
| `wc -l docs/ai/GOVERNANCE.md` | 150-200 |
| `docs/sprints/` | Only sprint-17, sprint-18 |
| `docs/phase-reports/` | 3 files |
| Stale reference grep | 0 matches in non-archive |
| Backend tests | 458 pass |
| Frontend tests | 29 pass |
| D-111→D-114 frozen | In DECISIONS.md |
