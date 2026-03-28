# Sprint 21 — Task Breakdown

**Sprint:** 21
**Phase:** 6
**Title:** Closure + Archive Automation
**Model:** A
**Goal:** After S21, only manual actions are operator judgment calls (freeze, close, exceptional rollback).

---

## Track 1: Review + Quality

**21.1 — Review packet generator**
Script: `tools/generate-review-packet.py`. Reads sprint dir (plan.yaml, issues.json, evidence/), produces a review summary markdown listing: task status, evidence inventory, PR linkage, acceptance criteria status. Input: sprint number. Output: review packet markdown.

**21.2 — Stale ref grep automation**
Script: `tools/check-stale-refs.py`. Scans active docs for references to files/paths that no longer exist. Checks: docs/ai/*.md, docs/shared/*.md, CLAUDE.md. Reports broken refs with file:line. Exit 0 if clean, exit 1 if stale refs found.

## Track 2: Closure Automation

**21.3 — Archive manifest generator**
Script: `tools/generate-archive-manifest.py`. Given a sprint number, produces a manifest of files to archive: sprint docs, evidence, review packets. Output: JSON manifest with source→destination mappings.

**21.4 — Closure preflight workflow**
GitHub Actions workflow: `closure-preflight.yml`. Runs on workflow_dispatch with sprint_number input. Checks: all evidence files exist, validator passes, no unmerged sprint branches, issues closed. Blocks closure if any check fails.

## Track 3: Branch Hygiene

**21.5 — Merged-state-only closure check**
Script: `tools/check-merged-state.py`. Verifies all sprint branches are merged to main. Lists any unmerged branches. Used by closure preflight.

**21.6 — Branch cleanup automation**
Script: `tools/cleanup-merged-branches.sh`. Deletes remote branches that have been merged to main for a given sprint. Dry-run mode by default, --force to actually delete.

## Gates

**21.G1 — Mid Review Gate**
After Track 1 + Track 2 complete.

**21.G2 — Final Review Gate**
After all tracks complete. Full evidence review.

**21.RETRO — Retrospective**
Did closure automation reduce manual work? What friction remains?

**21.CLOSURE — Sprint Closure**
All branches merged. All evidence present. Operator sign-off.
