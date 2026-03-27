# docs/ai/reviews/ — Review Artifact Directory

This directory contains review verdicts written by the architect reviewer (Claude chat session).

## Purpose

Decouple review decisions from chat sessions. All review outputs land here as repo-native artifacts.
Claude Code reads from here. No copy-paste. No re-upload.

## File Naming Convention

```
S{N}-REVIEW.md          — Sprint N closure review verdict
S{N}-KICKOFF-REVIEW.md  — Sprint N kickoff gate review
D{N}-REVIEW.md          — Decision record review
PHASE-{N}-REVIEW.md     — Phase closure review
```

## Closure Flow (Frozen)

```
sprint-finalize.sh  →  ELIGIBLE / NOT CLOSEABLE
Review verdict      →  PASS (eligible for operator close) / HOLD + patch list
Operator sign-off   →  closure_status=closed
```

**`closure_status=closed` is operator-only.** No tool, no review verdict, no automation can set it. PASS means "documents are defensible, operator may close" — not "closed."

## Verdict Definitions

| Verdict | Meaning | Next Action |
|---------|---------|-------------|
| PASS | Eligible for operator close | Operator signs off → `closure_status=closed` |
| HOLD | Patches required before re-review | Claude Code applies patches, re-runs finalize |
| FAIL | Fundamental issue, sprint cannot close | Investigate root cause, may require re-scoping |

## File Format

```markdown
# S{N}-REVIEW — [Sprint Title]

**Date:** YYYY-MM-DD
**Reviewer:** Claude (Architect)
**Input:** docs/review-packets/S{N}-REVIEW-PACKET.md

## Verdict

PASS — eligible for operator close
(or: HOLD — N patches required)
(or: FAIL — reason)

## Findings

### Blocking
- ...

### Non-Blocking
- ...

## Required Patches (if HOLD/FAIL)

| # | File | Change |
|---|------|--------|
| 1 | ... | ... |

## Next Step

→ Claude Code: [exact action]
→ Operator: [sign-off action if PASS]
```

## Current Reviews

| File | Sprint | Verdict | Date |
|------|--------|---------|------|
| S17-REVIEW.md | Sprint 17 | PASS (3rd round) | 2026-03-27 |
| S18-REVIEW.md | Sprint 18 | PASS (2nd round) | 2026-03-27 |
