# Architectural Decisions

**Last updated:** 2026-04-04 (D-135)

All decisions below are frozen unless marked otherwise.
Reopening requires explicit phase gate approval + operator sign-off.

---

## Phase 1 / 1.5 Decisions (D-001 → D-020)

### D-001: Single Execution Owner = oc runtime

**Phase:** 1.5-A | **Status:** Frozen

oc runtime is the only component that may queue, execute, retry, cancel, or report health on tasks.

---

### D-002: Terminology — orchestration vs conversation flow

**Phase:** 1.5-A | **Status:** Frozen

"Orchestration" = task execution orchestration, sole owner: oc runtime. OpenClaw = conversation flow, intent extraction, approval UX, result narration. Bridge = adapter / trust boundary, never an orchestrator.

---

### D-003: Worker model — ephemeral -RunOnce

**Phase:** 1.5-A | **Status:** Frozen

Each invocation claims pending tickets, processes them, exits. Persistent poll loop superseded.

---

### D-004: Bridge = stateless translation + auth gate

**Phase:** 1.5-A | **Status:** Frozen

No persistent state. One request = one API call = one response. Exception: terminal polling may use two sequential calls (get + output).

---

### D-005: External surface is task-centric

**Phase:** 1.5-A | **Status:** Frozen

Bridge contract uses task names and task IDs. No intent vocabulary at Bridge boundary.

---

### D-006: Raw action invocation forbidden externally

**Phase:** 1.5-A | **Status:** Frozen

oc-run-action.ps1 forbidden as external integration path. Runner is the only legitimate caller.

---

### D-007: Polling-only for Phase 1.5

**Phase:** 1.5-A | **Status:** Frozen

No callbacks, notifications, or webhooks. OpenClaw owns poll timing.

---

### D-008: Stuck task policy — fail-closed + dead-letter + no auto-retry

**Phase:** 1.5-A | **Status:** Frozen

Stuck tasks fail, write lastError, move to dead-letter. No auto-retry anywhere.

---

### D-009: Duplicate task creation accepted in Phase 1.5

**Phase:** 1.5-A | **Status:** Frozen

requestId is audit/correlation only, not dedupe.

---

### D-010: Retry not exposed externally in Phase 1.5

**Phase:** 1.5-C | **Status:** Frozen

retry_task is operator-only. User retry = new submit_task.

---

### D-011: External Bridge operations (Phase 1.5)

**Phase:** 1.5-C | **Status:** Frozen

Four operations: submit_task, get_task_status, cancel_task, get_health.

---

### D-012: Approval model — definition-level preapproval

**Phase:** 1.5-C | **Status:** Frozen

Runtime enforces approvalPolicy at task definition level. No policyContext. Bridge transports approvalStatus for audit only. Pending = rejected by Bridge.

---

### D-013: Allowlist fail-closed startup

**Phase:** 1.5-D | **Status:** Frozen

Missing/empty/unparseable allowlist = Bridge refuses to start (exit 2).

---

### D-014: Five-step validation order

**Phase:** 1.5-D | **Status:** Frozen

Structural → Operation → Allowlist → Field-level → Approval pre-validation. First failure stops.

---

### D-015: Operator exception — local/manual/admin-only

**Phase:** 1.5-A | **Status:** Frozen

Not part of Bridge external contract. Must not become shadow integration path.

---

### D-016: Health response sanitized

**Phase:** 1.5-D | **Status:** Frozen

Only health field (ok/degraded/error) plus wrapper fields. All runtime internals stripped.

---

### D-017: Minimum audit — 10 fields per request

**Phase:** 1.5-D | **Status:** Frozen

timestamp, requestId, source, sourceUserId, operation, taskName, approvalStatus, outcome, errorCode, runtimeTaskId.

---

### D-018: Bridge physical form — stateless single-invocation script

**Phase:** 1.5-E | **Status:** Frozen

bridge/oc-bridge.ps1, invoked once per request, produces response, exits.

---

### D-019: Canonical caller path — OpenClaw via WSL wrappers

**Phase:** TG-1R | **Status:** Frozen

OpenClaw Telegram → WSL wrappers → oc-bridge-call → pwsh.exe bridge/oc-bridge.ps1 → runtime.

---

### D-020: Project identity

**Phase:** Post-1.5 | **Status:** Frozen

Project: OpenClaw Local Agent Runtime. Repo: openclaw-local-agent-runtime.

---

## Phase 3-A / 3-F Decisions (D-021 → D-031)

### D-021: Agent Runner — single entry point for all agent execution

**Phase:** 3-B | **Status:** Frozen

`agent/oc-agent-runner.py` is the sole agent execution entry point. Handles single-agent and mission (multi-agent) modes. No other script may invoke LLM providers directly.

---

### D-022: Agent architecture — registry-based, multi-agent extensible

**Phase:** 3-A | **Status:** Frozen

Agent system uses a registry pattern. Roles registered with capabilities, tool policies, and model assignments. Extensible to new roles without modifying core runner.

---

### D-023: run_powershell denied to general-assistant, executor-only

**Phase:** 3-A | **Status:** Frozen

`run_powershell` tool restricted to remote-operator role only. Requires approval above "high" risk tier. General-assistant and all other roles denied.

---

### D-024: Tool access — role-scoped via Tool Gateway

**Phase:** 3-A | **Status:** Frozen

Every tool call passes through Tool Gateway which enforces role-based tool policy. Roles have explicit allowed/denied tool sets. No role can bypass gateway.

---

### D-025: Approval — service interface with correlation IDs

**Phase:** 3-A | **Status:** Frozen

Approval service exposes structured interface with correlation IDs for audit. Every approval request/response carries requestId for tracing through the full execution chain.

---

### D-026: Artifacts — typed output, handoff contracts

**Phase:** 3-A | **Status:** Frozen

Every agent stage produces typed artifacts (requirements_brief, discovery_map, technical_design, etc.). Artifact types define the handoff contract between stages. Untyped output forbidden in mission mode.

---

### D-027: Routing — deterministic table, not context-guessed

**Phase:** 3-A | **Status:** Frozen

Stage-to-role routing uses deterministic lookup table, not LLM-guessed context. Complexity router selects role sequence based on tier (trivial→complex). No runtime routing decisions.

---

### D-028: Framework — direct SDK calls, no LangChain

**Phase:** 3-A | **Status:** Frozen

Agent system uses direct SDK calls (OpenAI, Anthropic, Ollama). No LangChain, CrewAI, or other agent frameworks. Reduces dependency chain and allows full control over prompt construction.

---

### D-029: Hub-and-spoke — all handoffs through Mission Controller

**Phase:** 3-F | **Status:** Frozen

Mission Controller is the central hub. All stage handoffs pass through controller. Agents never call each other directly. Controller manages state transitions, artifact routing, and failure handling.

---

### D-030: Specialists share same LLM provider, differentiated by system prompt + tool policy

**Phase:** 3-F | **Status:** Frozen

All specialist roles within a mission use the same underlying LLM provider. Differentiation via role-specific system prompt and tool policy. Model assignment is per-role (gpt-4o or claude-sonnet), not per-invocation.

---

### D-031: Sequential execution only in Phase 3-F, parallel deferred

**Phase:** 3-F | **Status:** Frozen

Mission stages execute sequentially. Parallel stage execution deferred to future phase. Simplifies state management, artifact handoff, and failure recovery.

---

## Phase 4 Design Decisions (D-032 → D-058)

### D-032: Execution ladder — 4-tier complexity routing

**Phase:** 4 (Design, 3G-K) | **Status:** Frozen

Complexity router assigns missions to one of 4 tiers: trivial (3 roles), simple (4 roles), medium (7 roles), complex (9 roles). Tier determines which roles participate and in what order. **Trade-off:** Simpler missions skip unnecessary roles, reducing cost and latency.

---

### D-033: Cost governance — per-stage budget limits

**Phase:** 4 (Design, 3G-K) | **Status:** Frozen

Each skill contract defines budget limits: maxTurns, maxFileReads, maxTokens. Exceeding budget triggers stage termination. **Trade-off:** Prevents runaway LLM costs at the expense of potentially truncating complex analysis.

---

### D-034: Discovery governance — analyst/architect only

**Phase:** 4 (Design, 3G-K) | **Status:** Frozen

