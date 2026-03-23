# Architectural Decisions

**Last updated:** 2026-03-23

All decisions below are frozen. Reopening requires explicit phase gate approval.

---

## D-001: Single Execution Owner = oc runtime

**Phase:** 1.5-A | **Status:** Frozen

oc runtime is the only component that may queue, execute, retry, cancel, or report health on tasks.

---

## D-002: Terminology — orchestration vs conversation flow

**Phase:** 1.5-A | **Status:** Frozen

"Orchestration" = task execution orchestration, sole owner: oc runtime. OpenClaw = conversation flow, intent extraction, approval UX, result narration. Bridge = adapter / trust boundary, never an orchestrator.

---

## D-003: Worker model — ephemeral -RunOnce

**Phase:** 1.5-A | **Status:** Frozen

Each invocation claims pending tickets, processes them, exits. Persistent poll loop superseded.

---

## D-004: Bridge = stateless translation + auth gate

**Phase:** 1.5-A | **Status:** Frozen

No persistent state. One request = one API call = one response. Exception: terminal polling may use two sequential calls (get + output).

---

## D-005: External surface is task-centric

**Phase:** 1.5-A | **Status:** Frozen

Bridge contract uses task names and task IDs. No intent vocabulary at Bridge boundary.

---

## D-006: Raw action invocation forbidden externally

**Phase:** 1.5-A | **Status:** Frozen

oc-run-action.ps1 forbidden as external integration path. Runner is the only legitimate caller.

---

## D-007: Polling-only for Phase 1.5

**Phase:** 1.5-A | **Status:** Frozen

No callbacks, notifications, or webhooks. OpenClaw owns poll timing.

---

## D-008: Stuck task policy — fail-closed + dead-letter + no auto-retry

**Phase:** 1.5-A | **Status:** Frozen

Stuck tasks fail, write lastError, move to dead-letter. No auto-retry anywhere.

---

## D-009: Duplicate task creation accepted in Phase 1.5

**Phase:** 1.5-A | **Status:** Frozen

requestId is audit/correlation only, not dedupe.

---

## D-010: Retry not exposed externally in Phase 1.5

**Phase:** 1.5-C | **Status:** Frozen

retry_task is operator-only. User retry = new submit_task.

---

## D-011: External Bridge operations (Phase 1.5)

**Phase:** 1.5-C | **Status:** Frozen

Four operations: submit_task, get_task_status, cancel_task, get_health.

---

## D-012: Approval model — definition-level preapproval

**Phase:** 1.5-C | **Status:** Frozen

Runtime enforces approvalPolicy at task definition level. No policyContext. Bridge transports approvalStatus for audit only. Pending = rejected by Bridge.

---

## D-013: Allowlist fail-closed startup

**Phase:** 1.5-D | **Status:** Frozen

Missing/empty/unparseable allowlist = Bridge refuses to start (exit 2).

---

## D-014: Five-step validation order

**Phase:** 1.5-D | **Status:** Frozen

Structural → Operation → Allowlist → Field-level → Approval pre-validation. First failure stops.

---

## D-015: Operator exception — local/manual/admin-only

**Phase:** 1.5-A | **Status:** Frozen

Not part of Bridge external contract. Must not become shadow integration path.

---

## D-016: Health response sanitized

**Phase:** 1.5-D | **Status:** Frozen

Only health field (ok/degraded/error) plus wrapper fields. All runtime internals stripped.

---

## D-017: Minimum audit — 10 fields per request

**Phase:** 1.5-D | **Status:** Frozen

timestamp, requestId, source, sourceUserId, operation, taskName, approvalStatus, outcome, errorCode, runtimeTaskId.

---

## D-018: Bridge physical form — stateless single-invocation script

**Phase:** 1.5-E | **Status:** Frozen

bridge/oc-bridge.ps1, invoked once per request, produces response, exits.

---

## D-019: Canonical caller path — OpenClaw via WSL wrappers

**Phase:** TG-1R | **Status:** Frozen

OpenClaw Telegram → WSL wrappers → oc-bridge-call → pwsh.exe bridge/oc-bridge.ps1 → runtime.

---

## D-020: Project identity

**Phase:** Post-1.5 | **Status:** Active

Project: OpenClaw Local Agent Runtime. Repo: openclaw-local-agent-runtime.

---

## D-021: WSL Guardian replaces WSLKeepAlive

**Phase:** 1.6 | **Status:** Active

Passive `sleep infinity` keepalive replaced by active guardian (`oc-wsl-guardian.ps1`). Checks WSL + OpenClaw every 30s, auto-restarts if down, sends Telegram alerts on state changes. Scheduled task `OpenClawWslGuardian` replaces `WSLKeepAlive`.

---

## D-022: Agent architecture — registry-based, multi-agent extensible

**Phase:** 3-A | **Status:** Frozen

Agent Runner is the first entry in an Agent Registry, not a singleton. Every component designed as first-of-many: registry for agents, role-scoped policies for tools, service interfaces for approval, typed artifacts for output, table-driven routing. Single Claude agent implemented first; patterns support specialist agents without architectural rewrites.

---

## D-023: run_powershell restricted — denied to general-assistant

**Phase:** 3-A | **Status:** Frozen

`run_powershell` is NOT available to `general-assistant` agent. Reserved for future `executor` role only, requiring policy check + risk escalation + approval. Agent uses named tools (`get_system_info`, `read_file`, etc.) instead. Prevents shell escape bypassing the entire tool catalog.

---

## D-024: Tool access — role-scoped via Tool Gateway

**Phase:** 3-A | **Status:** Frozen

All tool access mediated by Tool Gateway. LLM only sees tools allowed by its role's policy. Tool Gateway checks policy, classifies risk, routes to approval if needed, executes via MCP, logs to audit. New agents get different policies through the same gateway.

---

## D-025: Approval — service interface with correlation IDs

**Phase:** 3-A | **Status:** Frozen

Approval is a decoupled service, not embedded in agent logic. Each request gets a unique approval ID. User approves by ID, not "yes/no". Supports concurrent approvals for multi-agent future. File-based storage for Phase 3-B, upgradeable later.

---

## D-026: Artifacts — typed output, handoff contracts for multi-agent

**Phase:** 3-A | **Status:** Frozen

Every agent invocation returns a standardized envelope with typed artifacts (`text_response`, `file_created`, `task_submitted`, `error`, `approval_needed`). This envelope is the handoff contract — Mission Controller will read these to decide next steps in multi-agent missions.

---

## D-027: Routing — deterministic table, not context-guessed

**Phase:** 3-A | **Status:** Frozen

Request routing uses explicit pattern-matching rules (`routing-rules.json`). First match wins, agent is the default fallback. No LLM-based intent guessing at the routing layer.

---

## D-028: Framework — direct SDK calls, GPT-4o first provider

**Phase:** 3-A/3-B | **Status:** Active

Direct SDK calls, no LangChain. GPT-4o is the first provider (OpenAI SDK). Claude added when API credits are available. Provider abstraction in `agent/providers/base.py` supports swapping without rewrites. Evaluate LangChain ONLY if adding a 3rd+ provider becomes painful.
