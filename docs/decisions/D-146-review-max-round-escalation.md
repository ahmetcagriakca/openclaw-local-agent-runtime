# D-146 — Review Max Round + Escalation Rule

**ID:** D-146
**Title:** Review Max Round + Escalation Rule
**Status:** frozen
**Date:** 2026-04-06
**Owner:** AKCA
**Trigger:** S73 — 10 round review loop

## Context

S73 review went 10 rounds. GPT reviewer repeated the same structural finding (single commit mid-review gate timing proof) from R4 onwards with cosmetic variations. Pipeline had no loop-breaking mechanism.

## Decision

1. Maximum review round per sprint: 5
2. Same core finding unchanged across 3 consecutive rounds → reviewer must issue ESCALATE verdict instead of HOLD
3. ESCALATE triggers Stage 5 (operator escalation) in the review pipeline
4. Operator can: override close, agree and create remediation task, or defer with waiver
5. ask-gpt-review.sh enforces round limit with warning at R3 and block at R5

## Trade-off

- Pro: Prevents infinite review loops, preserves operator authority
- Con: Genuine complex blockers might get escalated prematurely at R5
- Mitigation: Operator can always FORCE_REVIEW=1 to proceed past R5

## Validation

1. gpt-review-system_v3.md contains Anti-Loop Rule section
2. review-verdict-contract_v2.md contains rules 13-15
3. review-pipeline-runbook_v2.md contains Stage 5
4. ask-gpt-review.sh contains round tracking logic

## Impacted Files

- docs/ai/prompts/gpt-review-system_v3.md
- docs/ai/prompts/review-verdict-contract_v2.md
- docs/ai/prompts/review-pipeline-runbook_v2.md
- tools/ask-gpt-review.sh
