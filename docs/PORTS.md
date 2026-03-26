# Vezir Platform — Port Registry

| Port | Service | Status | Notes |
|------|---------|--------|-------|
| 3000 | Vezir UI (React/Vite) | Active | Frontend dashboard |
| 8001 | WMCP (Windows MCP Proxy) | Active | 18 MCP tools |
| 8002 | — | Removed | Was legacy health dashboard (D-097) |
| 8003 | Vezir API (FastAPI) | Active | 14 endpoints, primary backend |
| 9000 | Math Service | Active | Example deployable service |

All services bind to `127.0.0.1` (localhost only).
