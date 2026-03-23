# Collaboration Protocol

**Last updated:** 2026-03-23

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

## Reopening Frozen Decisions

Requires: identify which decision, provide evidence, get operator approval, update DECISIONS.md. No silent drift. No temporary exceptions.

---

## Technical Standards

- Scripts, logs, commands, code outputs: English/ASCII only
- Manifest-based action registry
- All persistent state in repo files, not chat history
