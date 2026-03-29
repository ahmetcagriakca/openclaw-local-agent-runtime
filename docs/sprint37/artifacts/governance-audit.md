# Governance Audit Report — Sprint 37

**Date:** 2026-03-29
**Auditor:** Claude Code
**CURRENT:** Sprint 37 | **PREVIOUS:** Sprint 36

## Summary

- Total checks: 28
- PASS: 12
- FAIL: 10
- PARTIAL: 3
- STALE: 3

---

## Critical Findings (FAIL)

### F-01. STATE.md internal decision count inconsistency (1.1)

`docs/ai/STATE.md:6` says "130 frozen decisions" but `docs/ai/STATE.md:109` says "125 frozen decisions (D-001 through D-125)." Two contradicting values in the same file.

**Evidence:**
```
Line 6:  130 frozen decisions (D-001 → D-130, D-126 skipped)
Line 109: 125 frozen decisions (D-001 through D-125)
```

**Verdict:** FAIL — internal contradition, Architectural Decisions section not updated since S33.

---

### F-02. CLAUDE.md decision count stale (1.1)

`CLAUDE.md:31` references `Frozen decisions (D-001→D-114)`. Actual count is 130 (D-001→D-130, D-126 skipped). Delta = 16 decisions behind.

**Evidence:** `grep "D-001" CLAUDE.md` → `D-001→D-114`
**Verdict:** FAIL — 16 decisions behind current state.

---

### F-03. NEXT.md extremely stale (1.2 + 1.4)

`docs/ai/NEXT.md:2` says "Phase 6 active. Sprint 21 closed." Reality: Phase 7, Sprint 36 closed. This file is 15 sprints and 1 phase behind.

**Evidence:**
```
NEXT.md line 4: Current: Phase 6 active. Sprint 21 closed.
STATE.md line 4: Phase 7 — Sprint 36 closed, Sprint 37 kickoff pending
```

**Verdict:** FAIL — canonical file (D-110) is 15 sprints stale. Violates 2-sprint freshness rule.

---

### F-04. Test count mismatch > 5 (1.3)

| Source | Backend | Frontend |
|--------|---------|----------|
| Actual (pytest --co) | 521 | 75 |
| STATE.md | 458 | 29 |
| CLAUDE.md | 458 | 29 |

Backend delta: +63 (> 5 threshold). Frontend delta: +46 (> 5 threshold).

**Evidence:** `cd agent && python -m pytest tests/ --co -q` → "521 tests collected"
**Verdict:** FAIL — both backend and frontend counts severely stale in STATE.md and CLAUDE.md.

---

### F-05. D-113 archive boundary violated — 10 stale sprint folders (2.1)

`docs/sprints/` contains sprint-23 through sprint-32 (10 folders). Per D-113, only last closed sprint + current sprint should be there. These 10 should be in `docs/archive/sprints/`.

**Evidence:**
```
docs/sprints/ contains: sprint-23, sprint-24, sprint-25, sprint-26, sprint-27,
                        sprint-28, sprint-29, sprint-30, sprint-31, sprint-32
```

Note: S33-S37 use `docs/sprint{N}/` pattern (no `s`), not `docs/sprints/sprint-{N}/`, creating an additional inconsistency.

**Verdict:** FAIL — 10 extra sprint folders violating D-113.

---

### F-06. Decision formal record files split across two directories (3.1)

Decision records are split between `decisions/` (root, 7 files: D-123→D-130) and `docs/decisions/` (14 files: D-105→D-122). This dual-directory pattern is undocumented and inconsistent.

Missing formal records for D-105+ decisions: D-111, D-112, D-113, D-114 (4 decisions frozen in S18 without formal record files).

**Evidence:**
```
decisions/  → D-123, D-124, D-125, D-127, D-128, D-129, D-130 (7 files)
docs/decisions/ → D-105 through D-122 (14 files, gaps at D-111-D-114)
Total formal records: 21 out of 26 required (D-105+, D-126 skipped)
```

**Verdict:** FAIL — 4 missing formal records for D-105+ decisions, plus undocumented directory split.

---

### F-07. DECISIONS.md index format inconsistency (3.1)

