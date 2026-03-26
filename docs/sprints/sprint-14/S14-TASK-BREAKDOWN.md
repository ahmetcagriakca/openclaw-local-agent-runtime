# Sprint 14 — Task Breakdown (Phase 6A: Structural Hardening)

**Date:** 2026-03-26
**Phase:** 6A — Backend & Frontend Restructure
**Goal:** Layered architecture, dev tooling, carry-forward completion.
**implementation_status:** not_started
**closure_status:** not_started

---

## Carry-Forward from Sprint 13

### CF-1: UIOverview + WindowList tools (M)

Create lightweight MCP tools that return UI state without full screenshot.

| Subtask | Description |
|---------|-------------|
| CF-1a | UIOverview tool: focused window elements (≤30), names only, no coordinates |
| CF-1b | WindowList tool: window titles + dimensions + focused flag |
| CF-1c | Unit tests for both tools |
| CF-1d | Update analyst/architect prompts: prefer UIOverview over Snapshot |

**Acceptance:** UIOverview ≤1500 tokens, WindowList ≤300 tokens.

### CF-2: Feature flag CONTEXT_ISOLATION_ENABLED (S)

Add config flag to toggle L1/L2 isolation. Default: true.

### CF-3: E2E validation missions (M)

Run 3 complex + 3 simple missions through the pipeline. Verify:
- Developer stage input ≤30K tokens
- No context overflow
- Mission completes successfully

### CF-4: WSL naming cleanup (M)

Rename `.openclaw` → `.vezir` in WSL. Symlink for backward compat.

---

## Track A: Backend Restructure

### 14.1: create_app() factory + BaseSettings (M)

```
agent/app/__init__.py        # create_app() factory
agent/app/config.py          # BaseSettings with env override
agent/app/lifespan.py        # startup/shutdown lifecycle
```

- Move current `server.py` app creation into factory
- Environment-based config (PORT, LOG_LEVEL, etc.)
- Lifespan context manager for startup checks

### 14.2: Route migration → api/v1/ routers (L)

```
agent/app/api/v1/missions.py    # from api/mission_api.py
agent/app/api/v1/roles.py       # from api/roles_api.py
agent/app/api/v1/health.py      # from api/health_api.py
agent/app/api/v1/approvals.py   # from api/approval_api.py
agent/app/api/v1/events.py      # from api/sse_endpoints.py
agent/app/api/v1/mutations.py   # from api/mission_mutation_api.py
```

- Each router is a separate module with `router = APIRouter()`
- `create_app()` includes all routers under `/api/v1/`
- Old imports redirect to new paths (temporary compat)

### 14.3: Logic → services/ layer (L)

```
agent/app/services/normalizer.py    # from api/normalizer.py
agent/app/services/health.py        # from api/health_api.py (logic)
agent/app/services/capabilities.py  # from api/capabilities.py
```

- Routes call services, services contain business logic
- No direct file I/O in route handlers

### 14.4: Math Service → services/math/ (S)

Move `agent/math_service/` → `agent/app/services/math/`.
Update imports and test paths.

### 14.5: Telegram Bot → services/telegram/ (S)

Move `agent/telegram_bot.py` → `agent/app/services/telegram/bot.py`.
Update imports.

### 14.6: pyproject.toml + ruff + mypy (M)

```toml
[project]
name = "vezir-backend"
requires-python = ">=3.12"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
warn_return_any = true

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### 14.7: Test restructure (M)

```
agent/tests/unit/           # fast, no I/O
agent/tests/integration/    # API client tests
agent/tests/e2e/            # full pipeline tests
```

Move existing tests into appropriate directories. Update conftest.

---

## Mid-Review Gate

| Check | Criterion |
|-------|-----------|
| All backend tests pass | `pytest tests/ -v` |
| Imports clean | No `from api.xxx` outside compat shims |
| create_app() works | `python -c "from app import create_app; print('OK')"` |
| ruff clean | `ruff check agent/` |

---

## Track B: Frontend Restructure

### 14.8: Feature-based layout (L)

```
frontend/src/
  features/
    dashboard/
    missions/
    approvals/
    roles/
  components/ui/       # shared UI components
  api/                 # API client layer
  hooks/               # shared hooks
  types/               # shared types
  layouts/             # page layouts
  lib/                 # utilities
```

### 14.9: Migrate pages → features/ (L)

- Each feature: `index.tsx`, `components/`, `hooks/`, `types/`
- Barrel exports from each feature
- No cross-feature direct imports

### 14.10: API client + @/ alias + vite proxy (M)

- Centralized `api/client.ts` with typed methods
- `@/` path alias in tsconfig + vite
- Vite proxy `/api` → `localhost:8003`

### 14.11: Coverage + Lighthouse regression (M)

- `npx vitest run --coverage`
- Lighthouse score comparison vs Sprint 12 baseline
- Target: accessibility ≥95, no regression

---

## Track C: Tooling

### 14.12: Pre-commit hooks (S)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff
      - id: mypy
      - id: tsc
```

### 14.13: Docker dev environment (M)

```yaml
# docker-compose.dev.yml
services:
  api:      # Vezir API on :8003
  ui:       # Vezir UI on :3000
  math:     # Math Service on :9000
  telegram: # Telegram Bot
```

---

## Track D: Closure

### 14.REPORT: Final review report
### 14.RETRO: Sprint retrospective
### 14.CLOSURE: Closure summary

---

## Evidence Checklist

| # | Evidence | Task |
|---|----------|------|
| 1 | backend-structure-after.txt | 14.2 |
| 2 | backend-tests-after.txt | 14.7 |
| 3 | ruff-output.txt | 14.6 |
| 4 | mypy-output.txt | 14.6 |
| 5 | frontend-structure-after.txt | 14.9 |
| 6 | frontend-tests-after.txt | 14.11 |
| 7 | frontend-coverage.txt | 14.11 |
| 8 | lighthouse-comparison.txt | 14.11 |
| 9 | docker-compose-test.txt | 14.13 |
| 10 | create-app-verify.txt | 14.1 |
| 11 | uioverview-token-test.txt | CF-1 |
| 12 | mission-validation.txt | CF-3 |

---

## Implementation Notes

| Task | Planned | Implemented | Why Different |
|------|---------|-------------|---------------|
| CF-1 → 14.13 | — | — | — |

## File Manifest

| File | Action | Task |
|------|--------|------|
| agent/app/__init__.py | Create | 14.1 |
| agent/app/config.py | Create | 14.1 |
| agent/app/api/v1/*.py | Create | 14.2 |
| agent/app/services/*.py | Create | 14.3 |
| pyproject.toml | Create | 14.6 |
| .pre-commit-config.yaml | Create | 14.12 |
| docker-compose.dev.yml | Create | 14.13 |
| frontend/src/features/ | Create | 14.8 |
| frontend/src/api/ | Create | 14.10 |

---

*Sprint 14 Task Breakdown — Vezir Platform*
*Created: 2026-03-26*
