# Sprint 24 Kickoff — CI Gate Hardening / Operational Safety

## Metadata

| Field | Value |
|-------|-------|
| Sprint | 24 |
| Phase | 6 |
| Model | **A** (full evidence, sprint-time gates) |
| implementation_status | `not_started` |
| closure_status | `not_started` |
| Operator | GPT (Custom GPT: Vezir) |
| Plan date | 2026-03-28 |
| GPT pre-sprint | PASS (scope recommendation + approval in single round) |

---

## Scope — IN

| ID | Theme | Source |
|----|-------|--------|
| 24.1 | Benchmark regression gate | D-109 follow-up, S23 defer |
| 24.2 | Playwright API smoke in CI | S22 retro, S23 defer |
| 24.3 | Dependabot moderate vuln fix | S23 carry-forward |
| 24.4 | PROJECT_TOKEN operational hardening | S23 retro |
| Gates | G1, G2, RETRO, CLOSURE | Standard |

## Scope — OUT (explicit defer)

| Item | Reason | Target |
|------|--------|--------|
| Archive --execute | Operator decision pending | S25 |
| Frontend Vitest component tests | Separate capability track | S25 |
| OpenAPI → TypeScript SDK | Separate scope | S25+ |
| Backend restructure, Docker, Live E2E | Phase 6 roadmap | Unassigned |

---

## Evidence checklist

- [ ] `python tools/validate-plan-sync.py docs/sprints/sprint-24/` → PASS
- [ ] Benchmark CI pass + fail evidence
- [ ] Playwright CI green evidence
- [ ] `npm audit` before/after
- [ ] SECRETS-CONTRACT.md committed
- [ ] Backend tests 458 PASS
- [ ] Frontend tests 29 PASS, 0 TS errors

---

## Benchmark threshold

Default: **±25% median** per endpoint family on ubuntu-latest, single run.
Baseline source: `tools/benchmark_api.py` output against live Vezir API.
Update policy: operator re-generates baseline, commits new file.
