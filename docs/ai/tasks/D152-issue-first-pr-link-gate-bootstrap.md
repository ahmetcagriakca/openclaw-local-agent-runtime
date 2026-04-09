# D-152 Bootstrap — Issue-First PR Link Gate

Status: bootstrap PR opened before issue creation due to current connector limitation (issue create unavailable in this session).

## TASK

Make the GitHub-native communication architecture permanent by enforcing issue-first PR linkage across the repo lifecycle.

## SCOPE / CRITICAL RULES

- First implementation action: create a GitHub issue for D-152 and update the PR title/body to reference that issue explicitly.
- After issue creation, add `Closes #<issue>` to the PR body.
- Freeze `D-152` decision for issue-first PR linkage.
- Add machine-readable PR template.
- Add fail-closed PR linkage validator.
- Add PR gate workflow that blocks invalid implementation PRs.
- Extend `issue-from-plan.yml` so `issues.json` becomes the source-of-truth for PR linkage validation.
- Integrate issue↔PR linkage checks into validator/closure flow.
- Preserve current D-142 intake behavior; extend it, do not weaken it.
- Preserve explicit narrow exemption path for docs/gate/meta work only.
- Keep all technical artifacts in English/ASCII.

## VALIDATION

- `docs/decisions/D-152-issue-first-pr-link-gate.md` exists and is frozen.
- `.github/pull_request_template.md` exists and is machine-readable.
- `tools/pr-issue-link-check.py` exists and fails closed on invalid linkage.
- `.github/workflows/pr-issue-gate.yml` exists and blocks invalid PR linkage.
- `.github/workflows/issue-from-plan.yml` emits required linkage metadata into `issues.json`.
- Validator/closure flow recognizes issue↔PR linkage.
- Tests prove valid PASS and invalid FAIL cases.
- Governance/state docs are updated.
- Audit artifact exists for current repo state.

## COMPLETION CRITERIA

- Issue-first PR linkage is enforced by code and workflow, not by convention.
- Implementation PR without linked task issue fails gate.
- `issues.json` contains linkage metadata required for deterministic PR validation.
- Review/closure artifacts include Parent Issue + Task Issue + PR + Branch.
- This bootstrap PR is updated to link the created issue and then carries the implementation to completion.
