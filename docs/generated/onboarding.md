# Vezir Platform — Developer Onboarding Guide

**Auto-generated:** 2026-04-04 09:53 UTC

---

## Prerequisites

- **OS:** Windows 11 with WSL2
- **Python:** 3.14+
- **Node.js:** 20+
- **Git:** 2.40+

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/ahmetcagriakca/vezir.git
cd vezir
```

### 2. Backend setup

```bash
cd agent
pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Start services

```bash
# Terminal 1: Backend API
cd agent && python -m api.server

# Terminal 2: Frontend dev server
cd frontend && npm run dev
```

The API runs on http://127.0.0.1:8003, UI on http://localhost:3000.

## Running Tests

### Backend (pytest)

```bash
cd agent && python -m pytest tests/ -v
```

### Frontend (Vitest)

```bash
cd frontend && npx vitest run
```

### TypeScript check

```bash
cd frontend && npx tsc --noEmit
```

### Playwright E2E

```bash
cd frontend && npx playwright test
```

### All-in-one preflight

```bash
bash tools/preflight.sh
```

## Project Structure

```
vezir/
  agent/                  # Python backend
    api/                  # FastAPI routers (~82 endpoints)
    mission/              # Mission controller, state machine, roles
    events/               # EventBus (28 event types)
    observability/        # OTel tracing, metrics, alerts
    persistence/          # JSON file stores
    services/             # Risk engine, approval, etc.
    auth/                 # Session, middleware, isolation
    tests/                # Backend test suite
  frontend/               # React dashboard
    src/api/              # Generated API client (from OpenAPI)
    src/components/       # React components
    src/pages/            # Route pages
  config/
    policies/             # YAML policy rules
    templates/            # Mission presets
    tls/                  # TLS certificates
  tools/                  # CLI tools (export, generate, audit)
  docs/
    ai/                   # Governance docs (STATE, NEXT, DECISIONS)
    api/                  # OpenAPI spec
    generated/            # Auto-generated docs (this tool)
  bridge/                 # PowerShell MCP bridge
```

## Key Conventions

- **Atomic writes:** Always use `atomic_write_json()` — never write directly
- **Decisions:** Frozen as D-XXX in `docs/ai/DECISIONS.md`
- **Commit format:** `Sprint N Task X.Y: <description>`
- **Tests required:** Every feature must have tests before merge
- **OpenAPI sync:** Run `python tools/export_openapi.py` after API changes
- **SDK sync:** Run `cd frontend && npm run generate:api` after OpenAPI update

## API Authentication

Mission creation requires an `Authorization: Bearer <token>` header.
In development, the token is configured via environment variable.

## Useful Commands

```bash
# Export OpenAPI spec
cd agent && python ../tools/export_openapi.py

# Regenerate frontend API types
cd frontend && npm run generate:api

# Generate documentation
python tools/generate_docs.py

# Run benchmark (evidence only)
python tools/benchmark_api.py

# Generate backlog from GitHub
python tools/generate-backlog.py
```

## Getting Help

- System state: `docs/ai/STATE.md`
- Roadmap: `docs/ai/NEXT.md`
- Decisions: `docs/ai/DECISIONS.md`
- Governance: `docs/ai/GOVERNANCE.md`
- Backlog: `docs/ai/BACKLOG.md`
