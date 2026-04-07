# Vezir Platform — Architecture Overview

**Auto-generated:** 2026-04-04 10:02 UTC

---

## System Overview

Vezir is a governed multi-agent mission platform that orchestrates
9 specialist AI roles through a quality-gated, 11-state mission
state machine. It integrates 3 LLM providers (GPT-4o, Claude Sonnet,
Ollama) and 24 MCP tools via a Windows bridge.

## Component Map

```
+------------------+     +------------------+     +------------------+
|  Vezir UI (4000) |<--->| Vezir API (8003) |<--->| Mission Controller|
|  React + Vite    |     | FastAPI + Uvicorn |     | 9 roles, 3 gates |
+------------------+     +------------------+     +------------------+
                              |                          |
                              v                          v
                    +------------------+     +------------------+
                    | SSE Manager      |     | Policy Engine    |
                    | Live updates     |     | YAML rules       |
                    +------------------+     +------------------+
                              |                          |
                              v                          v
                    +------------------+     +------------------+
                    | Persistence      |     | LLM Providers    |
                    | JSON file store  |     | GPT/Claude/Ollama|
                    +------------------+     +------------------+
                              |                          |
                              v                          v
                    +------------------+     +------------------+
                    | Observability    |     | WMCP Bridge(8001)|
                    | OTel + Alerts    |     | 24 MCP tools     |
                    +------------------+     +------------------+
```

## Port Map

| Port | Service | Protocol |
|------|---------|----------|
| 4000 | Vezir UI (React + Vite + Tailwind) | HTTP |
| 8001 | WMCP (Windows MCP Proxy) | HTTP |
| 8003 | Vezir API (FastAPI + Uvicorn) | HTTP/HTTPS |
| 9000 | Math Service (example) | HTTP |

## Mission State Machine

11 states with governed transitions:

```
CREATED -> PLANNING -> READY -> RUNNING -> COMPLETED
                                  |
                                  +-> FAILED
                                  +-> TIMED_OUT
                                  +-> WAITING_APPROVAL -> RUNNING
                                  +-> PAUSED -> RUNNING
                                  +-> CANCELLED
```

## Specialist Roles (9)

| # | Role | Responsibility |
|---|------|---------------|
| 1 | Planner | Mission decomposition, stage planning |
| 2 | Researcher | Information gathering, context building |
| 3 | Coder | Code generation, modification |
| 4 | Reviewer | Quality review, gate enforcement |
| 5 | Tester | Test execution, validation |
| 6 | Deployer | Deployment, environment management |
| 7 | Documenter | Documentation generation |
| 8 | Optimizer | Performance optimization |
| 9 | Security | Security analysis, vulnerability scanning |

## Quality Gates (3)

| Gate | Trigger | Action |
|------|---------|--------|
| G1 — Planning Gate | After PLANNING | Validates stage plan completeness |
| G2 — Execution Gate | After each stage | Validates stage output quality |
| G3 — Final Gate | Before COMPLETED | Validates all artifacts, coverage |

## Governance

- 132+ frozen architectural decisions (D-001 to D-133)
- 18-step sprint closure checklist (Rule 16)
- File-persisted state (atomic writes: temp -> fsync -> os.replace)
- EventBus: 37 event types, internal/test infrastructure (D-147, not wired to production startup)
- Alert engine: 9 rules with Telegram notification

## Data Flow

1. **Request** arrives via Dashboard UI or Telegram
2. **Mission Create API** writes mission JSON, spawns controller thread
3. **Controller** plans stages via Planner role
4. **Quality Gate G1** validates the plan
5. **Per-stage execution**: policy check -> role dispatch -> LLM call -> tool use
6. **Quality Gate G2** validates each stage output
7. **Quality Gate G3** validates final mission
8. **SSE events** broadcast state changes to UI in real-time
9. **Observability layer** records traces, metrics, structured logs

## Key Technologies

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.14, FastAPI, Pydantic V2 |
| Frontend | React 18, Vite, Tailwind CSS, TypeScript |
| LLM | GPT-4o (OpenAI), Claude Sonnet (Anthropic), Ollama (local) |
| Observability | OpenTelemetry (traces + metrics), structured JSON logs |
| CI/CD | GitHub Actions (7 workflows), branch protection |
| Testing | pytest (backend), Vitest (frontend), Playwright (E2E) |