D-001 through D-114 use full `### D-XXX:` header format with description paragraphs. D-115 through D-130 use compact `*D-XXX:` italic one-liner format. The `### D-` grep count returns 114, causing state-sync tool to report mismatch against the actual 130 frozen decisions.

**Evidence:** `grep -c "^### D-" docs/ai/DECISIONS.md` → 114 (not 130)
**Verdict:** FAIL — format inconsistency breaks automated tooling.

---

### F-08. S36 retro missing required sections (4.5)

`docs/sprint36/SPRINT-36-RETRO.md` has "What Went Well", "What Didn't Go Well", and "Metrics" but is missing:
- Net judgment
- Root cause analysis
- Concrete actions (new D-XXX, task patch, process patch, script patch, or scoreboard update)

Per governance rules: "Commentary-only retrospective without concrete output = FAIL."

**Evidence:** Full file contents of `docs/sprint36/SPRINT-36-RETRO.md` — 23 lines, no "Root Cause", "Actions", "Output" sections.
**Verdict:** FAIL — retro exists but lacks required concrete outputs.

---

### F-09. No S37 review file yet (4.1)

`docs/ai/reviews/S37-REVIEW.md` does not exist. GPT HOLD verdict is only referenced in the handoff, not in a formal review file.

**Evidence:** `ls docs/ai/reviews/S37*` → no match
**Verdict:** FAIL — GPT HOLD verdict not captured in review file. (Note: S37 is in kickoff phase, so this is expected-but-flagged per audit rules.)

---

### F-10. No plan.yaml for S37 — no backlog_ref linkage (8.2)

Sprint 37 has no `plan.yaml` file. Task-to-backlog linkage via `backlog_ref` (D-122) cannot be verified.

**Evidence:** `grep "backlog_ref" docs/sprint37/*.yaml` → no match, no yaml files exist.
**Verdict:** FAIL — D-122 sprint-backlog linkage not implemented for S37.

---

## Warnings (PARTIAL / STALE)

### W-01. STATE.md test evidence table stale (1.3) — STALE

Test Evidence table in `docs/ai/STATE.md:96-106` last updated at Sprint 16 (458 backend, 29 frontend). Current: 521 backend, 75 frontend. Table has not been updated for 21 sprints.

---

### W-02. copilot-instructions.md has no phase/sprint reference (7.2) — PARTIAL

`.github/copilot-instructions.md` (v3.0, 2026-03-25) contains sprint governance rules but does not explicitly state the current phase or sprint number. Not technically stale but lacks phase context.

**Evidence:** `grep -i "phase\|sprint" .github/copilot-instructions.md` shows rules but no "Phase 7" or "Sprint 37" reference.

---

### W-03. Governance files have different scope, not conflicting (7.1) — PARTIAL

- `docs/ai/GOVERNANCE.md` — sprint governance (D-112), evidence standard, gates
- `docs/shared/GOVERNANCE.md` — operator authority, merge rules, branch-exempt gates
- `.github/copilot-instructions.md` — AI agent working instructions (v3.0)

No direct contradictions found, but the two GOVERNANCE.md files cover different aspects without cross-references. Risk of future divergence.

---

### W-04. Sprint folder naming inconsistency (2.1) — PARTIAL

S23-S32 use `docs/sprints/sprint-{N}/` pattern. S33-S37 use `docs/sprint{N}/` (no `sprints/` parent, no hyphen). No decision or documented reason for the path change.

---

### W-05. D-126 gap undocumented (3.2) — STALE

DECISIONS.md jumps from D-125 to D-127. The handoff notes "D-126 skipped" but no explanation is in DECISIONS.md itself.

---

### W-06. S37 evidence directory not created (4.1) — STALE

`evidence/sprint-37/` does not exist. Acceptable since implementation has not started, but should be created at kickoff per governance.

---

## Passed Checks

### P-01. Handoff decision count correct (1.1) — PASS
`docs/ai/handoffs/current.md:17` says "130 frozen (D-001 → D-130, D-126 skipped)". Matches DECISIONS.md actual count (114 full + 16 compact = 130).

### P-02. Sprint state in STATE.md and handoff agree (1.2) — PASS
Both say Sprint 36 closed, Sprint 37 kickoff pending.

### P-03. Phase state agreement (STATE.md + handoff) (1.4) — PASS
Both say Phase 7.

