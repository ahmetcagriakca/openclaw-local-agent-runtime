# Architectural Decisions

**Last updated:** 2026-03-24

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

## D-029: Multi-agent uses hub-and-spoke

**Phase:** 3-F | **Status:** Frozen

All agent handoffs go through Mission Controller. Agents never call each other directly. Controller owns success/failure, stage sequencing, and artifact collection. Prevents circular dependencies and makes debugging deterministic.

---

## D-030: Specialists differentiated by system prompt + tool policy

**Phase:** 3-F | **Status:** Frozen

Specialist agents (analyst, executor) use the same underlying LLM provider but receive different system prompts and filtered tool sets. This avoids config explosion while enforcing role boundaries. Future: each specialist can use a different provider/model.

---

## D-031: Sequential stage execution in Phase 3-F

**Phase:** 3-F | **Status:** Active

Mission stages execute sequentially (A → B → C). Each stage receives artifacts from all previous stages as context. Parallel execution deferred — requires concurrency control, conflict resolution, and artifact merge logic.

---

## D-028: Framework — direct SDK calls, multi-provider

**Phase:** 3-A/3-B/3-E | **Status:** Active

Direct SDK calls, no LangChain. Three providers implemented: GPT-4o (active), Claude (ready, needs API key), Ollama (ready, needs local server). Provider factory in `agent/providers/factory.py` selects provider from `agent-config.json`. Each provider converts OpenAI tool format internally. LangChain not needed — 3 providers added without it.

---

## D-032: 7-tier execution ladder

**Phase:** 3-G | **Status:** Frozen

Deterministic → Ollama → GPT/Sonnet → MCP → Opus → remote → computer-use. Each tier escalates cost and capability. Lower tiers attempted first.

---

## D-033: Remote control = quarantined last resort

**Phase:** 3-G | **Status:** Frozen

Remote control is disabled by default, quarantined as last resort. Requires explicit operator enablement.

---

## D-034: 10 cost governance rules

**Phase:** 3-G | **Status:** Frozen

Cost budgets per complexity class: trivial $0.05, simple $0.50, medium $2.00, complex $5.00, XL $15.00. Prevents runaway LLM spending.

---

## D-035: Cost budget per complexity class

**Phase:** 3-G | **Status:** Frozen

Each complexity tier has a hard dollar ceiling. Mission aborts if cumulative token cost exceeds the tier budget.

---

## D-036: READ ONCE, DISTRIBUTE MANY

**Phase:** 4 | **Status:** Frozen

Governing principle for context economy. A file is read once by the discovering role (analyst), then distributed as typed artifacts to downstream roles. No re-discovery.

---

## D-037: Discovery restricted to Analyst/Architect

**Phase:** 4 | **Status:** Frozen

Only Analyst and Architect have broad filesystem discovery rights. All other roles consume typed artifacts from upstream stages.

---

## D-038: Downstream roles consume typed artifacts

**Phase:** 4 | **Status:** Frozen

Developer, Tester, Reviewer, Manager receive pre-packaged artifacts (discovery_map, technical_design, etc.) rather than re-reading the filesystem.

---

## D-039: Role vs Skill model

**Phase:** 4 | **Status:** Frozen

Roles own skills, skills define contracts. Each role has allowedSkills and forbiddenSkills. Each skill contract specifies inputArtifact, outputArtifact, and tool requirements.

---

## D-040: Context Assembler — 5-tier delivery

**Phase:** 4 | **Status:** Frozen

5 delivery tiers: A (metadata only), B (summary), C (scoped/partial), D (full content), E (full + neighbors). Each role gets the cheapest sufficient tier per the artifact×role matrix.

---

## D-041: Artifact×Role tier matrix

**Phase:** 4 | **Status:** Frozen

Matrix maps (artifact_type, requesting_role) → delivery tier. Analyst gets Tier D for discovery_map; Manager gets Tier B for code_delivery. Prevents context bloat.

---

## D-042: Reread escalation policy

**Phase:** 4 | **Status:** Frozen

