# Next Steps — Vezir Platform

**Last updated:** 2026-03-27
**Current:** Phase 6 active. Sprint 20 closed.

---

## Sprint 20 — Project Integration + PR Traceability (CLOSED)

**Model:** A (implementation)
**Scope:** GitHub Project field schema, labels/milestones bootstrap, issue form templates, project auto-add, status sync, PR validator, PR linkage
**Deliverables:** 7 tasks, 3 workflows, 3 issue templates, 2 tools, Project V2 board
**Review:** PASS — prerequisites resolved, runtime evidence captured
**Key artifacts:** `project-auto-add.yml`, `status-sync.yml`, `pr-validator.yml`, `bootstrap-labels-milestones.sh`, `update-pr-linkage.py`
**Note:** 20.5/20.6 partial delivery by design (full mutation + body sections deferred to S21)

## Sprint 19 — Single-Repo Automation MVP (CLOSED)

**Model:** A (implementation)
**Scope:** plan.yaml schema, validator, issue-from-plan workflow, branch naming contract, main protection, governance rules
**Deliverables:** 7 implementation tasks, 2 gates, retrospective
**Review:** PASS (3 rounds) — `docs/sprints/sprint-19/S19-FINAL-REVIEW.md`
**Key artifacts:** `plan.yaml`, `issues.json`, `issue-from-plan.yml`, `BRANCH-CONTRACT.md`, `GOVERNANCE.md`

## Sprint 18 — Repo Cleanup (CLOSED)

**Model:** B (docs-only)
**Scope:** Source-of-truth compression, governance consolidation, archive boundary, stale reference cleanup
**Decisions:** D-111→D-114
**Review:** PASS (2 rounds) — `docs/ai/reviews/S18-REVIEW.md`

## Phase 6 — Roadmap

| Item | Why Now |
|------|---------|
| Browser E2E with Playwright | CI/CD pipeline exists |
| OpenAPI → TypeScript SDK generation | Backend structured, API versioned |
| Multi-user / authentication | Session model foundation exists (D-108) |
| Jaeger/Grafana deployment | OTel export path documented |
| Plugin system for custom handlers | EventBus architecture supports it |
| Mission templates / presets | Mission persistence exists |
| Cost tracking / billing | Token metrics recorded |
| Frontend component tests | Vitest + React Testing Library |
| Webhook notifications (Slack, Discord) | Alert notifier extensible |
| Benchmark regression gate | D-109 deferred, JSON baseline needed |

## Carry-Forward

| Item | Source |
|------|--------|
| Backend physical restructure | S14A/14B |
| Docker dev environment | S14B |
| Live mission E2E | S14A waiver |
| UIOverview + WindowList tools | D-102 |
| Feature flag CONTEXT_ISOLATION_ENABLED | D-102 |
| Live API + Telegram E2E | S16 WAIVER-1 |
| Frontend Vitest component tests | S16 P-16.3 |
| Alert "any" rule namespace scoping | S16 P-16.2 |
| Jaeger deployment | S16 deferred |
| Multi-user auth | D-104/D-108 |

## Decision Debt

- D-001→D-114: all frozen (114 total)
- D-021→D-058 extraction (AKCA-assigned, non-blocking)
