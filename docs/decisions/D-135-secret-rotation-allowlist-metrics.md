# D-135: Secret Rotation + Allowlist + Metrics Contract

**Phase:** Sprint 57 | **Status:** Frozen | **Date:** 2026-04-04

## Context

Sprint 57 introduces three security/operations features that require architectural decisions:
- B-007: Automatic secret rotation (extends D-129 SecretStore)
- B-009: Multi-source allowlist (new authorization layer)
- B-117: Prometheus metrics exposure (new observability endpoint)

## Decisions

### Secret Rotation (B-007)

1. **Rotation Policy:** Age-based with configurable `max_age_days` (default 90) and `warning_threshold_days` (default 14)
2. **Key Versioning:** SHA-256 hash tracking (truncated to 16 hex chars). Raw keys never stored — only hashes for identity verification
3. **Rotation Lifecycle:** `initialize → status → check_due → rotate`. Rotation = re-encrypt all secrets with new key
4. **Fail-safe:** On re-encryption failure, key is rolled back to old value. Metadata not updated on failure
5. **No Auto-rotation:** `auto_rotate` flag exists but rotation requires explicit operator trigger
6. **Metadata:** Persisted atomically (D-071) in `config/secret-rotation-meta.json`
7. **Status States:** ok (within policy), warning (approaching expiry), expired (past max_age), unknown (no metadata)

### Multi-source Allowlist (B-009)

1. **Storage:** YAML files in `config/allowlists/`. Single owner: `AllowlistStore`
2. **Source Types:** `caller_source`, `caller_id`, `caller_role`
3. **Matching Semantics:** Exact match, wildcard (`*` = allow all), prefix (`admin.*` = any value starting with `admin.`)
4. **Fail-open vs Fail-closed:**
   - No allowlist for source type → **open** (allowed, no restrictions)
   - Allowlist exists but value not matched → **closed** (denied)
5. **Disabled Entries:** Transparently skipped (as if not present)
6. **Ambiguity Resolution:** First matching entry wins. Multiple allowlists for same source_type: value must appear in at least one
7. **Write Authority:** Thread-safe CRUD with write lock. Atomic YAML writes (D-071 pattern)

### Prometheus Metrics (B-117)

1. **Endpoint:** `/api/v1/metrics` (Prometheus text format), `/api/v1/metrics/json` (JSON)
2. **Auth:** No authentication required — localhost-only binding per D-070
3. **Data Sources:** MissionStore (mission counts/status) and MetricStore (performance). No new data collection
4. **Dashboards:** 3 Grafana JSON templates in `config/grafana/` — missions, policy/security, API/infra
5. **Validation:** `tools/grafana_setup.py --validate` ensures all dashboard JSONs are well-formed

## Consequences

- Secret rotation extends D-129 without breaking existing SecretStore contract
- Allowlist is additive — no existing behavior changes when no allowlists are configured
- Metrics endpoint is read-only, no write surface exposed
