# Review Verdict Contract v2

<!--
Canonical Vezir review output. Use exactly one markdown code block.
No prose before or after the block.
PASS means eligible for operator closure review only.
HOLD means blockers remain.
-->

## Schema

```markdown
# Sprint {N} Review — Round {R}

## 1. Sprint / Phase / Model Metadata
- Sprint: {N}
- Phase: {phase}
- Model: {model}
- Class: {product | governance}
- Date: {YYYY-MM-DD}

## 2. Verdict
{PASS | HOLD}

## 3. Closure Eligibility
{Eligible for operator close review | Not eligible for closure}

## 4. Scope Reviewed
- {task_or_scope_1}
- {task_or_scope_2}

## 5. Accepted Findings
- {confirmed_claim_1}
- {confirmed_claim_2}

## 6. Blocking Findings
- B1 — {description} [evidence: {file/command/path mismatch}]
- B2 — {description} [evidence: {missing or contradictory proof}]

## 7. Required Patch Set
- P1 (B1) — {exact file/process patch required}
- P2 (B2) — {exact file/process patch required}

## 8. PASS Criteria
- {condition_1}
- {condition_2}

## 9. Final Judgment
{One sentence. Direct. No recap.}

## 10. Next Step
{Operator close review | Claude Code patch + rerun evidence + resubmit Round {R+1}}
```

## Rules

1. Use this structure exactly. Do not add or remove sections.
2. Verdict domain is `PASS` or `HOLD` only. `FAIL` is off-contract for this workflow.
3. Return exactly one markdown code block and nothing else.
4. `PASS` never means closed. It only means eligible for operator close review.
5. Every HOLD must contain at least one blocker and one concrete patch item.
6. Every blocker must cite direct evidence from repo state, raw outputs, decisions, or evidence manifest.
7. Keep wording short, patch-oriented, and non-narrative.
8. Round 2+ reviews must only check patch deltas plus any new defects introduced by those patches.
9. Do not repeat previously accepted findings in re-reviews unless a new patch changed them.
10. If there are zero blockers: write `None.` under Blocking Findings and `None.` under Required Patch Set.
11. If PASS: PASS Criteria must say `Satisfied.` unless a narrower wording is needed.
12. Stay under 600 tokens total.
13. Maximum 5 rounds per sprint. Round 5 HOLD triggers automatic operator escalation.
14. If the same blocker text (same core finding) appears in 3 consecutive rounds without new evidence from the reviewer, verdict must be `ESCALATE` instead of `HOLD`.
15. `ESCALATE` verdict uses the same template but replaces `## 2. Verdict` value with `ESCALATE — operator decision required` and `## 10. Next Step` with `Operator override review required. Reviewer cannot resolve this finding through further rounds.`