Repository discovery (file listing, grep, read) restricted to analyst and architect roles. Developer, tester, and other roles forbidden from discovery. Prevents scope creep during execution phases.

---

### D-035: Cost class routing — model selection by role cost tier

**Phase:** 4 (Design, 3G-K) | **Status:** Frozen

Roles assigned cost classes (low/medium/high). PO, PM, manager use gpt-4o (low cost). Analyst, architect, developer, tester, reviewer use claude-sonnet (medium). Cost class determines model selection.

---

### D-036: Skill contracts — machine-readable role-skill binding

**Phase:** 4 (Design, 3G-L) | **Status:** Frozen

10 skill contracts define: owningRoles, forbiddenRoles, inputArtifacts, outputArtifact, allowedTools, budgets (maxTurns, maxFileReads), costClass, escalationTier. Violation of forbidden skill-role combination → mission-level policy fail.

---

### D-037: Working set concept — bounded per-stage file access

**Phase:** 4 (Design, 3G-L) | **Status:** Frozen

Each mission stage executes with bounded working set: allowed read/write files, creatable files, forbidden directories/patterns, read/write/expansion budgets. Budgets are per-stage, not shared across mission.

---

### D-038: Enforcer runs before Risk Engine

**Phase:** 4-0/1 | **Status:** Frozen

Working Set Enforcer sits between Tool Gateway and Risk Engine. Policy violations denied before approval/MCP execution. When `working_set=None` (single-agent mode), enforcer bypassed entirely.

---

### D-039: Policy telemetry event types

**Phase:** 4-1 | **Status:** Frozen

Every enforcer decision emits structured JSONL event to `logs/policy-telemetry.jsonl`. Initial event types: filesystem_tool_allowed, policy_denied, budget_exhausted, path_resolution_failed. Extended by D-055.

---

### D-040: Summary cache — zero-cost reuse

**Phase:** 4-2 | **Status:** Frozen

In-memory cache stores artifact summaries (<30% original size). `generate_basic_summary()` extracts field names, types, truncated values without LLM. Summaries enable zero-cost second delivery of same artifact to same role.

---

### D-041: Five-tier context delivery (A through E)

**Phase:** 4-2 | **Status:** Frozen

Artifact delivery tiers: A (metadata only), B (structural summary <30%), C (scoped excerpt), D (full with header), E (full + related files). Default tier per role defined in 47-entry tier matrix (artifact type × role).

---

### D-042: Reread auto-downgrade + expansion broker

**Phase:** 4-2 | **Status:** Frozen

First full read: delivered in full. Second read by same role: auto-downgraded to summary (tier B). Different roles reading same artifact: not a reread, full delivery. Expansion Broker handles working set growth with role-based budgets (developer max 8, tester max 3, analyst/architect unlimited, others 0).

---

### D-043: Artifact consumption logging

**Phase:** 4-2 | **Status:** Frozen

Every artifact access logged: artifactId, role, stageId, tier, reread flag, timestamp. Consumption stats aggregated for quality gate verification.

---

### D-044: Canonical path resolution

**Phase:** 4-0/1 | **Status:** Frozen

Every filesystem tool call path resolved via `os.path.realpath(os.path.normpath(path))`. Windows case-insensitive via `os.path.normcase()`. Produces absolute path free of `..` traversals. Foundation for all containment checks. See also D-049.

---

### D-045: Write authorization scope

**Phase:** 4-1 | **Status:** Frozen

Write operations (`mutationSurface == "code"`) must target paths in `read_write`, `creatable`, or `generated_outputs` sets. Violation → policy_denied event + LLM feedback message.

---

### D-046: Per-stage budget isolation

**Phase:** 4-1H | **Status:** Frozen

Each stage has independent budget counters. One stage exhausting its file_reads budget does not affect next stage. When exhausted, subsequent read attempts denied with `budget_exhausted` event.

---

### D-047: Artifact identity header — 12 mandatory fields

**Phase:** 4-2 | **Status:** Frozen

Every artifact carries identity header: artifactId (unique), artifactType, version (monotonic), missionId, producedByStage, producedByRole, producedBySkill, producedAt (ISO), inputArtifactIds (lineage), contentHash (SHA-256), sizeTokens, compressionAvailable. Enables tracking, deduplication, lineage verification.

---

### D-048: Canonical role names + alias resolution

**Phase:** 4-2C | **Status:** Frozen

Working set templates use canonical role names (product-owner, analyst, architect, project-manager, developer, tester, reviewer, manager, remote-operator). Alias table: `{"executor": "remote-operator"}`. Unknown roles get restrictive fallback: 5 file reads, 2 dir reads, 0 expansions.

---

### D-049: Path resolution — absolute, case-normalized, traversal-safe

**Phase:** 4-0/1 | **Status:** Frozen

Extends D-044. `os.path.realpath(os.path.normpath(path))` with `os.path.normcase()`. Containment check against project root. Used by Working Set Enforcer for every filesystem tool call.

---

### D-050: Mission mode fail-closed gate

**Phase:** 4-1H | **Status:** Frozen

Pre-dispatch check in `execute_mission()`: if stage's `working_set` is None in mission mode, stage immediately fails with `POLICY:` message and mission aborts. Single-agent mode (working_set=None) continues to work — enforcer bypass only outside mission context. See also D-053.

---

### D-051: Mutation surface mismatch detection

**Phase:** 4-2C | **Status:** Frozen

When tool's `mutationSurface` doesn't match working set expectations, `mutation_surface_mismatch` telemetry event emitted. Soft denial with warning — operation may proceed but is flagged.

---

### D-052: Per-mission structured summary

**Phase:** 4-2C | **Status:** Frozen

`_emit_mission_summary()` produces `logs/missions/{mission_id}-summary.json` with: stateTransitions, finalState, attemptCounters, feedbackLoopStats, gatesChecked. Also emits `mission_completed` or `mission_failed` telemetry event.

---

### D-053: Mission mode fail-closed — working set required

**Phase:** 4-1H | **Status:** Frozen

If a stage's `working_set` is None in mission mode, stage immediately fails with `POLICY:` message. Default working sets auto-generated per specialist role during planning via `_build_default_working_set()`. Code: `controller.py` line 126.

---

### D-054: Feedback loops — quality improvement cycles

**Phase:** 4-5 | **Status:** Frozen

Two feedback loops: (1) test-developer loop — tester failure feeds back to developer for fix, (2) reviewer-developer loop — reviewer rejection feeds back to developer. Max 2 iterations per loop before escalation.

---

### D-055: Policy telemetry — 6 enforcer event types

**Phase:** 4-1H/2C | **Status:** Frozen

Six enforcer telemetry event types to `logs/policy-telemetry.jsonl`: filesystem_tool_allowed, policy_denied, budget_exhausted, path_resolution_failed, mutation_surface_mismatch (Sprint 2C), policy_soft_denied (Sprint 2C). 12+ total event types across all layers.

---

### D-056: Recovery triage — manager recovery before abort

**Phase:** 4-5C | **Status:** Frozen

On stage failure, `_handle_stage_failure()` checks retry budget (max 3 per stage). If available, creates manager `recovery_triage` stage. Manager returns action: `retry_stage`, `abort`, `escalate_to_operator`, or `retry_from` (rewind). 4th failure on same stage always aborts. Recovery failure caught by outer try/except.

---

### D-057: Startup metadata validation gate

**Phase:** 4-1H | **Status:** Frozen

`validate_catalog_governance()` runs on every startup before any LLM/MCP call. Validates all 24 tools have complete governance metadata. Missing metadata → `FATAL:` error + `exit 1`. Also validates skill contracts and role registry. Code: `oc-agent-runner.py` line 30.

---

### D-058: Path hardening — null byte + UNC rejection

**Phase:** 4-1H | **Status:** Frozen

Extension to D-049. Rejects: null byte injection (`\x00` → None), UNC paths (`\\server\share` → None). Blocks 9 Windows attack vectors (traversal, junction escape, symlink, null byte, UNC). Test corpus: 9 cases, all pass. Code: `path_resolver.py` lines 14-19.

---

## Phase 5 Decisions (D-059 → D-076)

### D-059: Read-only first, Controller sole executor

**Phase:** 5 (design) | **Status:** Frozen

