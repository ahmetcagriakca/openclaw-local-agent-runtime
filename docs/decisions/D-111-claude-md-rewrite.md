# D-111 — CLAUDE.md Rewrite

**ID:** D-111
**Title:** CLAUDE.md Rewrite — Compact Operating Brief
**Status:** frozen
**Proposed date:** 2026-03-27
**Frozen date:** 2026-03-27
**Owner:** AKCA
**Recommended by:** Claude (Sprint 18 docs cleanup)

---

## Context

CLAUDE.md had grown to include stale sections (Current State, Phase 5 Progress, Architecture Quick Reference) that duplicated STATE.md/NEXT.md content and drifted from reality. Claude Code convention requires the filename stay as `CLAUDE.md`.

---

## Decision

- **Filename:** Keep `CLAUDE.md` (Claude Code convention).
- **Target size:** ~80-100 lines (compact operating brief).
- **Remove:** Stale sections — Current State, Phase 5 Progress, Architecture Quick Reference.
- **Keep sections:** Project, Key Files, Documentation, Build & Test, Hard Rules, Do Not.
- **Rationale:** CLAUDE.md should be a quick-reference operating brief, not a state document. STATE.md and NEXT.md are canonical for system state per D-110.

---

## Validation

- CLAUDE.md exists and is ≤100 lines.
- No stale sections remain.
- All referenced files/paths are valid.

---

## References

- D-110: Documentation Model Hierarchy
- Sprint 18: Docs cleanup scope
