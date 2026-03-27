# Next Steps — Vezir Platform

**Last updated:** 2026-03-27
**Current:** Phase 6 active. Sprint 18 in progress.

---

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
