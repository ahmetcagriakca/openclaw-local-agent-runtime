# Review Pipeline Runbook v2 — Vezir

## Purpose

Separate deterministic gate checks from AI judgment so review stays fast, narrow, and auditable.

## Pipeline

### Stage 0 — Preflight Build
Run before any model review.
Goal: generate or refresh the packet inputs.

1. Generate or refresh closure packet under `evidence/sprint-{N}/`
2. Run `tools/sprint-closure-check.sh {N}` and save raw output
3. Run validator and save raw output
4. Confirm retrospective exists
5. Confirm task docs contain Implementation Notes + File Manifest + Evidence Checklist
6. Confirm all required decisions are frozen

If Stage 0 fails, do not ask for PASS/HOLD review yet.

### Stage 1 — Deterministic Gate Validation
Input: repo + evidence directory generated in Stage 0
Output: packet-ready or blocked
Goal: validate the generated artifacts, not create them.

Required checks:
- mandatory artifacts present
- status model valid
- no stale closure packet
- no missing raw outputs disguised by reports
- no open decisions leaking into implementation
- gate tasks exist in sprint doc

### Stage 2 — Delta Packet Build
Create `review-delta-packet_v2.md` for the sprint.
Rules:
- delta only
- no full handoff dump
- no previous review transcript dump
- no narrative summary
- only checkable claims

### Stage 3 — AI Review
Use:
- system prompt: `gpt-review-system_v3.md`
- user payload: filled `review-delta-packet_v2.md`
- output contract: `review-verdict-contract_v2.md`

Execution:
```bash
tools/ask-gpt-review.sh <sprint-number>
```

Expected result:
- PASS or HOLD only
- one code block only
- blocker-driven patch set if HOLD

### Stage 4 — Re-review
Only after concrete patches and new evidence exist.
Required inputs:
- previous blockers
- `PATCHES APPLIED` section
- new raw evidence paths
- new commit ids

Do not re-review already accepted findings.

### Stage 5 — Operator Escalation
Triggered when:
- Same finding persists unchanged across 3+ rounds
- Round count reaches 5
- Reviewer explicitly issues ESCALATE verdict

Operator actions:
1. Review the blocker history across rounds
2. Determine if blocker is valid, invalid, or unresolvable
3. Either:
   a. Override: close sprint with documented override reason
   b. Agree: create remediation task for next sprint
   c. Defer: waiver + carry-forward to backlog

Document decision in `docs/ai/reviews/S{N}-GPT-REVIEW.md` under `## Operator Override` section.

## Stop Rules

Stop and hold immediately if:
- closure-check output is missing
- validator output is missing
- retrospective is missing
- a decision is still open but implementation depends on it
- gate timing cannot be proven
- packet uses non-canonical status terms
- a report is used where raw evidence is required

## Minimal Attachment Set

For chat-based review, attach or make accessible at least:
- filled delta packet
- closure-check-output.txt
- validator-output.txt
- review-summary.md
- file-manifest.txt
- any raw output referenced by a blocker-sensitive claim

## Rotation Rule

Use a separate clean review session for closure review.
Rotate session at least:
- every new phase
- every 3-4 sprints
- whenever doctrine changes materially
- whenever latency or context drift becomes visible

## Division of Labor

- Script: deterministic invariant checks
- AI reviewer: independent PASS/HOLD judgment
- Operator: final closure decision