### P-04. Stale reference check tool (2.3) — PASS
`python tools/check-stale-refs.py` → "PASS: No stale references found" (71 references checked, 0 stale).

### P-05. Archive structure (2.4) — PASS
`docs/archive/sprints/` is sub-structured by sprint (sprint-12 through sprint-22). `docs/archive/` has sub-directories: evidence, sprints, stale-ai-docs.

### P-06. Canonical files exist (2.5) — PASS
STATE.md, NEXT.md (stale but exists), DECISIONS.md, GOVERNANCE.md, handoffs/current.md all present.

### P-07. No OD leak outside DECISIONS.md (3.3) — PASS
`grep -rn "OD-"` in docs/ai/, CLAUDE.md, and sprint folders found matches only in DECISIONS.md (historical reassignment notes for OD-11, OD-12, OD-14). No leak into implementation or sprint docs.

### P-08. S36 kickoff before implementation (6.1) — PASS
Git log shows kickoff commits (`b897b55` through `489622a`) before implementation commits (`2cca7c6`, `19515e4`). Gates happened before gated work.

### P-09. S36 review exists and says PASS (4.1 for PREVIOUS) — PASS
`docs/ai/reviews/S36-REVIEW.md` exists, verdict "PASS", tasks mapped to commits.

### P-10. S36 retro exists (4.5 partial) — PASS
`docs/sprint36/SPRINT-36-RETRO.md` exists (content quality flagged in F-08 separately).

### P-11. S36 evidence packet complete (5.1) — PASS
`evidence/sprint-36/` contains 20 files including mandatory: closure-check-output.txt, contract-evidence.txt, pytest-output.txt, vitest-output.txt, tsc-output.txt, lint-output.txt, mutation-drill.txt, e2e-output.txt, lighthouse.txt.

### P-12. S36 evidence freshness (5.2) — PASS
`evidence/sprint-36/closure-check-output.txt` dated 2026-03-29T10:29:52+03:00 — same day as S36 closure.

---

## Recommended Actions

| # | Action | File(s) | Priority |
|---|--------|---------|----------|
| R-01 | Fix STATE.md line 109 to say "130 frozen decisions (D-001→D-130, D-126 skipped)" | `docs/ai/STATE.md:109` | P1 |
| R-02 | Update CLAUDE.md decision reference from D-114 to D-130 | `CLAUDE.md:31` | P1 |
| R-03 | Rewrite NEXT.md or mark as deprecated — 15 sprints stale | `docs/ai/NEXT.md` | P1 |
| R-04 | Update test counts in STATE.md (521 backend, 75 frontend) and CLAUDE.md | `docs/ai/STATE.md:96-106`, `CLAUDE.md` | P1 |
| R-05 | Archive docs/sprints/sprint-23 through sprint-32 to docs/archive/sprints/ | `docs/sprints/sprint-{23..32}/` | P1 |
| R-06 | Consolidate decision files into single directory (recommend `docs/decisions/`) | `decisions/` → `docs/decisions/` | P2 |
| R-07 | Normalize DECISIONS.md D-115+ entries to use `### D-XXX:` header format, or update state-sync tool to count both formats | `docs/ai/DECISIONS.md` | P2 |
| R-08 | Add missing formal records for D-111, D-112, D-113, D-114 | `docs/decisions/` | P2 |
| R-09 | Add Root Cause, Concrete Actions, Net Judgment to S36 retro | `docs/sprint36/SPRINT-36-RETRO.md` | P2 |
| R-10 | Create S37 GPT review file when HOLD is resolved | `docs/ai/reviews/S37-REVIEW.md` | P2 |
| R-11 | Create plan.yaml for S37 with backlog_ref per D-122 | `docs/sprint37/plan.yaml` | P2 |
| R-12 | Standardize sprint folder naming (decide: `docs/sprints/sprint-N/` or `docs/sprintN/`) | governance decision needed | P3 |
| R-13 | Document D-126 skip reason in DECISIONS.md | `docs/ai/DECISIONS.md` | P3 |
| R-14 | Create `evidence/sprint-37/` directory | `evidence/sprint-37/` | P3 |

---

*Audit complete. 28 checks executed. No checks skipped. All findings backed by file path, line number, or command output.*
