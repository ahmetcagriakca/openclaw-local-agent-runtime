# Sprint 57 File Manifest

## New Files

| File | Purpose | Tests |
|------|---------|-------|
| `agent/services/secret_rotation.py` | Secret rotation service (B-007) | 28 |
| `agent/api/secret_rotation_api.py` | Rotation API (4 endpoints) | — |
| `agent/tests/test_secret_rotation.py` | Rotation tests | 28 |
| `agent/services/allowlist_store.py` | Allowlist store (B-009) | 24 |
| `agent/api/allowlist_api.py` | Allowlist API (7 endpoints) | — |
| `agent/tests/test_allowlist.py` | Allowlist tests | 24 |
| `agent/api/metrics_api.py` | Prometheus metrics endpoint (B-117) | — |
| `agent/tests/test_grafana_dashboards.py` | Dashboard + metrics tests | 30 |
| `config/grafana/vezir-missions.json` | Grafana missions dashboard | — |
| `config/grafana/vezir-policy.json` | Grafana policy/security dashboard | — |
| `config/grafana/vezir-api.json` | Grafana API/infra dashboard | — |
| `tools/grafana_setup.py` | Dashboard validation + provisioning tool | — |
| `docs/decisions/D-135-secret-rotation-allowlist-metrics.md` | Decision record | — |

## Modified Files

| File | Change |
|------|--------|
| `agent/api/server.py` | +3 routers (secret_rotation, allowlist, metrics) |
| `docs/api/openapi.json` | 90 → 103 endpoints |
| `frontend/src/api/generated.ts` | SDK regenerated |
| `docs/ai/DECISIONS.md` | D-135 added |

## Closure Artifacts

| Artifact | Path |
|----------|------|
| Closure check | `docs/sprints/sprint-57/closure-check-output.txt` |
| Retrospective | `docs/sprints/sprint-57/retrospective.md` |
| File manifest | `docs/sprints/sprint-57/file-manifest.md` |
| Review | `docs/ai/reviews/S57-REVIEW.md` |
| Decision | `docs/decisions/D-135-secret-rotation-allowlist-metrics.md` |
