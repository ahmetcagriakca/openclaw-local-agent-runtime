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

## File Format

```markdown
# S{N}-REVIEW — [Sprint Title]

**Date:** YYYY-MM-DD
**Reviewer:** Claude (Architect)
**Input:** docs/review-packets/S{N}-REVIEW-PACKET.md

## Verdict

PASS | HOLD | FAIL

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
```

## Current Reviews

| File | Sprint | Verdict | Date |
|------|--------|---------|------|
| *(none yet — first review will appear here)* | | | |
