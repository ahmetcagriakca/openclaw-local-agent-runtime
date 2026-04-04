# D-132: Sprint Folder Naming Convention

**Status:** Frozen
**Sprint:** 50 (Task 50.10-50.12)
**Date:** 2026-04-04

## Decision

All sprint evidence and artifacts use the canonical path `docs/sprints/sprint-NN/`.

### Rules

- Sprint folders: `docs/sprints/sprint-{number}/` (e.g., `docs/sprints/sprint-50/`)
- No nested `docs/sprints/evidence/` or `docs/sprints/docs/sprints/` paths
- Each sprint folder contains: closure-check-output.txt, plan.yaml (if applicable), issues.json (if applicable)
- CI workflows reference `docs/sprints/sprint-{N}/` format

### Migration (Sprint 50)

- Removed nested `docs/sprints/docs/sprints/` directory (empty)
- Removed `docs/sprints/automation_extracted/` directory (legacy)
- Flattened `docs/sprints/evidence/sprint-NN/` to `docs/sprints/sprint-NN/`

## Validation

- CI workflows (issue-from-plan, close-sprint-issues, closure-preflight) already use `docs/sprints/sprint-{N}/` format
- No path references to old `evidence/` subfolder in active code
