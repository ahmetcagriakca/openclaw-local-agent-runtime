# S20.G2 — Final Review Gate Report

**Sprint:** 20
**Phase:** 6
**Gate:** Final Review (20.G2)
**Date:** 2026-03-27

---

## All Tasks Summary

| Task | Title | Status | Evidence |
|------|-------|--------|----------|
| 20.1 | plan.yaml + task breakdown + field schema | Merged | plan-yaml-valid.txt, validator-pass.txt |
| 20.2 | Labels + milestones bootstrap script | Merged | bootstrap script in tools/ |
| 20.3 | Issue form templates | Merged | 3 YAML templates in .github/ISSUE_TEMPLATE/ |
| 20.4 | Project auto-add workflow | Merged | project-auto-add.yml |
| 20.5 | Status sync workflow | Merged | status-sync.yml |
| 20.6 | PR title/body validator | Merged | pr-validator.yml |
| 20.7 | issues.json PR linkage script | Merged | update-pr-linkage.py |

## Files Produced

| Path | Task |
|------|------|
| docs/sprints/sprint-20/plan.yaml | 20.1 |
| docs/sprints/sprint-20/SPRINT-20-TASK-BREAKDOWN.md | 20.1 |
| docs/sprints/sprint-20/PROJECT-FIELD-SCHEMA.md | 20.1 |
| tools/bootstrap-labels-milestones.sh | 20.2 |
| .github/ISSUE_TEMPLATE/sprint-task.yml | 20.3 |
| .github/ISSUE_TEMPLATE/bug-report.yml | 20.3 |
| .github/ISSUE_TEMPLATE/feature-request.yml | 20.3 |
| .github/workflows/project-auto-add.yml | 20.4 |
| .github/workflows/status-sync.yml | 20.5 |
| .github/workflows/pr-validator.yml | 20.6 |
| tools/update-pr-linkage.py | 20.7 |

## Acceptance Criteria

- [x] plan.yaml parses → evidence: plan-yaml-valid.txt
- [x] Validator sync passes → evidence: validator-pass.txt
- [x] Bootstrap script handles labels + milestones idempotently
- [x] 3 issue form templates (sprint-task, bug-report, feature-request) in .github/ISSUE_TEMPLATE/
- [x] Project auto-add workflow: triggers on issue with sprint label, uses GraphQL API
- [x] Status sync workflow: PR open → In Progress, PR merge → Done
- [x] PR validator: validates [SN-N.M] title pattern, skips bot PRs
- [x] PR linkage script: scans merged PRs, updates issues.json PR fields

## Scope Note

Implementation PRs cover tasks 20.1-20.7. Evidence-only remediation PRs are excluded from the implementation PR set per Sprint 19 convention.

## Verdict

**HOLD** — All code artifacts merged to main. Tasks 20.1 and 20.3 fully delivered with evidence. Tasks 20.2, 20.4, 20.5, 20.6, 20.7 have code merged but lack runtime evidence due to missing prerequisites (gh CLI not installed, no GitHub Project V2 board created).

**Not eligible for closure.** Eligible only after:
1. gh CLI installed on dev machine
2. GitHub Project V2 board created
3. `bootstrap-labels-milestones.sh` executed with raw output captured
4. `project-auto-add.yml` tested with real board, run output captured
5. `status-sync.yml` tested with real PR → issue linkage, run output captured
6. `pr-validator.yml` pass/fail output captured from real PR
7. `update-pr-linkage.py` executed with raw output captured
