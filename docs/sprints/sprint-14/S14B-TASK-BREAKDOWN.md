# Sprint 14B — Task Breakdown (Post-Hoc Regularized)

**Sprint:** 14B — Frontend Restructure + Tooling
**Date:** 2026-03-27 (retroactive — produced per independent closure review B-3B)
**closure_status:** closed

---

## Delivered Tasks

| # | Task | Description | Output |
|---|------|-------------|--------|
| 14B.1 | Feature-based frontend structure | Move pages/components into features/ modules | `features/missions/`, `features/health/`, `features/approvals/`, `features/telemetry/` |
| 14B.2 | Barrel exports | index.ts per feature module | 4 barrel files |
| 14B.3 | Path alias (@/) | tsconfig paths + vite resolve config | `@/` → `src/` |
| 14B.4 | Pre-commit hooks | ruff check + tsc --noEmit + pytest quick | `.pre-commit-config.yaml` |
| 14B.5 | CONTRIBUTING.md | Developer onboarding guide | `CONTRIBUTING.md` |
| 14B.6 | Structured logging config | JSON formatter for backend | `agent/app/core/logging.py` |
| 14B.7 | Lighthouse hold verification | Confirm no accessibility regression | Score maintained at 95 |
| 14B.8 | Dependency audit | Check for known vulnerabilities | Clean audit |

## Deferred Items

| Item | Reason | Target |
|------|--------|--------|
| Docker dev environment | Scope too large for tooling sprint | Phase 6 |
| Backend physical restructure | Shim approach sufficient for now | Phase 6 |
| Mission error recovery UI | Requires backend error taxonomy | Phase 6 |
| Performance benchmark automation | Needs CI pipeline first (delivered in S16) | Done in S16 |
| ESLint strict mode | Risk of breaking existing code | Phase 6 |
| Frontend unit test expansion | Time constraint | Phase 6 |
| API client code generation | Needs stable OpenAPI spec | Phase 6 |
| Monorepo workspace config | Single repo sufficient for now | Phase 6 |

## Scope Boundary: 14A vs 14B

| Concern | 14A | 14B |
|---------|-----|-----|
| EventBus + handlers | Delivered | — |
| Backend app/ package (shim) | Delivered | — |
| Backend physical restructure | — | Deferred to Phase 6 |
| Frontend feature structure | — | Delivered |
| Pre-commit + tooling | — | Delivered |
| pyproject.toml + ruff + mypy | Delivered | — |
