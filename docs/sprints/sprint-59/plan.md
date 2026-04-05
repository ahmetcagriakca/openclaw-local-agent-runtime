# Sprint 59 — B-118 Plugin Marketplace / Discovery

**Model:** A (full closure)
**Phase:** 7
**Decision:** D-136 (Plugin Marketplace + Installer Contract)
**Scope:** Single feature — B-118 Plugin marketplace / discovery

---

## Goal

Build plugin marketplace store, lifecycle API, and installer with hot-reload on top of existing plugin infrastructure (D-118: PluginRegistry, PluginManifest, PluginExecutor, EventBus).

## Dependencies

- D-118 Plugin Runtime Contract (S29) — manifest schema, registry, executor
- D-106 Persistence Model — JSON file store
- D-108 Session/Auth — single-operator (no auth required)
- Existing: `agent/plugins/registry.py`, `agent/plugins/manifest.py`, `agent/plugins/executor.py`, `agent/events/bus.py`, `tools/scaffold_template.py`

## Blocking Risks

- Installer mutation must be isolated in Task 59.3 with fail-closed semantics
- Invalid manifest must never be installed (reject + 422)
- EventBus hot-reload must not break existing handlers

---

## Task Breakdown

### Task 59.1: Plugin Marketplace Store + Discovery (#317)

**Scope:** PluginMarketplaceStore class with metadata CRUD, search, filter, install state tracking.

**Input:** Plugin manifest JSON files from `agent/plugins/*/manifest.json`
**Output:** Store with search/filter/CRUD API

**Acceptance Criteria:**
- [ ] PluginMarketplaceStore indexes all discovered plugins from PluginRegistry
- [ ] Search by name, tag, category returns correct results
- [ ] Filter by status (available/installed/enabled/disabled) works
- [ ] Install state transitions: available → installed → enabled/disabled
- [ ] Plugin detail includes: name, version, description, author, capabilities, risk_tier, source, trust_status
- [ ] Invalid/missing manifest fields → plugin listed with risk_tier="high", trust_status="unknown"
- [ ] Store persisted via atomic_write_json
- [ ] 25 tests pass

**New file:** `agent/services/plugin_marketplace.py`

---

### Task 59.2: Plugin Lifecycle API (#318)

**Scope:** 10 FastAPI endpoints per D-136 contract.

**Input:** HTTP requests
**Output:** JSON responses per RFC 9457 error envelope

**Endpoint Inventory:**

| # | Method | Path | R/W | Auth | Task |
|---|--------|------|-----|------|------|
| 1 | GET | /api/v1/plugins | R | None | 59.2 |
| 2 | GET | /api/v1/plugins/search | R | None | 59.2 |
| 3 | GET | /api/v1/plugins/{id} | R | None | 59.2 |
| 4 | POST | /api/v1/plugins/{id}/install | W | None | 59.3 |
| 5 | POST | /api/v1/plugins/{id}/uninstall | W | None | 59.3 |
| 6 | POST | /api/v1/plugins/{id}/enable | W | None | 59.3 |
| 7 | POST | /api/v1/plugins/{id}/disable | W | None | 59.3 |
| 8 | PUT | /api/v1/plugins/{id}/config | W | None | 59.3 |
| 9 | GET | /api/v1/plugins/events | R | None | 59.2 |
| 10 | GET | /api/v1/plugins/stats | R | None | 59.2 |

**Acceptance Criteria:**
- [ ] All 6 read endpoints return 200 with correct JSON
- [ ] 4 write endpoints registered but delegate to installer (Task 59.3)
- [ ] Search supports query param `q` for name/description
- [ ] Filter supports query params `status`, `category`
- [ ] Detail endpoint returns full plugin metadata per D-136
- [ ] 404 for unknown plugin ID
- [ ] OpenAPI schema updated (docs/api/openapi.json)
- [ ] Frontend SDK regenerated (frontend/src/api/generated.ts)
- [ ] 25 tests pass

**New file:** `agent/api/plugins_api.py`
**Modified:** `agent/api/server.py` (+1 router)

---

### Task 59.3: Plugin Installer + Hot-Reload (#319)

**Scope:** PluginInstaller class with install/uninstall/enable/disable logic, EventBus hot-reload, scaffold integration.

**Input:** Plugin ID from marketplace store
**Output:** Installed plugin in PluginRegistry, handlers in EventBus

**Acceptance Criteria:**
- [ ] Install: validate manifest → register in PluginRegistry → create config → register EventBus handlers → update store state
- [ ] Uninstall: deregister handlers → remove config → deregister from registry → update store state
- [ ] Enable/disable: toggle config enabled flag → register/deregister handlers
- [ ] Invalid manifest → 422 fail-closed (no partial install)
- [ ] Already installed → 409
- [ ] Not installed → 404 on uninstall
- [ ] Concurrent install same plugin → lock prevents race
- [ ] EventBus handlers registered at priority 500+ (no restart needed)
- [ ] scaffold_template.py creates marketplace-compatible plugin
- [ ] All events logged to plugin event store
- [ ] 20 tests pass

**New file:** `agent/services/plugin_installer.py`

---

## Verification Commands

```bash
cd agent && python -m pytest tests/test_plugin_marketplace.py -v
cd frontend && npx tsc --noEmit
cd frontend && npx vitest run
cd agent && python -m ruff check .
```

## Expected Evidence

- `pytest-output.txt` — 70+ new tests pass
- `tsc-output.txt` — 0 TS errors
- `vitest-output.txt` — 217+ frontend tests pass
- `lint-output.txt` — 0 ruff errors
- `closure-check-output.txt` — full closure check

## Exit Criteria

- [ ] All 70 tests pass
- [ ] 10 API endpoints operational
- [ ] OpenAPI schema updated to ~133 endpoints
- [ ] D-136 contract fully implemented
- [ ] No regressions in existing 1530 tests