Phase 5A–5B read-only. Mission Controller remains the sole executor — UI observes, never mutates mission state directly. Mutation (intervention, approval) gated behind feature flags in Phase 5C.

---

### D-060: Polling → SSE, No WebSocket

**Phase:** 5B (Sprint 10) | **Status:** Frozen

Frontend starts with 2s polling (Sprint 9), upgrades to SSE (Sprint 10). WebSocket explicitly rejected — SSE is simpler, sufficient for one-directional server→client push, and natively supports Last-Event-ID replay.

---

### D-061: FastAPI from day 1

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

FastAPI + Uvicorn for all phases. No Flask, no custom HTTP. Decision is irreversible — all API work builds on this stack.

**Trade-off:** Heavier initial setup vs. consistent foundation. async-native from start.

---

### D-062: Intervention via atomic file signal

**Phase:** 5C (Sprint 11) | **Status:** Frozen

UI writes intervention request as atomic JSON file. Controller polls for intervention signals between stages. No direct process communication.

**Trade-off:** Higher latency (poll interval) vs. crash-safe, no IPC complexity.

---

### D-063: Approval via service layer

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Current strict-ID approval service sunsets in Phase 5C. New approval flow: UI → API → ApprovalService → atomic file → Controller reads. Structured request/response contract.

**Trade-off:** Migration effort vs. clean contract for future multi-approver support.

---

### D-064: Port assignment — API 8003, React 3000

**Phase:** 5A (Sprint 8) | **Status:** Frozen

Mission Control API on port 8003, React dev server on 3000. Env override supported. No conflict with existing WMCP (8001) and legacy dashboard (8002).

---

### D-065: Normalized API — MissionNormalizer

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

API does not expose raw files. MissionNormalizer reads multiple sources (state.json, mission JSON, telemetry JSONL, summary), applies precedence rules, caches result, returns normalized response.

**Precedence:** state > mission (for status), summary > telemetry (for forensics).

---

### D-066: Legacy dashboard lives until 5D

**Phase:** 5D (Sprint 12) | **Status:** Frozen

Legacy health dashboard on port 8002 runs in parallel until Sprint 12 evaluation. No premature removal.

---

### D-067: Schema frozen after 5A-1, additive-only

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

API response schemas freeze at Sprint 8 exit. Post-freeze: additive fields only, no removal, no type change. Versioned as `/api/v1/`.

---

### D-068: Unknown ≠ zero, data quality states

**Phase:** 5A–5B (Sprint 8–9) | **Status:** Frozen (amended by D-079)

Every data point has a quality state. UI must distinguish all states. Rendering unknown as zero, empty, pass, or green is forbidden.

**Original (5 states):** `known_zero`, `unknown`, `not_reached`, `stale`, `degraded`.
**Amended (D-079, 6 states):** `fresh`, `partial`, `stale`, `degraded`, `unknown`, `not_reached`.

**Impacted:** All API responses, all UI components, all normalizer logic.

---

### D-069: No control without acknowledgement

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Every mutation request follows lifecycle: `requested → accepted → applied | rejected | timed_out`. No fire-and-forget commands.

---

### D-070: DNS rebinding protection

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

FastAPI validates Host header. Explicit CORS config. Server binds to 127.0.0.1 only. Rejects requests with unexpected Host or Origin headers.

---

### D-071: Atomic file writes system-wide

**Phase:** 4.5-C → 5 (Sprint 7+) | **Status:** Frozen

All JSON file writes use atomic pattern: write to temp file → fsync → os.replace(). No partial writes. Applied to capabilities.json, state files, intervention signals, all API-written files.

---

### D-072: Per-source circuit breaker + per-panel error boundary

**Phase:** 5A (Sprint 8–9) | **Status:** Frozen

Backend: per-source circuit breaker (state file, mission file, telemetry). If one source fails, others still serve. Frontend: per-panel React error boundary — one panel crash doesn't take down the page.

---

### D-073: Log rotation — 10MB / 5 files / 14 days

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

API logs: 10MB max per file, keep 5 rotated files, 14-day retention. Consistent with existing runtime log rotation policy.

---

### D-074: Startup sequence + ownership matrix

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

Explicit startup order: config load → file system validation → cache warm → normalizer init → API serve. Each subsystem has a single owner — no shared writes to the same file.

---

### D-075: All state on ext4, cross-OS via API

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

All persistent state files live on ext4 (WSL2 filesystem). Windows access exclusively through API (port 8003). No direct NTFS↔ext4 file sharing for state. File owner/target FS matrix tracked and reviewed at Sprint 8 kickoff.

---

### D-076: SSE event ID = `{source}:{offset}`

**Phase:** 5B (Sprint 10) | **Status:** Frozen

Event ID format: `{source_file}:{byte_offset}` (JSONL) or `{source_file}:{mtime_ms}` (JSON). Restart-safe via Last-Event-ID. Monotonic. Dedupe by same source:offset → skip.

Example: `policy-telemetry.jsonl:48231`, `mission-abc123.json:1711288380`

---

## Phase 4.5-C / Sprint 7-8 Decisions (D-077 → D-080)

### D-077: Sprint-End Documentation Policy

**Phase:** 4.5-C (Sprint 7) | **Status:** Frozen

Mandatory documentation update at every sprint closure. Originally enforced by validate_sprint_docs.py (removed in cleanup; superseded by `tools/validate-plan-sync.py` and `closure-preflight.yml` in S19+). Validation must pass before sprint is marked "done". Required docs: STATE.md, NEXT.md, DECISIONS.md, BACKLOG.md, handoffs/current.md, capabilities.json, sprint plan doc. Checks: freshness, required sections, capability autoGenerated flag, open checkboxes, test count regression. **Trade-off:** Sprint closure takes ~15 min longer vs. document consistency and session handoff quality guaranteed.

---

### D-078: Sprint 7 E2E Partial Pass Waiver

**Phase:** 4.5-C → 5A-1 | **Status:** Frozen

Sprint 7 E2E 2/4 pass accepted. T-OT-3: LLM quality (out of Sprint 7 scope). T-OT-4: `_save_mission()` non-atomic write crash (pre-existing bug, planned as Sprint 8 blocking fix). Sprint 7 code changes (denyForensics, agentUsed, gateResults) validated in successful missions. Both failures outside Sprint 7 scope. **Trade-off:** Proceeding to Sprint 8 with 50% E2E. Risk accepted because fail root causes are not in Sprint 7 code.

---

### D-079: DataQuality Enum Amendment (D-068 update)

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

D-068 principle preserved but state list updated. `known_zero` removed (was a value state, not a quality state), `fresh` and `partial` added. 6 states: `fresh`, `partial`, `stale`, `degraded`, `unknown`, `not_reached`. Precedence: `degraded > stale > partial > fresh`. **Trade-off:** Frozen decision state count changed. Principle and safety guarantee unchanged, representation capacity increased.

---

### D-080: Service Registry Freshness Rule

**Phase:** 5A-1 (Sprint 8) | **Status:** Frozen

Service registration protected by heartbeat-based freshness. Each service writes `lastHeartbeatAt` + `heartbeatIntervalS`. Liveness: `lastHeartbeatAt + (heartbeatIntervalS × 2) > now`. Threshold exceeded → stale → health `degraded`. Prevents stale "running" entries after crash. **Impacted:** `agent/api/server.py`, `agent/api/health_api.py`

---

## Phase 5A-2 Decisions (Sprint 9 — Read-Only UI)

### D-081: CSS Framework — Tailwind CSS Utility-First

**Phase:** 5A-2 (Sprint 9) | **Status:** Frozen

Tailwind CSS utility-first approach. No component library; all UI built with Tailwind utility classes. **Trade-off:** More verbose JSX, but zero runtime CSS bloat and design token consistency guaranteed.

---

### D-082: Type Generation — Manual TS Types from Frozen Pydantic Schemas

**Phase:** 5A-2 (Sprint 9) | **Status:** Frozen

Frontend TypeScript types written manually from frozen Pydantic schemas (D-067). No auto code-gen tools (openapi-typescript, etc.). **Trade-off:** Both sides must update on schema change, but dependency chain stays simple.

---

### D-083: Polling — Global 30s + Manual Refresh, Page Visibility Pause

