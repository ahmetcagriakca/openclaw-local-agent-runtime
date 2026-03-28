# Sprint 20 — Task Breakdown

**Sprint:** 20
**Phase:** 6
**Title:** Project Integration + PR Traceability
**Model:** A

---

## Track 1: Foundation

**20.1 — plan.yaml + task breakdown + project field schema**
Create plan.yaml, task breakdown, and GitHub Project field schema design document. Define fields: Status, Sprint, Task ID, PR Link, Track.

**20.2 — Labels + milestones bootstrap script**
Script: `tools/bootstrap-labels-milestones.sh`. Creates all labels and milestones needed for Sprint 20+ using gh CLI. Idempotent.

## Track 2: Issue Infrastructure

**20.3 — Issue form templates**
Create `.github/ISSUE_TEMPLATE/` with YAML-based issue forms: sprint-task.yml (structured task issue), bug-report.yml, feature-request.yml.

**20.4 — Project auto-add workflow**
GitHub Actions workflow that auto-adds new issues to the GitHub Project board when they have sprint labels.

## Track 3: PR Traceability

**20.5 — Status sync workflow**
GitHub Actions workflow: PR open → issue status "In Progress", PR merge → issue status "Done". Updates via GitHub Project API.

**20.6 — PR title/body validator**
GitHub Actions workflow that validates PR title matches `[SN-N.M]` pattern and body contains required sections.

## Track 4: Linkage

**20.7 — issues.json PR linkage**
Script or workflow that updates issues.json PR fields when PRs are created/merged. Backfills Sprint 19 PR data.

## Gates

**20.G1 — Mid Review Gate**
After Track 1 + Track 2 complete. Review: plan validates, labels/milestones exist, issue templates work, project auto-add works.

**20.G2 — Final Review Gate**
After all tracks complete. Full evidence review.

**20.RETRO — Retrospective**
Did PR traceability reduce manual work? Is the project board useful? What should change for S21?

**20.CLOSURE — Sprint Closure**
All branches merged. All evidence present. Operator sign-off.
