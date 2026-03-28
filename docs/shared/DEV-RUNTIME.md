# Dev Runtime Runbook

**Effective:** Sprint 26+
**Owner:** AKCA

---

## Quick Start

```bash
# One-command startup
docker compose up -d

# Verify health
curl http://127.0.0.1:8003/api/v1/health

# View logs
docker compose logs -f vezir-api

# Stop
docker compose down
```

## Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose v2+
- No other service on port 8003

## Architecture

Single container: `vezir-api` (Python 3.14 + FastAPI + uvicorn on :8003)

## Data Persistence

| Directory | Purpose | Volume Mounted |
|-----------|---------|---------------|
| `agent/missions/` | Mission JSON files | Yes |
| `agent/approvals/` | Approval JSON files | Yes |
| `agent/logs/` | API logs | Yes |

Data survives `docker compose down`. Use `docker compose down -v` to reset.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8003 in use | Stop existing service or change port in docker-compose.yml |
| Build fails | Check `agent/requirements.txt` dependencies |
| Health check fails | Check `docker compose logs vezir-api` for startup errors |
| Import errors | Ensure `agent/` directory structure is intact |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONDONTWRITEBYTECODE` | 1 | Skip .pyc files |
| `PYTHONUNBUFFERED` | 1 | Real-time log output |
| `OPENAI_API_KEY` | — | Required for GPT missions |
| `ANTHROPIC_API_KEY` | — | Required for Claude missions |
