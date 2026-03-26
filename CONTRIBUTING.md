# Contributing to Vezir Platform

## Quick Start

```bash
# Backend
cd agent && python -m pytest tests/ -v --timeout=30

# Frontend (requires Node.js 20)
cd frontend && npx tsc --noEmit && npx vitest run

# All tests
bash scripts/test-all.sh
```

## Project Structure

```
agent/           Backend (Python 3.12+)
  api/           FastAPI routes
  app/           Application package (create_app factory)
  events/        EventBus + 13 governance handlers
  mission/       Mission controller, roles, quality gates
  services/      MCP client, risk engine, approval service
  tests/         pytest test suite (353 tests)

frontend/        Frontend (React + TypeScript + Vite)
  src/features/  Feature-based modules
  src/components/ Shared UI components
  src/api/       API client layer
  src/hooks/     React hooks (SSE, polling, mutation)

scripts/         Dev scripts (test-all, dev-backend, dev-frontend)
docs/ai/         Living project docs (STATE, DECISIONS, NEXT)
```

## Conventions

- Python: 4 spaces, line length 100 (ruff)
- TypeScript: 2 spaces, strict mode
- Commits: imperative mood, explain why not what
- Decisions: D-XXX format, frozen once approved
- Tests: every feature ships with tests

## Sprint Process

See `docs/ai/PROCESS-GATES.md` for the full sprint governance model.
