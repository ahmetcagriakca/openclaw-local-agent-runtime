# D-118: Plugin Runtime Contract

**Phase:** 6 (Sprint 29)
**Status:** Frozen
**Date:** 2026-03-28

---

## Decision

File-based plugin system with JSON manifest, EventBus integration, and config-driven loading. Plugins are Python modules that register handlers for specific event types.

## Plugin Manifest Schema

Each plugin has a `manifest.json`:

```json
{
  "name": "webhook-notifications",
  "version": "1.0.0",
  "description": "Send webhook notifications on mission events",
  "author": "vezir",
  "handlers": [
    {
      "event_type": "mission_completed",
      "handler": "on_mission_completed",
      "priority": 500
    },
    {
      "event_type": "mission_failed",
      "handler": "on_mission_failed",
      "priority": 500
    }
  ],
  "config_schema": {
    "webhook_url": {"type": "string", "required": true},
    "events": {"type": "array", "required": false}
  }
}
```

## Registration/Discovery Model

1. Plugins live in `agent/plugins/<plugin-name>/`
2. Each plugin directory contains `manifest.json` + Python handler module
3. Plugin config lives in `config/plugins/<plugin-name>.json`
4. Registry scans `agent/plugins/` at startup, validates manifests
5. Enabled plugins have a config file in `config/plugins/`

## Handler Lifecycle

```
1. LOAD    — Registry finds plugin directories, reads manifests
2. VALIDATE — Manifest schema checked, handler module imported
3. INIT    — Plugin init() called with config (if defined)
4. REGISTER — Handlers registered on EventBus with specified priorities
5. EXECUTE — EventBus dispatches events to registered handlers
6. TEARDOWN — Plugin cleanup() called on shutdown (if defined)
```

## Execution Boundary

1. **Timeout:** Each handler call has a 30-second timeout
2. **Error isolation:** Handler exceptions are caught and logged, never crash the bus
3. **No halt:** Plugin handlers cannot halt event propagation (priority 500+ only)
4. **Async safe:** Handlers may be sync or async

## Config/Loading Rules

1. Plugin without config file = disabled (not loaded)
2. Config file with `{"enabled": false}` = disabled
3. Invalid manifest = skipped with warning log
4. Missing handler module = skipped with error log
5. Config validated against manifest `config_schema`

## Security Constraints

1. Plugins cannot access EventBus internal state
2. Plugins receive Event data (read-only copy)
3. Plugins cannot register additional handlers at runtime
4. Plugin handlers run at priority 500+ (after governance handlers)
5. No direct file system access outside plugin directory
6. HTTP calls allowed (webhooks) but with timeout enforcement

## Directory Structure

```
agent/plugins/
├── registry.py         # Plugin loading and registration
├── executor.py         # Handler dispatch with timeout/error isolation
├── manifest.py         # Manifest schema validation
└── webhooks/           # Reference plugin
    ├── manifest.json
    ├── handler.py
    └── __init__.py
```

## Impact

- EventBus: add plugin handler registration path
- Config: `config/plugins/` directory for plugin configs
- Tests: plugin loading + dispatch tests