**Phase:** 5A-2 (Sprint 9) | **Status:** Frozen

Initial data fetch strategy: 30s global polling interval + manual refresh button. Polling pauses when tab is in background (Page Visibility API). Augmented by SSE in Sprint 10, polling remains as fallback. **Trade-off:** 30s stale window accepted; real-time SSE comes in next sprint.

---

### D-084: Error Boundary — Per-Panel Isolation, Per-Route Wrap

**Phase:** 5A-2 (Sprint 9) | **Status:** Frozen

Each dashboard panel has its own ErrorBoundary. One panel crash does not affect others. Route-level ErrorBoundary also present. **Trade-off:** More boilerplate, but partial degradation possible — single panel failure does not take down entire UI.

---

## Phase 5B Decisions (Sprint 10 — SSE Live Updates)

### D-085: File Watcher — Manual mtime Polling 1s, Pure Python os.stat

**Phase:** 5B (Sprint 10) | **Status:** Frozen

File change detection via 1s interval `os.stat()` mtime polling instead of watchdog/inotify. Pure Python, cross-platform. **Trade-off:** 1s latency and CPU overhead (stat call per file), but zero dependency and Windows/WSL2 compatible.

---

### D-086: SSE Events — Per-Entity Invalidation Signal, Not Per-Field

**Phase:** 5B (Sprint 10) | **Status:** Frozen

SSE events send entity-level invalidation signals (e.g., `mission_updated`), not field-level diffs. Client re-fetches the relevant entity on SSE event. **Trade-off:** More HTTP requests, but SSE payload stays simple and no partial state risk.

**Sprint 11 Extension — Mutation SSE Event Types:**

| Event Type | Trigger | Data |
|-----------|---------|------|
| `mutation_requested` | API signal artifact persisted | `{ requestId, targetId, type }` |
| `mutation_accepted` | Controller consumed signal, validation passed | `{ requestId, targetId, type }` |
| `mutation_applied` | Controller completed state transition | `{ requestId, targetId, type, newState }` |
| `mutation_rejected` | Controller validation failed | `{ requestId, targetId, reason }` |
| `mutation_timed_out` | Controller did not process within 10s | `{ requestId, targetId }` |

---

### D-087: SSE Auth — Localhost-Only, D-070 Extension, No Extra Token

**Phase:** 5B (Sprint 10) | **Status:** Frozen

SSE endpoint protected by D-070 (localhost-only binding + Host header validation). No additional SSE token or authentication mechanism. **Trade-off:** Insufficient for multi-user scenario, but adequate for single-operator localhost.

---

### D-088: SSE Reconnect — Backoff + Polling Fallback

**Phase:** 5B (Sprint 10) | **Status:** Frozen

On SSE disconnect: 1s→2s→4s→8s→16s→30s exponential backoff reconnect. 3 consecutive failures → switch to polling fallback mode. Last-Event-ID persistence catches missed events. 60s heartbeat timeout → connection considered dead. **Trade-off:** Complex reconnect logic, but UI never goes dark on SSE loss.

---

## Phase 5C Decisions (Sprint 11 — Intervention / Mutation)

### D-089: CSRF — Origin Header Check (SameSite browser-dependent)

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Origin header check enforced on all POST endpoints; SameSite depends on browser cookie context (not server-enforced). Mutation endpoints reject requests with missing or invalid Origin → 403. Double-submit cookie unnecessary for localhost single-operator. **Trade-off:** Older browsers may not send Origin on same-origin POST. Accepted: system is localhost-only (D-070).

---

### D-090: Mutation Confirm — Confirmation Dialog for Destructive Actions

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Destructive actions (cancel, reject) require confirmation dialog. Non-destructive (approve, retry) are single click. No undo mechanism — mutations are irreversible. **Trade-off:** Increased UX friction, but eliminates accidental destructive action risk.

---

### D-091: Mutation UI — Server-Confirmed, No Optimistic UI

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Mutation request → wait for server response → SSE event confirms state change → UI refresh. No optimistic state update. 100-500ms latency accepted — operator dashboard, not real-time trading. **Trade-off:** Slower UX, but zero risk of displaying incorrect state.

---

### D-092: Approval Sunset Phase 1

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Dashboard `approve <id>` / `reject <id>` becomes primary channel. Telegram yes/no still works but logs deprecation warning. Full removal deferred to Phase 6 (D-099 scope boundary). **Trade-off:** Two active channels during transition, but backward compatibility preserved.

---

### D-093: Reserved — reassigned to D-097

**Phase:** 5D (Sprint 12) | **Status:** Deprecated (reassigned)

Originally planned as OD-11 (legacy dashboard decision). Reassigned to D-097 during Sprint 12 kickoff to maintain contiguous numbering with D-098→D-101. See D-097 for the frozen decision.

---

### D-094: Reserved — reassigned to D-098

**Phase:** 5D (Sprint 12) | **Status:** Deprecated (reassigned)

Originally planned as OD-12 (E2E framework decision). Reassigned to D-098 during Sprint 12 kickoff. See D-098 for the frozen decision.

---

### D-095: Reserved — reassigned to D-099

**Phase:** 5D (Sprint 12) | **Status:** Deprecated (reassigned)

Originally planned as OD-14 (approval sunset Phase 2). Reassigned to D-099 during Sprint 12 kickoff. See D-099 for the frozen decision.

---

### D-096: Mutation Response Contract — Full Lifecycle

**Phase:** 5C (Sprint 11) | **Status:** Frozen

Every mutation endpoint returns D-096 lifecycle: `{ requestId, lifecycleState, targetId, requestedAt, acceptedAt, appliedAt, rejectedReason, timeoutAt }`. Lifecycle: `requested → accepted → applied | rejected | timed_out`. API response always returns `lifecycleState=requested`. Subsequent states arrive via SSE only. Client correlates SSE events by requestId. Fire-and-forget forbidden.

---

## Phase 5D Decisions (Sprint 12 — Polish + Phase 5 Closure)

### D-097: Legacy dashboard retired — removal deferred

**Phase:** 5D (Sprint 12) | **Status:** Frozen

Mission Control (:8003 + :3000) fully replaces legacy health dashboard (:8002). Deprecation banner added to UI, startup log warning emitted. Code removal deferred to Sprint 13. **Trade-off:** Keeping code in Sprint 12 avoids regression risk during Phase 5 closure. Removal in Sprint 13 (stabilization sprint) is lower risk. **Validation:** Deprecation banner visible at localhost:8002, startup log contains warning, OPERATOR-GUIDE.md documents deprecation.

---

### D-098: API-level E2E with httpx + pytest — browser E2E deferred

**Phase:** 5D (Sprint 12) | **Status:** Frozen

E2E tests use `httpx` + `pytest` for API-level testing. Browser-level E2E (Playwright/Cypress) deferred to Phase 6. API-level E2E covers critical paths (roles, signals, approvals, SSE) without browser driver overhead. **Trade-off:** UI interaction coverage deferred but not eliminated. **Validation:** `pytest tests/e2e/ -v` → 12+ PASS, 0 FAIL. Tests isolated from unit test suite.

---

### D-099: Approval model changes are Phase 6 scope

**Phase:** 5D (Sprint 12) | **Status:** Frozen

Current preapproval model (D-012) remains unchanged. Approval evolution (dynamic approval, per-request approval, delegation) is Phase 6 work. **Trade-off:** Defers flexibility for stability. Phase 5 closes with a proven, tested approval model.

---

### D-100: OpenAPI spec auto-generated from FastAPI

**Phase:** 5D (Sprint 12) | **Status:** Frozen

OpenAPI spec generated from FastAPI built-in schema, exported to `docs/api/openapi.json`. No hand-written spec. Custom documentation added via FastAPI decorators. **Trade-off:** Auto-generated spec always in sync with code. **Validation:** `curl localhost:8003/openapi.json | python -m json.tool` → valid JSON. Endpoint count matches actual routes.

---

### D-101: SSE is Mission Control frontend transport only — amends D-068

**Phase:** 5D (Sprint 12) | **Status:** Frozen | **Amends:** D-068

