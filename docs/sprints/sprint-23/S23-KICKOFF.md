# Sprint 23 Kickoff — Regression Guards & Live E2E CI

## Metadata

| Field | Value |
|-------|-------|
| Sprint | 23 |
| Phase | 6 |
| Model | **A** (full evidence, sprint-time gates) |
| implementation_status | `not_started` |
| closure_status | `not_started` |
| Owner | AKCA |
| Plan date | 2026-03-28 |

---

## Process alignment (GOVERNANCE.md)

1. **Pre-sprint GPT review** → verdict PASS stored as `docs/ai/reviews/S23-REVIEW.md` (or pre-kickoff filename per operator) before first implementation commit.
2. **Sprint kickoff gate:** previous sprint `closure_status=closed` (S22 closed per handoff); open decisions ≤ 2; task breakdown + `plan.yaml` frozen; evidence checklist agreed below.
3. **Branch-per-task:** `sprint-23/t23.*` per `docs/shared/BRANCH-CONTRACT.md`; no direct push to `main`.
4. **Closure:** artifacts under `docs/sprints/sprint-23/artifacts/` including `closure-check-output.txt` (raw pytest / vitest / tsc / ruff / CI links as applicable).

---

## Scope — IN

| ID | Theme |
|----|--------|
| 23.1 | Stale doc references (S22 retro) |
| 23.2 | Benchmark regression baseline + CI enforcement (D-109 follow-up) |
| 23.3 | Playwright smoke vs live API in GitHub Actions (S22 retro) |
| Gates | G1, G2, RETRO, CLOSURE per task breakdown |

## Scope — OUT (defer to S24+)

- OpenAPI → TypeScript SDK generation (NEXT.md candidate; separate scope).
- `status-sync` full Project V2 field mutation (S20 partial).
- `pr-validator` required PR body sections (S20 partial).
- Multi-user auth, Jaeger deploy, Docker dev stack.

---

## Evidence checklist (minimum)

- [ ] `python tools/validate-plan-sync.py docs/sprints/sprint-23/` → PASS  
- [ ] Backend tests unchanged count policy respected (no `collect_ignore`)  
- [ ] Benchmark job uploads/regression step documented  
- [ ] Playwright CI job log excerpt or artifact reference in sprint artifacts  

---

## Operator actions before `issue-from-plan`

- [ ] Create GitHub milestone **Sprint 23** if missing (`tools/bootstrap-labels-milestones.sh` or UI).  
- [ ] Run workflow dispatch on `issue-from-plan.yml` with sprint directory `docs/sprints/sprint-23` (path per workflow input).  
- [ ] Confirm `gh` project scope if using Project V2 auto-add.

---

## Regression tolerance (23.2)

Default proposal: **±25%** median vs baseline per endpoint family on `ubuntu-latest`, single run — adjust after first noisy failure. Record final number in Implementation Notes when frozen.
