# Sprint 56 File Manifest

## New Files

| File | Purpose | Tests |
|------|---------|-------|
| `agent/persistence/mission_retention.py` | Age+count mission retention policy | 22 |
| `agent/api/retention_api.py` | 5 admin API endpoints (retention + bak) | — |
| `agent/tests/test_mission_retention.py` | Retention policy tests | 22 |
| `tools/cleanup_bak.py` | .bak file scanner + CLI cleanup tool | 22 |
| `agent/tests/test_cleanup_bak.py` | .bak cleanup tests | 22 |
| `agent/mission/intent_mapper.py` | 8-intent mapper (TR+EN) | 27 |
| `agent/tests/test_intent_mapper.py` | Intent mapper tests | 27 |

## Modified Files

| File | Change |
|------|--------|
| `agent/api/server.py` | Added retention_router import + include_router |
| `docs/api/openapi.json` | 85 → 90 endpoints |
| `frontend/src/api/generated.ts` | SDK regenerated for 90 endpoints |

## Closure Artifacts

| Artifact | Path |
|----------|------|
| Closure check output | `docs/sprints/sprint-56/closure-check-output.txt` |
| Review file | `docs/ai/reviews/S56-REVIEW.md` |
| Retrospective | `docs/sprints/sprint-56/retrospective.md` |
| File manifest | `docs/sprints/sprint-56/file-manifest.md` |
