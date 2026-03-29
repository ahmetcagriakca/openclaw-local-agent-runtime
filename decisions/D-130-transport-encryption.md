# D-130: Transport Encryption Contract

**ID:** D-130
**Status:** Frozen
**Phase:** 7 / Sprint 37
**Date:** 2026-03-29

---

## Context

API server on `127.0.0.1:8003` serves plaintext HTTP. No transport encryption. B-011 requires TLS enforcement.

## Decision

### TLS Configuration
- Protocol: TLS 1.2+ only (reject SSLv3, TLS 1.0, TLS 1.1)
- Certificate source: `config/tls/server.pem` (cert) + `config/tls/server-key.pem` (private key)
- HSTS header: `Strict-Transport-Security: max-age=31536000` when TLS active

### Mode Matrix

| Mode | Cert Present | Behavior |
|------|-------------|----------|
| Default (production) | Yes | Serve HTTPS on :8003 |
| Default (production) | No | **Startup DENY** — refuse to serve, exit 1 |
| Dev (`--dev` or `VEZIR_DEV=1`) | Yes | Serve HTTPS on :8003 |
| Dev (`--dev` or `VEZIR_DEV=1`) | No | Serve HTTP with warning log (explicit insecure) |

### B-011 Closure Condition
- B-011 is closeable when: default mode requires TLS, server refuses to start without valid cert in non-dev mode
- Dev-mode HTTP fallback does NOT satisfy B-011 — it is an explicit opt-in for local development only

### Dev Certificate Generation
- Tool: `tools/generate-dev-cert.sh`
- Generates self-signed cert valid for 365 days
- Subject: `CN=localhost`
- Output: `config/tls/server.pem` + `config/tls/server-key.pem`

### Impacted Files

| File | Change |
|------|--------|
| `agent/api/server.py` | Add TLS params to uvicorn startup, dev-mode flag |
| `tools/generate-dev-cert.sh` | Self-signed cert generator |
| `agent/tests/test_transport_encryption.py` | TLS tests |

### Validation Method
- Test: TLS active with cert → HTTPS works
- Test: No cert + default mode → startup exit 1
- Test: No cert + dev mode → HTTP with warning
- Test: TLS 1.2+ enforced
- Test: HSTS header present

### Rollback Condition
- If TLS enforcement breaks existing CI/test pipelines, revert to HTTP-only and keep D-130 frozen for re-implementation with proper CI cert provisioning.

## Consequences
- API server is encrypted in transit by default
- Dev mode explicitly opts into insecure HTTP
- HSTS prevents downgrade attacks