SSE is a Mission Control frontend transport concern only. Does not amend or expand Bridge contract responsibilities. Bridge contract remains four operations (D-011). SSE streams served by Mission Control API (:8003) to React frontend (:3000). **Trade-off:** Clear ownership boundary. SSE complexity stays inside Mission Control. Bridge remains stateless single-invocation (D-018). **Validation:** `grep -r "SSE\|EventSource" bridge/` → 0 matches.

---

### D-102: Token budget enforcement — 5-layer defense

**Phase:** Post-5D | **Status:** Frozen

Token budget enforcement to prevent context overflow in multi-stage missions. 5-layer architecture:
- **Layer 3 (Observability):** `TokenTracker` logs per-tool-call and per-stage token consumption. `estimate_tokens()` at ~4 chars/token. Per-mission report saved to `{mission_id}-token-report.json`.
- **Layer 4 (Budget Enforcement):** `truncate_tool_response()` auto-truncates tool responses >10K tokens, blocks >50K. Controller truncates artifact context >40K chars.
- **Layer 5 (Role-Based Tool Access):** `take_screenshot` removed from analyst/architect/tester allowedTools — developer-only. Runtime enforcement at dispatch: tool calls not in `allowedTools` are blocked with `policyDenied` flag.
- **Token Report API:** `GET /api/v1/missions/{id}/token-report` returns aggregated report. UI panel in MissionDetailPage shows per-stage breakdown with progress bars.
- **Budget Config:** tool_response_limit=10K, tool_response_hard_limit=50K, stage_input_limit=50K, stage_input_hard_limit=150K, mission_total_limit=500K.

**Key files:** `agent/context/token_budget.py`, `agent/mission/role_registry.py`, `agent/oc_agent_runner_lib.py` (dispatch enforcement), `agent/mission/controller.py` (`_save_token_report`).
**Trade-off:** Conservative limits (10K truncate, 50K block) may require tuning per use case. Runtime enforcement adds ~1ms per tool call overhead — acceptable vs. context overflow risk. **Validation:** Backend 233 tests pass. Frontend TypeScript 0 errors, 29 tests pass.

### D-103: Complexity-based rework limits

**Phase:** Sprint 13 | **Status:** Frozen

Rework cycle limits scale with mission complexity to prevent runaway rework on simple missions.

| Complexity | Dev-Test max | Dev-Review max |
|------------|-------------|----------------|
| trivial    | 1           | 1              |
| simple     | 2           | 1              |
| medium     | 3           | 2              |
| complex    | 4           | 3              |

**Rationale:** Simple missions were seeing 6+ rework cycles (observed in Sprint 12 test scenarios). Complexity-based limits escalate to recovery earlier for simpler tasks, reducing wasted token budget and mission duration.

**Key files:** `agent/mission/feedback_loops.py` (REWORK_LIMITS dict, `__post_init__`), `agent/mission/controller.py` (`_mission_complexity`, `_check_gates_and_loops`).
**Validation:** 12 unit tests in `agent/tests/test_rework_limiter.py`. All existing feedback loop tests (12) pass unchanged.

---

## Sprint 14A / Phase 5.5 Decisions (D-104 → D-108)

### D-104: Backend Package Name = `app/`

**Phase:** Sprint 14A | **Status:** Frozen

Backend restructure uses `app/` as the top-level package name with `create_app()` factory pattern. Enables proper Python packaging and test isolation.
Formal record: Sprint 14A task breakdown + retrospective.

---

### D-105: Sprint Closure Model — Model A / Model B

**Phase:** Sprint 16 | **Status:** Frozen

Two closure models. Model A = full (all evidence + gates sprint-time). Model B = lightweight (retroactive evidence + waiver docs acceptable). Operator selects at kickoff. Model B max 2 consecutive sprints. Retrospective never waivable.
Formal record: `docs/decisions/D-105-CLOSURE-MODEL.md`.

---

### D-106: Persistence Model — JSON File Store

**Phase:** Sprint 16 | **Status:** Frozen (post-hoc)

JSON file store for mission history, OTel traces, metric snapshots. `mission_store.py`, `trace_store.py`, `metric_store.py`. Atomic writes. No ORM, no migrations.
Formal record: `docs/decisions/D-106-PERSISTENCE-MODEL.md`.

---

### D-107: Alert Engine — Rule-Based Threshold Evaluation

**Phase:** Sprint 16 | **Status:** Frozen (post-hoc)

Rule-based threshold evaluation. 9 default rules + CRUD API. Telegram notifier. Known limitation: `"any"` rules lack namespace scoping (P-16.2 carry-forward).
Formal record: `docs/decisions/D-107-ALERT-ENGINE.md`.

---

### D-108: Session/Auth Model — Single-Operator Foundation

**Phase:** Sprint 16 | **Status:** Frozen (post-hoc)

Single-operator identity model (`agent/auth/session.py`). No password auth, no token issuance. Multi-user deferred to Phase 6 under D-104.
Formal record: `docs/decisions/D-108-SESSION-AUTH-MODEL.md`.

---

### D-109: Benchmark Strategy — Evidence-Only Model

**Phase:** Sprint 17 | **Status:** Frozen

Benchmark pipeline produces `benchmark.txt` as CI artifact. No automated regression gate. JSON baseline + comparator deferred to future sprint.
Formal record: `docs/decisions/D-109-BENCHMARK-STRATEGY.md`.

---

### D-110: Documentation Model Hierarchy — Dual Source

**Phase:** Sprint 17 | **Status:** Frozen

Dual model: STATE.md/NEXT.md canonical for system state and roadmap. handoffs/current.md supplementary for session context. Sprint tooling optional.
Formal record: `docs/decisions/D-110-DOC-MODEL.md`.

---

### D-111: CLAUDE.md Rewrite — Compact Operating Brief

**Phase:** Sprint 18 | **Status:** Frozen

CLAUDE.md stays as filename (Claude Code convention). Rewritten to ~80-100 lines. Stale sections (Current State, Phase 5 Progress, Architecture Quick Reference) removed. Sections: Project, Key Files, Documentation, Build & Test, Hard Rules, Do Not.
Formal record: `docs/decisions/D-111-claude-md-rewrite.md`.

---

### D-112: Governance Consolidation — PROCESS-GATES + PROTOCOL → GOVERNANCE.md

**Phase:** Sprint 18 | **Status:** Frozen

PROCESS-GATES.md (368 lines) + PROTOCOL.md (93 lines) merged into `docs/ai/GOVERNANCE.md` (~150-200 lines). Keep: source hierarchy, sprint status model, gate model, done/evidence/closure/archive rules, test hygiene, retrospective gate, proposal format, cross-review protocol. Drop: patch history (P-01→P-10), migration model, sprint-specific rules.
Formal record: `docs/decisions/D-112-governance-consolidation.md`.

---

### D-113: Archive Boundary — Active vs Historical Separation

**Phase:** Sprint 18 | **Status:** Frozen

Archive boundary: `docs/archive/` sub-structured by type (sprints, phase-reports, process-history, debt-plans, review-packets). Active sprints in `docs/sprints/` = last closed + current only. Old phase reports archived except PHASE-5.5-CLOSURE-REPORT.md and Sprint 15/16 reports.
Formal record: `docs/decisions/D-113-archive-boundary.md`.

---

### D-114: Handoff Model — Keep current.md Path

**Phase:** Sprint 18 | **Status:** Frozen

Keep `docs/ai/handoffs/current.md` path (sprint-plan.py depends on it). Archive stale snapshots. Handoff is supplementary to STATE.md/NEXT.md (per D-110).
Formal record: `docs/decisions/D-114-handoff-model.md`.

---

## Phase 5 Freeze Addendum (Sprint 7→8 transition)

### Blocking Fix Closures

Written closure of 4 blocking fixes in PHASE-5-FREEZE-ADDENDUM.md (archived/removed in S18 cleanup).
Sprint 8 did not start until this document was FROZEN.

| BF | Topic | Reference |
|----|------|----------|
| BF-1 | Response freshness semantics | Freeze Addendum Section 1 |
| BF-2 | Startup ownership matrix | Freeze Addendum Section 2 |
| BF-3 | Migration boundary inventory (D-075) | Freeze Addendum Section 3 |
| BF-4 | Source precedence table (D-065) | Freeze Addendum Section 4 |

---

