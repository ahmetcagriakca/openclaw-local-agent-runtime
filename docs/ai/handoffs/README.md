# docs/ai/handoffs/ — Session Handoff Directory

## Purpose

Single source of truth for session-to-session context transfer.
Replaces manual upload of SESSION-HANDOFF.md files.

## Active File

`current.md` — always the live handoff. Claude Code overwrites this at session end.

## Archive

Previous handoffs move to the `archive/` subdirectory with naming pattern `YYYY-MM-DD-vN.md` when a new one is written.

## current.md Format

```markdown
# Session Handoff — YYYY-MM-DD

**Platform:** Vezir Platform
**Session scope:** [what this session covered]

## Sprint Status
[table]

## Open Blockers
[numbered list]

## Decisions
[D-XXX table with status changes this session]

## Next Session Priority
[numbered, with blocker flag]

## Hard Rules Active
[any active constraints]
```

## Protocol

1. Claude Code writes `current.md` at end of every session
2. Next session starts by reading `current.md`
3. No manual upload needed
4. Chat session trigger: "current handoff oku" or just start working — Claude Code reads it automatically
