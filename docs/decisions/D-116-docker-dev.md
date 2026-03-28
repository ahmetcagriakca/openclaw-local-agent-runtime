# D-116: Docker Dev Runtime Topology

**Phase:** 6 (Sprint 26)
**Status:** Frozen
**Date:** 2026-03-28

---

## Decision

Single-service Docker Compose configuration for local development. Vezir API runs in a container with volume mounts for live data.

## Topology

```
docker-compose.yml
└── vezir-api (Python 3.14 + FastAPI + uvicorn)
    ├── Port: 8003
    ├── Health: /api/v1/health (10s interval)
    ├── Volumes: missions/, approvals/, logs/
    └── Auto-restart: unless-stopped
```

## Usage

```bash
# Start
docker compose up -d

# Health check
curl http://127.0.0.1:8003/api/v1/health

# Logs
docker compose logs -f

# Stop
docker compose down
```

## Design Choices

1. **Single service** — no database, no message queue. Vezir uses file-based persistence.
2. **Volume mounts** — missions/approvals/logs persist across container restarts.
3. **Python 3.14-slim** — matches CI environment.
4. **No LLM provider config** — API keys are passed via environment variables when needed.
5. **Health check built-in** — Docker and compose both check /api/v1/health.

## Future Extensions

- Add Jaeger container for tracing (when D-XXX for observability stack)
- Add frontend container (when needed for full-stack dev)
- Add seed data script for development fixtures
