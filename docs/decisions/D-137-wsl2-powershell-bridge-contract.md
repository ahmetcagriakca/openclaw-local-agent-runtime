# D-137: WSL2 <-> PowerShell Bridge Contract

**Phase:** Sprint 60 | **Status:** Frozen | **Date:** 2026-04-05

## Context

Vezir has a Windows-first deterministic execution layer (PowerShell runtime, WMCP server) plus WSL2-based components (Telegram bot, Vezir gateway). This creates a hard trust boundary. Cross-environment execution must be forced through one canonical governed path to structurally guarantee fail-closed execution.

## Decision

### Canonical Bridge Paths (ALLOWED)

1. **oc-bridge.ps1** — Stateless PowerShell entrypoint (Phase 1.5-C/D/E frozen)
   - Operations: submit_task, get_task_status, cancel_task, get_health
   - Invoked via WSL wrappers: oc-bridge-call, oc-bridge-submit, oc-bridge-status, oc-bridge-cancel, oc-bridge-health
   - Enforcement: allowlist, audit log, fail-closed, 30s timeout

2. **WMCP HTTP transport** — MCP server on localhost:8001
   - Python client: `agent/services/mcp_client.py` -> `POST /PowerShell`
   - All tool_catalog PowerShell commands route through this path
   - No shell escaping — HTTP boundary isolation

3. **Tool catalog templates** — `agent/services/tool_catalog.py`
   - PowerShell commands defined as templates
   - Executed via mcp_client.execute_powershell() only
   - Risk classification via risk_engine.py

### Denied Paths (REMOVED)

All direct WSL subprocess calls (`wsl -d Ubuntu-E`) from Python agent code are removed:
- `agent/services/approval_service.py` — WSL token resolution fallback
- `agent/telegram_bot.py` — WSL token resolution fallback
- `agent/api/health_api.py` — WSL token resolution fallback

These fallbacks are replaced by mandatory env var configuration (`OC_TELEGRAM_BOT_TOKEN`).

### Contract Requirements

| Property | Value |
|----------|-------|
| Request schema | JSON with operation, source, sourceUserId, requestId (+ operation-specific fields) |
| Response schema | JSON with status (accepted/rejected/error/in_progress/completed/acknowledged) |
| Timeout | 30s per runtime script invocation (configurable) |
| Stdout/stderr | Captured and parsed, stderr for diagnostics only |
| Exit codes | 0=success, 1=rejection/error, 2=startup failure |
| Path normalization | Resolved via `$ocRoot` relative paths |
| Filesystem scope | Bridge root + bin/ scripts only, no arbitrary path access |
| Credential handling | Env vars only, no secrets in request JSON or audit logs |
| Audit events | Every request emits to bridge-audit.jsonl (JSONL format) |
| AuthZ enforcement | Allowlist-based, fail-closed (missing/empty allowlist = exit 2) |
| Malformed request | Rejected with INVALID_INPUT error code |
| Unknown operation | Rejected with INVALID_INPUT error code |
| Non-canonical calls | DENIED — no direct subprocess calls to wsl/powershell from agent code |

### Non-Negotiable Doctrines

1. Every cross-environment execution request goes through the canonical bridge or WMCP HTTP
2. No direct PowerShell invocation from mission/runtime paths outside the bridge
3. Timeout or malformed bridge request fails closed
4. Every bridge request emits an auditable event
5. Path scope is explicit, normalized, and enforced before execution
6. Secrets must not leak into prompts, logs, or evidence packets

## Consequences

- Telegram bot token must be pre-configured via env var (no WSL fallback)
- All new cross-environment execution must use mcp_client or bridge wrappers
- Bridge contract changes require a new decision record amendment

## References

- Phase 1.5-C: Bridge contract (frozen)
- Phase 1.5-D: Bridge security baseline (frozen)
- Phase 1.5-E: Bridge implementation report (frozen)
- D-092: Telegram approval deprecation
- D-083: WMCP degradation policy
