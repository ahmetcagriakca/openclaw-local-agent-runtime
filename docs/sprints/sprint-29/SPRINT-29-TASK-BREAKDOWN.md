# Sprint 29 — Task Breakdown

**Sprint:** 29
**Phase:** 6
**Title:** Plugin Foundation + Webhook + Auth UI
**Model:** A

**Goal:** Freeze plugin runtime contract (D-118), implement plugin registry, deliver webhook notifications as reference plugin, add auth session management UI, expand frontend tests.

---

## Track 1: Plugin Architecture

**29.1 — D-118 Plugin Runtime Contract Freeze**

Define plugin manifest, registration/discovery, handler lifecycle, execution boundary, config/loading rules, security constraints.

**Repo scope:** `docs/ai/DECISIONS.md`, `docs/decisions/`
**Branch:** `sprint-29/t29.1-plugin-contract`

**Implementation:**
1. Define plugin manifest schema (name, version, handlers, config)
2. Define registration/discovery model (file-based, config-driven)
3. Define handler lifecycle (load, init, execute, teardown)
4. Define execution boundary (sandboxing, timeout, error isolation)
5. Define security constraints (no direct DB/file access, API-only)
6. Freeze as D-118

**Acceptance:** D-118 frozen, no ambiguity in contract

---

**29.2 — Backend plugin registry + custom handler execution**

Implement plugin loading, registration, and dispatch based on D-118.

**Repo scope:** `agent/plugins/`
**Branch:** `sprint-29/t29.2-plugin-registry`
**Depends on:** 29.1

**Implementation:**
1. Create `agent/plugins/registry.py` — load plugins from config, register handlers
2. Create `agent/plugins/executor.py` — dispatch events to registered handlers
3. Create `agent/plugins/manifest.py` — validate plugin manifest schema
4. Wire into EventBus as plugin event consumer
5. Add plugin tests

**Acceptance:** Plugin registry loads, validates, and dispatches to handlers

---

## Gates

**29.G1 — Mid Review Gate**

After Track 1. Branch-exempt.

---

## Track 2: Reference Plugin + Auth UI + Tests

**29.3 — Webhook notifications as reference plugin**

First real plugin: Slack/Discord webhook notifications on mission events.

**Repo scope:** `agent/plugins/webhooks/`, `config/`
**Branch:** `sprint-29/t29.3-webhook-plugin`
**Depends on:** 29.G1

**Implementation:**
1. Create webhook plugin manifest
2. Implement webhook handler (HTTP POST to configured URL)
3. Support mission_completed, mission_failed, approval_pending events
4. Config: `config/plugins/webhooks.json` with URL + events
5. Add tests with mock HTTP

**Acceptance:** Webhook fires on mission events, config-driven, testable

---

**29.4 — Auth session management UI**

Frontend UI for viewing active sessions, expiration, and revocation.

**Repo scope:** `frontend/src/`
**Branch:** `sprint-29/t29.4-session-ui`
**Depends on:** 29.G1

**Implementation:**
1. Session list component showing active API keys (name, role, expires)
2. Expiration visibility (days remaining, expired badge)
3. Visual indicators for key status
4. Add component tests

**Acceptance:** Session list renders, expiration visible, tests pass

---

**29.5 — Frontend component test expansion**

Cover plugin/webhook/auth UI components.

**Repo scope:** `frontend/src/__tests__/`
**Branch:** `sprint-29/t29.5-component-tests`
**Depends on:** 29.G1

**Implementation:**
1. Tests for session management UI
2. Tests for webhook config display (if applicable)
3. Target: 80+ total frontend tests

**Acceptance:** 10+ new tests, 77+ total

---

**29.G2 — Final Review Gate**
**29.RETRO — Retrospective**
**29.CLOSURE — Sprint Closure**

---

## Decisions to Freeze

| ID | Topic | When |
|----|-------|------|
| D-118 | Plugin runtime contract | Before 29.2 |

## Carry-Forward

| Item | Target |
|------|--------|
| Mission templates/presets | S30+ |
| Cost tracking/billing | S30+ |

## Output Files

| Task | Output |
|------|--------|
| 29.1 | `docs/decisions/D-118-plugin-contract.md` |
| 29.2 | `agent/plugins/registry.py`, `executor.py`, `manifest.py` |
| 29.3 | `agent/plugins/webhooks/` |
| 29.4 | `frontend/src/components/SessionManager.tsx` |
| 29.5 | `frontend/src/__tests__/*.test.tsx` |
