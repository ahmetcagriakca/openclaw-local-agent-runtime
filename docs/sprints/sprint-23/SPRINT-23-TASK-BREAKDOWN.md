# Sprint 23 — Task Breakdown

**Sprint:** 23
**Phase:** 6
**Title:** Governance Debt Closure + CI Hygiene
**Model:** A

**Goal:** Close S20 partial governance mutations (status-sync, pr-validator) and remediate stale documentation references. These are prerequisite debt items blocking Phase 6 forward progress.

---

## Track 1: Governance Mutation Completion

**23.1 — status-sync full project-field mutation**

Complete the partial `status-sync.yml` workflow (S20 delivery). Currently the workflow detects PR events, extracts `[SN-N.M]` pattern, and queries project structure — but **does not execute the GraphQL mutation** to update the Status field.

**Repo scope:** `.github/workflows/status-sync.yml`
**Depends on:** —
**Branch:** `sprint-23/t23.1-status-sync-mutation`

**Implementation:**
1. Extract Status field ID and option IDs (Todo, In Progress, Done) from project query response
2. Get the project item ID for the linked issue
3. Execute `updateProjectV2ItemFieldValue` GraphQL mutation
4. Add error handling: field not found, option not found, mutation failure
5. Log mutation result for audit trail

**Acceptance:**
1. PR opened → linked issue status set to "In Progress" on Project V2 board
2. PR merged → status set to "Done"
3. PR closed (not merged) → status set to "Todo"
4. Missing field/option → graceful error with descriptive log
5. Evidence: workflow run log showing successful mutation on test PR

**Verification commands:**
```bash
# Trigger via test PR, then check project field
gh api graphql -f query='{ node(id: "PROJECT_ID") { ... on ProjectV2 { items(first: 5) { nodes { fieldValues(first: 10) { nodes { ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2SingleSelectField { name } } } } } } } } }'
```

**Evidence required:** CI workflow run log + project board screenshot or GraphQL query output

**23.2 — pr-validator body required sections**

Complete the partial `pr-validator.yml` workflow (S20 delivery). Currently validates PR title pattern and warns on empty body — but **does not validate required body sections**.

**Repo scope:** `.github/workflows/pr-validator.yml`
**Depends on:** —
**Branch:** `sprint-23/t23.2-pr-validator-body`

**Implementation:**
1. Define required sections for sprint PRs: `## Summary`, `## Test Plan`
2. Parse PR body for section headers (case-insensitive, `##` prefix)
3. Validate each required section exists and has content (not just header)
4. On missing sections: post PR comment listing required sections with template
5. Bot PRs remain exempt

**Acceptance:**
1. Sprint PR with all sections → passes validation
2. Sprint PR missing section → fails with descriptive error listing missing sections
3. Non-sprint PR → sections are recommended (warn) not required
4. Bot PRs → skipped entirely
5. Evidence: workflow run log on test PR with/without sections

**Verification commands:**
```bash
# Check workflow syntax
act -l -W .github/workflows/pr-validator.yml 2>/dev/null || echo "act not installed, manual verify"
```

**Evidence required:** CI workflow run log showing pass/fail on test PRs

---

## Gates

**23.G1 — Mid Review Gate**

After Track 1 (23.1 + 23.2). Review: both mutations functional, test evidence collected. Branch-exempt.

---

## Track 2: Documentation Hygiene

**23.3 — Stale documentation reference remediation**

Remediate remaining 4 stale references identified in S22 retrospective. Targets: `docs/ai/DECISIONS.md` and `docs/ai/handoffs/README.md`.

**Repo scope:** `docs/ai/DECISIONS.md`, `docs/ai/handoffs/README.md`
**Depends on:** 23.G1
**Branch:** `sprint-23/t23.3-stale-ref-remediation`

**Implementation:**
1. Run `python tools/check-stale-refs.py` to identify current stale refs
2. For each stale ref: fix (update path), remove (if target deleted), or waiver (if intentional historical pointer — document reason)
3. Run `python tools/check-stale-refs.py` again to verify zero stale count (or waivers documented)

**Acceptance:**
1. `check-stale-refs.py` default scan returns zero stale refs OR all remaining are documented waivers
2. Evidence: before/after output of `check-stale-refs.py` in sprint artifacts

**Verification commands:**
```bash
python tools/check-stale-refs.py
python tools/check-stale-refs.py --strict
```

**Evidence required:** Before/after `check-stale-refs.py` output in `docs/sprints/sprint-23/artifacts/`

---

**23.G2 — Final Review Gate**

Full evidence: pytest + vitest + tsc + ruff + workflow run logs; sprint artifact index. Branch-exempt.

**23.RETRO — Retrospective**

Answer: Are governance mutations stable? Is the PR validator too strict or too lenient? What to prioritize in S24 (benchmark gate, Playwright CI, OpenAPI SDK)?

**23.CLOSURE — Sprint Closure**

All implementation task branches merged to `main`; evidence under `docs/sprints/sprint-23/artifacts/`; operator sets `closure_status=closed`.

---

## Carry-Forward (explicit defer from this sprint)

| Item | Reason | Target | Owner |
|------|--------|--------|-------|
| Benchmark regression gate (D-109) | Governance debt must close first | S24 | Unassigned |
| Playwright API smoke in CI | Depends on stable CI; deferred to post-governance | S24 | Unassigned |
| Dependabot moderate vuln (1) | Not security-critical; monitor | S24 | AKCA |
| Archive --execute on closed sprints | Operator decision pending | TBD | AKCA |

---

## Output Files

| Task | Output |
|------|--------|
| 23.1 | `.github/workflows/status-sync.yml` (updated) |
| 23.2 | `.github/workflows/pr-validator.yml` (updated) |
| 23.3 | `docs/ai/DECISIONS.md`, `docs/ai/handoffs/README.md` (fixed refs) |
