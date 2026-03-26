# Sprint 14 — Structural Hardening

**Phase:** 6A — Backend & Frontend Restructure
**Status:** implementation_status=not_started, closure_status=not_started
**Predecessor:** Sprint 13 (Stabilization) — review_pending
**Goal:** Transform flat file layout into maintainable layered architecture. Complete deferred D-102 tooling.

---

## Scope

### From Sprint 13 Carry-Forward

| ID | Task | Size | Reason Deferred |
|----|------|------|-----------------|
| CF-1 | UIOverview + WindowList lightweight tools | M | Not blocking — L1/L2 already prevent overflow |
| CF-2 | CONTEXT_ISOLATION_ENABLED feature flag | S | Low risk without flag |
| CF-3 | E2E validation: 3 complex + 3 simple missions | M | Requires running mission pipeline |
| CF-4 | WSL naming: .openclaw → .vezir | M | WSL infrastructure, separate from Windows code |

### New: Backend Restructure

| ID | Task | Size |
|----|------|------|
| 14.1 | create_app() factory + BaseSettings + lifespan | M |
| 14.2 | Route migration: flat api/ → api/v1/ routers | L |
| 14.3 | Logic migration: inline → services/ layer | L |
| 14.4 | Math Service → backend/services/math/ | S |
| 14.5 | Telegram Bot → backend/services/telegram/ | S |
| 14.6 | pyproject.toml + ruff + mypy setup | M |
| 14.7 | Test restructure: unit/ + integration/ + e2e/ | M |

### New: Frontend Restructure

| ID | Task | Size |
|----|------|------|
| 14.8 | Feature-based layout: features/, components/ui/, api/, hooks/ | L |
| 14.9 | Migrate pages → features/ (dashboard, roles, approvals, missions) | L |
| 14.10 | API client layer + @/ alias + vite proxy | M |
| 14.11 | vitest coverage + Lighthouse regression check | M |

### Tooling

| ID | Task | Size |
|----|------|------|
| 14.12 | Pre-commit hooks (.pre-commit-config.yaml) | S |
| 14.13 | Docker dev environment (Dockerfile.dev + docker-compose.dev.yml) | M |

---

## Execution Plan

```
Phase 1 (CF):  Carry-forward items (CF-1 → CF-4)
Phase 2 (BE):  Backend restructure (14.1 → 14.7)
  MID GATE ─────
Phase 3 (FE):  Frontend restructure (14.8 → 14.11)
Phase 4 (DX):  Tooling + closure (14.12 → 14.13)
```

## Exit Criteria

1. All existing tests pass in new directory structure
2. `create_app()` factory with BaseSettings
3. Feature-based frontend layout
4. ruff + mypy clean
5. Pre-commit hooks operational
6. Docker dev environment starts all 4 services
7. No flat-file imports remaining (all via package paths)

---

## Dependencies

- Sprint 13 closure required before kickoff gate
- Node.js 20 required for frontend work
- Docker Desktop required for 14.13

---

*Sprint 14 — Vezir Platform*
*Created: 2026-03-26*
