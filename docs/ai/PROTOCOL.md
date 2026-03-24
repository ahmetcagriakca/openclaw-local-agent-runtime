# Collaboration Protocol

**Last updated:** 2026-03-24

---

## Proposal Format

Every substantial technical proposal must use:

1. **Current State** — reference STATE.md
2. **Goal** — what to achieve
3. **Assumptions** — what we take for granted
4. **Constraints** — what we cannot change
5. **Proposed Changes** — concrete file/code changes
6. **Risks** — what could go wrong
7. **Validation Plan** — how we prove it works
8. **Repo File Updates Needed** — which docs/ai/ files change

---

## Session Protocol

Every work session ends with:
- STATE delta
- BACKLOG delta
- DECISION delta
- NEXT update

---

## Sprint Protocol (Phase 4+)

Phase 4 sprints follow exit criteria documents:
- Each sprint produces a report in `docs/phase-reports/`
- Every sprint requires test count + 0 failure evidence
- Sprint reports include: executive summary, changes made, test evidence, file manifest

---

## Design Freeze Protocol

- Section-level amendments (L-A1, L-A2) for incremental freezes within a phase
- Amendment creates new frozen section without reopening existing frozen sections
- Consolidated design document (v3) is the master reference for all 58 decisions

---

## Reopening Frozen Decisions

Requires: identify which decision, provide evidence, get operator approval, update DECISIONS.md. No silent drift. No temporary exceptions.

---

## Technical Standards

- Scripts, logs, commands, code outputs: English/ASCII only
- Manifest-based action registry
- All persistent state in repo files, not chat history