Second full read of the same artifact auto-downgrades to summary tier. Prevents context window waste from redundant reads.

---

## D-043: Claude priority lanes

**Phase:** 4 | **Status:** Frozen

Three Claude priority lanes: architecture_synthesis (#1), quality_review (#2), recovery_triage (#3). High-leverage cognitive tasks routed to Claude; mechanical tasks stay on GPT-4o.

---

## D-044: Developer forbidden from controlled_execution

**Phase:** 4 | **Status:** Frozen

Developer role cannot use controlled_execution skill. Prevents code-writing role from also executing arbitrary system commands.

---

## D-045: Two-surface mutation model

**Phase:** 4 | **Status:** Frozen

Code surface: developer + write_file (bounded to working set). System surface: remote-operator + all operational tools. No role spans both surfaces.

---

## D-046: Single Working Set Enforcer middleware

**Phase:** 4 | **Status:** Frozen

Working Set Enforcer runs as middleware before the risk engine. Validates all file paths against the stage's declared working set. Fail-closed: path outside working set = blocked.

---

## D-047: Artifact identity header

**Phase:** 4 | **Status:** Frozen

Every artifact carries identity metadata: artifactId, contentHash, lineage (parent artifacts), compression pointers. Enables deduplication and provenance tracking.

---

## D-048: Canonical role name remote-operator

**Phase:** 4 | **Status:** Frozen

`remote-operator` is the canonical name. `executor` retired as alias. All code and docs use `remote-operator`.

---

## D-049: Canonical path enforcement

**Phase:** 4 | **Status:** Frozen

Path validation pipeline: normalize → resolve → symlink check → compare against working set. Fail-closed: any step failure = path rejected. Prevents path traversal attacks.

---

## D-050: Tool governance from mandatory catalog metadata

**Phase:** 4 | **Status:** Frozen

Tool access governance derived from tool catalog metadata (risk level, mutation surface, filesystem impact), not hardcoded lists. Adding a new tool automatically inherits governance.

---

## D-051: Developer write authorization target-bound

**Phase:** 4 | **Status:** Frozen

Developer can only write to paths declared as readWrite, creatable, or generatedOutputs in the stage's working set. All other paths are read-only or forbidden.

---

## D-052: Source of truth hierarchy

**Phase:** 4 | **Status:** Frozen

Consolidated design document v3 is the master reference. Sprint reports are implementation evidence. docs/ai/ state files are living summaries. Conflicts resolved by hierarchy: consolidated > sprint > state files.

---

## D-053: Mission mode fail-closed on missing working set

**Phase:** 4 | **Status:** Frozen

If working_set is None, the stage cannot start. Mission Controller must provide a working set for every stage. Prevents unbounded filesystem access.

---

## D-054: Premium escalation per-stage only

**Phase:** 4 | **Status:** Frozen

Premium model escalation (e.g., to Opus) happens per-stage, not per-mission. A single complex stage can escalate without affecting other stages' model selection.

---

## D-055: 20 mandatory telemetry event types

**Phase:** 4 | **Status:** Frozen

Policy telemetry emits 20 standardized event types covering tool calls, working set checks, context delivery, gate results, and state transitions. All events are append-only to JSONL.

---

## D-056: Recovery default = recovery_triage not restart

**Phase:** 4 | **Status:** Frozen

When a stage fails, the default recovery action is recovery_triage (analyst diagnoses the failure), not blindly restarting the failed stage. Prevents infinite retry loops.

---

## D-057: Startup metadata gate

**Phase:** 4 | **Status:** Frozen

At runtime startup, all tools are validated against their catalog metadata. A broken tool (missing command, invalid schema) prevents the runtime from starting. Fail-fast, not fail-at-call-time.

---

## D-058: Windows path hardening — 9-case test corpus

**Phase:** 4 | **Status:** Frozen

Path resolver tested against 9 edge cases: UNC paths, mixed separators, relative escapes, symlinks, junction points, null bytes, very long paths, reserved device names, trailing dots/spaces. All must be rejected or normalized correctly.
