# Collaboration Protocol

**Last updated:** 2026-03-25

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

## Sprint-End Documentation Protocol (D-077)

The following steps are mandatory at every sprint closure:

1. Complete all code tasks
2. Update the following documents:

| Document | Update |
|----------|--------|
| `docs/ai/STATE.md` | Active phase, sprint, test count |
| `docs/ai/NEXT.md` | Next sprint/task updates |
| `docs/ai/DECISIONS.md` | D-XXX decisions made in sprint |
| `docs/ai/BACKLOG.md` | Completed B-XXX, new items |
| `SESSION-HANDOFF.md` | Sprint snapshot |
| Sprint plan doc | Checklist [x] completion |

3. Run validation script:

```bash
python tools/validate_sprint_docs.py --sprint N --sprint-date YYYY-MM-DD
```

4. 0 FAIL → commit + push
5. If FAIL → fix and re-run

Sprint is not "done" until validation passes.

---

## Reopening Frozen Decisions

Requires: identify which decision, provide evidence, get operator approval, update DECISIONS.md. No silent drift. No temporary exceptions.

---

## Technical Standards

- Scripts, logs, commands, code outputs: English/ASCII only
- Manifest-based action registry
- All persistent state in repo files, not chat history

---

## Cross-Review Protocol

- GPT comments are never ignored, never treated as truth without verification
- Every cross-review comment is either: applied, rejected with reason, or deferred with tracking
- Applied fixes reference the review round (e.g., "GPT-1 fix applied")

---

## Source Hierarchy

When sources conflict:

1. Real code in the repo
2. Test results, logs, runtime evidence
3. Frozen decisions (D-XXX)
4. Sprint plans and design docs
5. GPT cross-review comments
6. Assumptions
