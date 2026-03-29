# Sprint 23 Kickoff — Governance Debt Closure + CI Hygiene

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
| GPT pre-sprint | Round 1: HOLD → scope revised per GPT patches |

---

## Process alignment (GOVERNANCE.md)

1. **Pre-sprint GPT review** → verdict PASS stored as `docs/ai/reviews/S23-REVIEW.md` before first implementation commit.
2. **Sprint kickoff gate:** S22 `closure_status=closed` (confirmed); open decisions ≤ 2 (0 open); task breakdown + `plan.yaml` frozen; evidence checklist agreed below.
3. **Branch-per-task:** `sprint-23/t23.*` per `docs/shared/BRANCH-CONTRACT.md`; no direct push to `main`.
4. **Closure:** artifacts under `docs/sprints/sprint-23/artifacts/`.

---

## Scope — IN

| ID | Theme | Source |
|----|-------|--------|
| 23.1 | status-sync full project-field mutation | S20 partial (open item #1) |
| 23.2 | pr-validator body required sections | S20 partial (open item #2) |
| 23.3 | Stale doc reference remediation | S22 retro (open item #3) |
| Gates | G1, G2, RETRO, CLOSURE | Standard |

## Scope — OUT (explicit defer with rationale)

| Item | Reason | Target Sprint |
|------|--------|---------------|
| Benchmark regression gate (D-109) | Governance debt must close first; benchmark is second-order quality | S24 |
| Playwright API smoke in CI | Depends on stable CI foundation; governance gaps first | S24 |
| Dependabot moderate vuln (1) | Not security-critical; actively monitored | S24 |
| Archive --execute | Operator decision pending; non-blocking | TBD |
| OpenAPI → TypeScript SDK | Separate scope, no dependency on current debt | S24+ |
| Multi-user auth, Jaeger, Docker | Phase 6 roadmap; no urgency | S25+ |

---

## Evidence checklist (minimum)

- [ ] `python tools/validate-plan-sync.py docs/sprints/sprint-23/` → PASS
- [ ] Backend tests unchanged count policy respected (no `collect_ignore`)
- [ ] status-sync workflow run log showing mutation success
- [ ] pr-validator workflow run log showing section validation pass/fail
- [ ] `check-stale-refs.py` before/after output

---

## Operator actions before `issue-from-plan`

- [ ] Create GitHub milestone **Sprint 23** if missing
- [ ] Run workflow dispatch on `issue-from-plan.yml` with sprint `23`
- [ ] Confirm `gh` project scope if using Project V2 auto-add