*Architectural Decisions — OpenClaw Local Agent Runtime*
*D-001 → D-020: Phase 1/1.5 (frozen)*
*D-021 → D-031: Phase 3-A/3-F (frozen)*
*D-032 → D-058: Phase 4 Design + Sprints 0–6D (frozen)*
*D-059 → D-076: Phase 5 (frozen)*
*D-077, D-078, D-079, D-080: Phase 4.5-C / 5A-1 (frozen)*
*D-081 → D-084: Phase 5A-2 / Sprint 9 (frozen)*
*D-085 → D-088: Phase 5B / Sprint 10 (frozen)*
*D-089 → D-092, D-096: Phase 5C / Sprint 11 (frozen)*
*D-097 → D-101: Phase 5D / Sprint 12 (frozen)*
*D-102: Token budget enforcement — Post-5D (frozen)*
*D-103: Complexity-based rework limits — Sprint 13 (frozen)*
*D-104: Backend package name = app/ — Sprint 14A (frozen)*
*D-105: Sprint closure model (Model A / Model B) — Sprint 16 (frozen)*
*D-106: Persistence model — JSON file store — Sprint 16 (frozen)*
*D-107: Alert engine — Rule-based threshold evaluation — Sprint 16 (frozen)*
*D-108: Session/auth model — Single-operator foundation — Sprint 16 (frozen)*
*BF-1 → BF-4: Phase 5 Freeze Addendum (frozen)*

## Phase 6 / Sprint 26-29 Decisions (D-115 → D-118)

### D-115: Backend Physical Topology

**Phase:** Sprint 26 | **Status:** Frozen

No restructure needed — current modular architecture is clean and acyclic (138 files, 12 modules, 0 circular deps). Import rules codified. S14A/14B carryover RETIRED.
Formal record: `docs/decisions/D-115-backend-restructure.md`.

---

### D-116: Docker Dev Runtime Topology

**Phase:** Sprint 26 | **Status:** Frozen

Docker Compose dev environment with hot-reload, volume mounts, health checks.
Formal record: `docs/decisions/D-116-docker-dev.md`.

---

### D-117: Multi-User Auth Contract

**Phase:** Sprint 27 | **Status:** Frozen

API key auth, operator/viewer roles, fail-closed, file-based key registry. Supersedes D-108.
Formal record: `docs/decisions/D-117-auth-contract.md`.

---

### D-118: Plugin Runtime Contract

**Phase:** Sprint 29 | **Status:** Frozen

File-based plugins, JSON manifest, EventBus integration, config-driven loading, 30s timeout, error isolation, priority 500+.
Formal record: `docs/decisions/D-118-plugin-contract.md`.

---

## Phase 7 / Sprint 30-33 Decisions (D-119 → D-125)

### D-119: Mission Template Lifecycle

**Phase:** Sprint 30 | **Status:** Frozen

JSON schema, CRUD API, parameter validation, run-from-template, draft/published/archived states.
Formal record: `docs/decisions/D-119-mission-templates.md`.

---

### D-120: Scheduled/Triggered Missions

**Phase:** Sprint 30 | **Status:** Frozen

Cron scheduling, event triggers, execution queue. Decision frozen, implementation deferred to S31+.
Formal record: `docs/decisions/D-120-scheduled-missions.md`.

---

### D-121: Approval Gate Contract

**Phase:** Sprint 30 | **Status:** Frozen

Centralized inbox, lifecycle (pending/approved/rejected/expired), actor-chain audit, 30min default timeout.
Formal record: `docs/decisions/D-121-approval-gate.md`.

---

### D-122: Backlog-to-Project-to-Sprint Contract

**Phase:** Sprint 31 | **Status:** Frozen

GitHub Issues canonical, BACKLOG.md generated, separate backlog/sprint issues, milestone as sprint container.
Formal record: `docs/decisions/D-122-backlog-project-sprint.md`.

---

### D-123: Project V2 Item Contract v1

**Phase:** Sprint 33 | **Status:** Frozen

Canonical truth definition (5 truths: Status, Sprint, Priority, Task ID, Issue State), write authority rule, non-canonical fields kept.
Formal record: `docs/decisions/D-123-project-item-contract.md`.

---

### D-124: Legacy Normalization Boundary

**Phase:** Sprint 33 | **Status:** Frozen

5-class taxonomy (backlog, sprint-task, legacy-sprint, normalized-legacy, unclassified), minimum normalization for pre-S31 items, unclassified=FAIL.
Formal record: `docs/decisions/D-124-legacy-normalization.md`.

---

### D-125: Closure State Sync

**Phase:** Sprint 33 | **Status:** Frozen

Triple consistency rule (issue state + project status + sprint identity), backlog closure evidence rule, forbidden states.
Formal record: `docs/decisions/D-125-closure-state-sync.md`.

---

## Sprint 34 Decisions (D-127)

*D-126: Reserved, not used — number gap between Sprint 33 (D-125) and Sprint 34 (D-127). No decision was proposed for this ID.*

### D-127: Sprint Closure Class Taxonomy

**Phase:** Sprint 34 | **Status:** Frozen

Product vs governance sprint classes, class-aware evidence manifests, sprint-class.txt metadata, NO EVIDENCE rules, auto-detect class resolution.
Formal record: `docs/decisions/D-127-closure-class-taxonomy.md`.

---

## Sprint 35 Decisions (D-128)

### D-128: Risk Classification Contract

**Phase:** Sprint 35 | **Status:** Frozen

4-level risk taxonomy (low/medium/high/critical), static tool mapping, unknown=high fail-safe, computed once at creation, persisted in mission state, internal-only (no API exposure in S35).
Formal record: `docs/decisions/D-128-risk-classification.md`.

---

## Sprint 36 Decisions (D-129)

### D-129: Secret Storage + Audit Integrity Contract

**Phase:** Sprint 36 | **Status:** Frozen

AES-256-GCM encryption, base64 32-byte key from env, read-only on missing/invalid key, atomic write, SHA-256 hash chain audit with CLI verify.
Formal record: `docs/decisions/D-129-secret-audit-contract.md`.

---

## Sprint 37 Decisions (D-130)

### D-130: Transport Encryption Contract

**Phase:** Sprint 37 | **Status:** Frozen

TLS 1.2+, fail-closed default (no cert = startup deny), dev-mode explicit HTTP fallback, HSTS, self-signed cert generator.
Formal record: `docs/decisions/D-130-transport-encryption.md`.

---

### D-131: Test Count Reporting Contract

**Phase:** Sprint 48 | **Status:** Frozen

Canonical test total = backend + frontend + Playwright (3 components). Format: `XXX backend + YYY frontend + ZZZ Playwright = NNN total`. All canonical docs (handoff, STATE.md, NEXT.md, CLAUDE.md) use this format. Sprint closure evidence includes 3 separate output lines.
Formal record: `docs/decisions/D-131-test-reporting.md`.

---

### D-133: Policy Engine Contract

**Phase:** Sprint 48 | **Status:** Frozen

Rule-based, config-driven, fail-closed policy engine. Pre-stage evaluation with policyContext (B-013), timeoutConfig (B-014), missionConfig, toolRequest inputs. Output: allow/deny/escalate/degrade. YAML rule format in `config/policies/`. S49 = implementation.
Formal record: `docs/decisions/D-133-policy-engine.md`.

---

### D-134: Source User Identity Resolution Contract

**Phase:** Sprint 55 | **Status:** Frozen

Mission creation `sourceUserId` resolved via 3-tier precedence: (1) authenticated session/token identity, (2) `X-Source-User` request header, (3) `config.default_user` fallback. Fail-closed: if no source resolves, request rejected (HTTP 401). Header-based resolution only accepted from trusted origins (localhost / internal). Auth context always takes precedence over header. This is an additive extension of D-117 (multi-user auth contract).

---

### D-135: Secret Rotation + Allowlist + Metrics Contract

**Phase:** Sprint 57 | **Status:** Frozen

**Secret Rotation (B-007):** SecretRotationService extends D-129 SecretStore. Age-based rotation policy (default 90 days, configurable). Key versioning via SHA-256 hash tracking (truncated to 16 hex chars, never raw key storage). Rotation lifecycle: initialize → status check → rotate (re-encrypt all secrets with new key). Fail-safe: rollback to old key on re-encryption failure. Rotation metadata persisted atomically (D-071) in `config/secret-rotation-meta.json`. Status states: ok/warning/expired/unknown. No auto-rotation without operator trigger (auto_rotate flag exists but requires explicit enablement).

**Multi-source Allowlist (B-009):** AllowlistStore provides YAML-backed source filtering in `config/allowlists/`. Source types: caller_source, caller_id, caller_role. Matching: exact, wildcard (`*`), prefix (`admin.*`). Fail-open when no allowlist exists for a source type (no restrictions = allowed). Fail-closed when allowlist exists and value not matched (denied). Disabled entries are transparently skipped. Write authority: AllowlistStore single owner, YAML atomic writes (D-071). Thread-safe CRUD with write lock.

**Prometheus Metrics (B-117):** Read-only metrics exposure at `/api/v1/metrics` (Prometheus text format) and `/api/v1/metrics/json`. No authentication required (localhost-only per D-070). Metrics derived from MissionStore and MetricStore — no new data collection. 3 Grafana dashboard templates in `config/grafana/` validated by `tools/grafana_setup.py`.

---

### D-136: Plugin Marketplace + Installer Contract

**Phase:** Sprint 59 | **Status:** Frozen

**Marketplace Store:** PluginMarketplaceStore manages plugin metadata (name, version, description, author, capabilities, risk_tier, source, trust_status). Plugins indexed from PluginManifest schema (D-118). Search by name/tag/category, filter by status. Install states: available → installed → enabled/disabled. Store persisted via JSON file (atomic_write_json per D-106).

**API Surface (10 endpoints):**
- `GET /api/v1/plugins` — list all (read)
- `GET /api/v1/plugins/search` — search/filter (read)
- `GET /api/v1/plugins/{id}` — detail (read)
- `POST /api/v1/plugins/{id}/install` — install (write, Task 59.3)
- `POST /api/v1/plugins/{id}/uninstall` — uninstall (write, Task 59.3)
- `POST /api/v1/plugins/{id}/enable` — enable (write, Task 59.3)
- `POST /api/v1/plugins/{id}/disable` — disable (write, Task 59.3)
- `PUT /api/v1/plugins/{id}/config` — update config (write, Task 59.3)
- `GET /api/v1/plugins/events` — event log (read)
- `GET /api/v1/plugins/stats` — dashboard stats (read)

**Installer Contract (Task 59.3):**
- **Source of truth:** Local plugin directory (`agent/plugins/`) with manifest.json.
- **Integrity:** Manifest validated via `load_manifest()` (D-118). Invalid manifest → fail-closed (reject install, log error, return 422).
- **Version policy:** One version per plugin name. Re-install overwrites. No multi-version support.
- **Rollback:** Uninstall deregisters from PluginRegistry + removes config. No rollback to previous version (single-version model).
- **Idempotency:** Install of already-installed plugin returns 409. Uninstall of not-installed returns 404.
- **Concurrency:** No concurrent installs of same plugin. Store-level lock per plugin ID.
- **Failure states:** Manifest validation failure → 422. Handler import failure → 422 + partial cleanup. Registry full → 507.
- **Audit trail:** All install/uninstall/enable/disable events logged to plugin event store.
- **Authorization:** No auth required (single-operator per D-108). Future: RBAC per D-117.

**Trust model:** All plugins local-only (no remote registry). PluginExecutor (D-118) provides 30s timeout + error isolation. Unknown/missing manifest fields → plugin rejected (fail-closed). Missing risk_tier defaults to "high".

**EventBus hot-reload:** Install registers handlers at priority 500+. Uninstall deregisters handlers. No restart required.

---

### D-137: WSL2 <-> PowerShell Bridge Contract

**Phase:** Sprint 60 | **Status:** Frozen

Canonical WSL2 <-> PowerShell bridge contract freeze. All cross-environment execution must go through oc-bridge.ps1 (stateless, allowlist-enforced, audit-logged, fail-closed, 30s timeout) or WMCP HTTP transport (mcp_client.py -> localhost:8001/PowerShell). Direct WSL subprocess calls (`wsl -d`) from agent code are denied and removed (3 legacy fallbacks quarantined: approval_service.py, telegram_bot.py, health_api.py). Secrets via env vars only. 19 enforcement tests validate bypass prevention, canonical path inventory, and bridge contract structure.
Formal record: `docs/decisions/D-137-wsl2-powershell-bridge-contract.md`.

---

### D-138: Approval Timeout=Deny Semantics + Escalation FSM

**Phase:** Sprint 61 | **Status:** Frozen

Canonical approval FSM: PENDING → APPROVED | DENIED | EXPIRED | ESCALATED. Timeout=deny doctrine: expired approval = denial, no mission proceeds on expired token. Terminal states (APPROVED, DENIED, EXPIRED) immutable — no reuse. Escalated re-enters decision cycle. Every state transition persisted to disk and emits `approval_decided` audit event. `decidedBy=system:timeout` for expired records. 31 enforcement tests covering approve/deny/expire/escalate/bypass/idempotency.
Formal record: `docs/decisions/D-138-approval-timeout-escalation-fsm.md`.

---

## Decision Index (D-001 → D-138)

137 frozen decisions. D-126 skipped, D-132 deferred.

| ID | Title | Phase |
|----|-------|-------|
| D-001 | Single Execution Owner = oc runtime | 1.5-A |
| D-002 | Terminology — orchestration vs conversation flow | 1.5-A |
| D-003 | Worker model — ephemeral -RunOnce | 1.5-A |
| D-004 | Bridge = stateless translation + auth gate | 1.5-A |
| D-005 | External surface is task-centric | 1.5-A |
| D-006 | Raw action invocation forbidden externally | 1.5-A |
| D-007 | Polling-only for Phase 1.5 | 1.5-A |
| D-008 | Stuck task policy — fail-closed + dead-letter + no auto-retry | 1.5-A |
| D-009 | Duplicate task creation accepted in Phase 1.5 | 1.5-A |
| D-010 | Retry not exposed externally in Phase 1.5 | 1.5-C |
| D-011 | External Bridge operations (Phase 1.5) | 1.5-C |
| D-012 | Approval model — definition-level preapproval | 1.5-C |
| D-013 | Allowlist fail-closed startup | 1.5-D |
| D-014 | Five-step validation order | 1.5-D |
| D-015 | Operator exception — local/manual/admin-only | 1.5-A |
| D-016 | Health response sanitized | 1.5-D |
| D-017 | Minimum audit — 10 fields per request | 1.5-D |
| D-018 | Bridge physical form — stateless single-invocation script | 1.5-E |
| D-019 | Canonical caller path — OpenClaw via WSL wrappers | TG-1R |
| D-020 | Project identity | Post-1.5 |
| D-021 | Agent Runner — single entry point for all agent execution | 3-B |
| D-022 | Agent architecture — registry-based, multi-agent extensible | 3-A |
| D-023 | run_powershell denied to general-assistant, executor-only | 3-A |
| D-024 | Tool access — role-scoped via Tool Gateway | 3-A |
| D-025 | Approval — service interface with correlation IDs | 3-A |
| D-026 | Artifacts — typed output, handoff contracts | 3-A |
| D-027 | Routing — deterministic table, not context-guessed | 3-A |
| D-028 | Framework — direct SDK calls, no LangChain | 3-A |
| D-029 | Hub-and-spoke — all handoffs through Mission Controller | 3-F |
| D-030 | Specialists share same LLM provider, differentiated by system prompt + tool policy | 3-F |
| D-031 | Sequential execution only in Phase 3-F, parallel deferred | 3-F |
| D-032 | Execution ladder — 4-tier complexity routing | 4 (Design, 3G-K) |
| D-033 | Cost governance — per-stage budget limits | 4 (Design, 3G-K) |
| D-034 | Discovery governance — analyst/architect only | 4 (Design, 3G-K) |
| D-035 | Cost class routing — model selection by role cost tier | 4 (Design, 3G-K) |
| D-036 | Skill contracts — machine-readable role-skill binding | 4 (Design, 3G-L) |
| D-037 | Working set concept — bounded per-stage file access | 4 (Design, 3G-L) |
| D-038 | Enforcer runs before Risk Engine | 4-0/1 |
| D-039 | Policy telemetry event types | 4-1 |
| D-040 | Summary cache — zero-cost reuse | 4-2 |
| D-041 | Five-tier context delivery (A through E) | 4-2 |
| D-042 | Reread auto-downgrade + expansion broker | 4-2 |
| D-043 | Artifact consumption logging | 4-2 |
| D-044 | Canonical path resolution | 4-0/1 |
| D-045 | Write authorization scope | 4-1 |
| D-046 | Per-stage budget isolation | 4-1H |
| D-047 | Artifact identity header — 12 mandatory fields | 4-2 |
| D-048 | Canonical role names + alias resolution | 4-2C |
| D-049 | Path resolution — absolute, case-normalized, traversal-safe | 4-0/1 |
| D-050 | Mission mode fail-closed gate | 4-1H |
| D-051 | Mutation surface mismatch detection | 4-2C |
| D-052 | Per-mission structured summary | 4-2C |
| D-053 | Mission mode fail-closed — working set required | 4-1H |
| D-054 | Feedback loops — quality improvement cycles | 4-5 |
| D-055 | Policy telemetry — 6 enforcer event types | 4-1H/2C |
| D-056 | Recovery triage — manager recovery before abort | 4-5C |
| D-057 | Startup metadata validation gate | 4-1H |
| D-058 | Path hardening — null byte + UNC rejection | 4-1H |
| D-059 | Read-only first, Controller sole executor | 5 (design) |
| D-060 | Polling → SSE, No WebSocket | 5B (Sprint 10) |
| D-061 | FastAPI from day 1 | 5A-1 (Sprint 8) |
| D-062 | Intervention via atomic file signal | 5C (Sprint 11) |
| D-063 | Approval via service layer | 5C (Sprint 11) |
| D-064 | Port assignment — API 8003, React 3000 | 5A (Sprint 8) |
| D-065 | Normalized API — MissionNormalizer | 5A-1 (Sprint 8) |
| D-066 | Legacy dashboard lives until 5D | 5D (Sprint 12) |
| D-067 | Schema frozen after 5A-1, additive-only | 5A-1 (Sprint 8) |
| D-068 | Unknown ≠ zero, data quality states | 5A–5B (Sprint 8–9) |
| D-069 | No control without acknowledgement | 5C (Sprint 11) |
| D-070 | DNS rebinding protection | 5A-1 (Sprint 8) |
| D-071 | Atomic file writes system-wide | 4.5-C → 5 (Sprint 7+) |
| D-072 | Per-source circuit breaker + per-panel error boundary | 5A (Sprint 8–9) |
| D-073 | Log rotation — 10MB / 5 files / 14 days | 5A-1 (Sprint 8) |
| D-074 | Startup sequence + ownership matrix | 5A-1 (Sprint 8) |
| D-075 | All state on ext4, cross-OS via API | 5A-1 (Sprint 8) |
| D-076 | SSE event ID = `{source}:{offset}` | 5B (Sprint 10) |
| D-077 | Sprint-End Documentation Policy | 4.5-C (Sprint 7) |
| D-078 | Sprint 7 E2E Partial Pass Waiver | 4.5-C → 5A-1 |
| D-079 | DataQuality Enum Amendment (D-068 update) | 5A-1 (Sprint 8) |
| D-080 | Service Registry Freshness Rule | 5A-1 (Sprint 8) |
| D-081 | CSS Framework — Tailwind CSS Utility-First | 5A-2 (Sprint 9) |
| D-082 | Type Generation — Manual TS Types from Frozen Pydantic Schemas | 5A-2 (Sprint 9) |
| D-083 | Polling — Global 30s + Manual Refresh, Page Visibility Pause | 5A-2 (Sprint 9) |
| D-084 | Error Boundary — Per-Panel Isolation, Per-Route Wrap | 5A-2 (Sprint 9) |
| D-085 | File Watcher — Manual mtime Polling 1s, Pure Python os.stat | 5B (Sprint 10) |
| D-086 | SSE Events — Per-Entity Invalidation Signal, Not Per-Field | 5B (Sprint 10) |
| D-087 | SSE Auth — Localhost-Only, D-070 Extension, No Extra Token | 5B (Sprint 10) |
| D-088 | SSE Reconnect — Backoff + Polling Fallback | 5B (Sprint 10) |
| D-089 | CSRF — Origin Header Check (SameSite browser-dependent) | 5C (Sprint 11) |
| D-090 | Mutation Confirm — Confirmation Dialog for Destructive Actions | 5C (Sprint 11) |
| D-091 | Mutation UI — Server-Confirmed, No Optimistic UI | 5C (Sprint 11) |
| D-092 | Approval Sunset Phase 1 | 5C (Sprint 11) |
| D-093 | Reserved — reassigned to D-097 | 5D (Sprint 12) |
| D-094 | Reserved — reassigned to D-098 | 5D (Sprint 12) |
| D-095 | Reserved — reassigned to D-099 | 5D (Sprint 12) |
| D-096 | Mutation Response Contract — Full Lifecycle | 5C (Sprint 11) |
| D-097 | Legacy dashboard retired — removal deferred | 5D (Sprint 12) |
| D-098 | API-level E2E with httpx + pytest — browser E2E deferred | 5D (Sprint 12) |
| D-099 | Approval model changes are Phase 6 scope | 5D (Sprint 12) |
| D-100 | OpenAPI spec auto-generated from FastAPI | 5D (Sprint 12) |
| D-101 | SSE is Mission Control frontend transport only — amends D-068 | 5D (Sprint 12) |
| D-102 | Token budget enforcement — 5-layer defense | Post-5D |
| D-103 | Complexity-based rework limits | Sprint 13 |
| D-104 | Backend Package Name = `app/` | Sprint 14A |
| D-105 | Sprint Closure Model — Model A / Model B | Sprint 16 |
| D-106 | Persistence Model — JSON File Store | Sprint 16 |
| D-107 | Alert Engine — Rule-Based Threshold Evaluation | Sprint 16 |
| D-108 | Session/Auth Model — Single-Operator Foundation | Sprint 16 |
| D-109 | Benchmark Strategy — Evidence-Only Model | Sprint 17 |
| D-110 | Documentation Model Hierarchy — Dual Source | Sprint 17 |
| D-111 | CLAUDE.md Rewrite — Compact Operating Brief | Sprint 18 |
| D-112 | Governance Consolidation — PROCESS-GATES + PROTOCOL → GOVERNANCE.md | Sprint 18 |
| D-113 | Archive Boundary — Active vs Historical Separation | Sprint 18 |
| D-114 | Handoff Model — Keep current.md Path | Sprint 18 |
| D-115 | Backend Physical Topology | Sprint 26 |
| D-116 | Docker Dev Runtime Topology | Sprint 26 |
| D-117 | Multi-User Auth Contract | Sprint 27 |
| D-118 | Plugin Runtime Contract | Sprint 29 |
| D-119 | Mission Template Lifecycle | Sprint 30 |
| D-120 | Scheduled/Triggered Missions | Sprint 30 |
| D-121 | Approval Gate Contract | Sprint 30 |
| D-122 | Backlog-to-Project-to-Sprint Contract | Sprint 31 |
| D-123 | Project V2 Item Contract v1 | Sprint 33 |
| D-124 | Legacy Normalization Boundary | Sprint 33 |
| D-125 | Closure State Sync | Sprint 33 |
| D-126 | *(Reserved — number gap, not used)* | — |
| D-127 | Sprint Closure Class Taxonomy | Sprint 34 |
| D-128 | Risk Classification Contract | Sprint 35 |
| D-129 | Secret Storage + Audit Integrity Contract | Sprint 36 |
| D-130 | Transport Encryption Contract | Sprint 37 |
| D-131 | Test Count Reporting Contract | Sprint 48 |
| D-132 | *(Deferred — Sprint folder naming standard, S49)* | — |
| D-133 | Policy Engine Contract | Sprint 48 |
| D-134 | Source User Identity Resolution Contract | Sprint 55 |
| D-135 | Secret Rotation + Allowlist + Metrics Contract | Sprint 57 |
| D-136 | Plugin Marketplace + Installer Contract | Sprint 59 |
| D-137 | WSL2 <-> PowerShell Bridge Contract | Sprint 60 |
| D-138 | Approval Timeout=Deny + Escalation FSM | Sprint 61 |
