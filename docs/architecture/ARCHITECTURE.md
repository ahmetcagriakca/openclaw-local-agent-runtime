# Vezir + oc runtime Architecture

**Status:** Canonical
**Version:** vCurrent
**Date:** 2026-03-27 (updated: OpenClaw → Vezir rebrand)

---

## 1. Purpose

This architecture defines the responsibility boundaries, execution model, stabilization priorities, and security baseline for the Vezir + oc runtime system.

The primary objective is:

**A user sends a message, the system safely translates it into a task, the task is executed reliably on the local machine, and the result is returned clearly without manual script/log juggling.**

This architecture is intentionally split into distinct layers to avoid orchestration overlap and drift.

---

## 2. System Overview

The system has three layers:

1. **Vezir / Telegram**
2. **Bridge**
3. **oc runtime**

### 2.1 Vezir / Telegram
This is the conversation and intent layer.

Responsibilities:
- receive user messages
- interpret user intent
- collect/prepare arguments
- ask for approval if needed
- present results back to the user

Non-responsibilities:
- does not own execution
- does not run its own queue/worker model
- does not call raw actions directly
- does not bypass the runtime task control plane

### 2.2 Bridge
This is the narrow translation and trust-boundary layer between Vezir and oc runtime.

Responsibilities:
- convert intent into canonical task contract
- enforce source authentication / authorization
- apply Telegram allowlist
- attach policy context
- call only the canonical task surface
- translate structured runtime responses into user-facing replies

Non-responsibilities:
- does not run actions directly
- does not own queue semantics
- does not reinterpret runtime state
- does not become a second orchestrator

### 2.3 oc runtime
This is the reliable local execution layer.

Responsibilities:
- validate incoming task contracts
- accept or reject tasks
- manage queue / worker / runner
- execute actions
- provide retry / cancel / health
- perform recovery / watchdog / preflight
- produce artifacts, logs, task state, and events

Non-responsibilities:
- does not interpret natural language
- does not choose user intent
- does not own Telegram/chat UX

---

## 3. Responsibility Boundaries

### 3.1 Vezir does
- intent extraction
- task selection
- parameter preparation
- approval UX
- result narration

### 3.2 Vezir does not
- manage runtime queue directly
- call raw actions
- implement parallel execution semantics
- override runtime task state

### 3.3 Bridge does
- source validation
- allowlist enforcement
- task contract mapping
- structured error forwarding
- task API invocation

### 3.4 Bridge does not
- call action scripts directly
- run its own queue/worker model
- invent retry semantics
- mutate runtime state outside canonical APIs

### 3.5 oc runtime does
- validate task contracts
- reject invalid or disallowed requests
- enqueue and execute tasks
- manage retry / cancel / health
- perform startup preflight / watchdog / recovery

### 3.6 oc runtime does not
- parse natural language
- choose user intent
- manage Telegram interaction
- duplicate bridge authorization logic

---

## 4. Canonical External Task Surface

Only the following task-centric surface is exposed externally:

- `enqueue_task`
- `get_task`
- `list_tasks`
- `get_task_output`
- `retry_task`
- `cancel_task`
- `task_healthcheck`

**Raw action surface is not exposed externally.**

This is a hard architecture rule.

---

## 5. Runtime Layout

The canonical runtime root is:

`%USERPROFILE%\oc\`

Expected layout:

```text
oc\
  bin\
  actions\
  defs\
    tasks\
  queue\
    pending\
    leases\
    dead-letter\
  tasks\
  logs\
  results\
```

### 5.1 Directory roles

- `bin\`  
  orchestration, control-plane, watchdog, preflight, health, bootstrap scripts

- `actions\`  
  executable action scripts and manifest

- `defs\tasks\`  
  task definitions

- `queue\pending\`  
  queued task tickets

- `queue\leases\`  
  claimed/in-flight task leases

- `queue\dead-letter\`  
  failed/dead-letter tickets

- `tasks\`  
  per-task state directories (`task.json`, `events.jsonl`, step logs, artifacts)

- `logs\`  
  worker, control-plane, watchdog, preflight, and health-related logs

- `results\`  
  user-facing output artifacts

---

## 6. Execution Model

### 6.1 Worker / Runner Model
- orchestration runs on **pwsh 7**
- action execution runs on **powershell.exe 5.1**
- GUI-capable actions remain compatible with interactive user sessions

### 6.2 Task Model
A task is the canonical execution unit.

A task has:
- `taskId`
- `taskName`
- `status`
- `input`
- `steps`
- `events`
- `artifacts`
- `lastError`
- optional retry linkage metadata

### 6.3 Retry Model
Retry uses **current task definition semantics**, not historical step replay.

Rules:
- retry never resurrects the original task in place
- retry always creates a **new task**
- original input snapshot is preserved
- current task definition is re-read at retry time
- original task remains immutable except for retry event append

Key fields/events:
- `retriedFromTaskId`
- `retriedAtUtc`
- `retryChainDepth`
- `task_retried`
- `task_created_by_retry`

---

## 7. Startup / Logon / Watchdog Model

These three roles are **distinct scripts, distinct scheduled tasks, and distinct triggers**.

| Role | Script | Scheduled Task | Trigger | Type |
|------|--------|---------------|---------|------|
| Startup Preflight | `oc-runtime-startup-preflight.ps1` | `OpenClawStartupPreflight` | `AtStartup` (boot) | non-interactive |
| Logon Worker | `oc-task-worker.ps1` | `OpenClawTaskWorker` | `AtLogOn` | interactive |
| Watchdog | `oc-runtime-watchdog.ps1` | `OpenClawRuntimeWatchdog` | periodic (every 15 min) | non-interactive |

### 7.1 Startup Preflight
**Script:** `bin/oc-runtime-startup-preflight.ps1`
**Task:** `OpenClawStartupPreflight`
**Config:** `PreflightScriptPath`, `PreflightTaskName`
**Trigger:** `AtStartup` (`MSFT_TaskBootTrigger`)
**Type:** non-interactive, S4U logon

Responsibilities:
- validate runtime layout
- validate key scripts (worker, runner, action runner, watchdog)
- validate manifest
- validate task definitions
- validate all 3 scheduled tasks
- recover stale leases
- detect stuck tasks
- rotate logs
- emit health/status logging with `[preflight]` tag

Non-responsibilities:
- does **not** launch GUI actions
- does **not** launch or kick the worker

### 7.2 Logon Worker
**Script:** `bin/oc-task-worker.ps1`
**Task:** `OpenClawTaskWorker`
**Config:** `WorkerScriptPath`, `SchedulerTaskName`
**Trigger:** `AtLogOn`
**Type:** interactive, single-instance (mutex: `Global\OpenClawTaskWorker`)

Responsibilities:
- start interactive worker (with `-RunOnce` at logon)
- preserve GUI-capable action compatibility
- enforce single worker instance via mutex

Non-responsibilities:
- does **not** perform health checks
- does **not** recover stale leases

### 7.3 Watchdog
**Script:** `bin/oc-runtime-watchdog.ps1`
**Task:** `OpenClawRuntimeWatchdog`
**Config:** `WatchdogScriptPath`, `WatchdogTaskName`
**Trigger:** periodic (every 15 min)
**Type:** non-interactive maintenance

Responsibilities:
- detect missing worker
- detect pending queue with no worker
- detect stale leases and recover them
- detect stuck tasks
- surface degraded conditions
- safely kick worker when appropriate
- rotate logs
- emit health/status logging with `[watchdog]` tag

Non-responsibilities:
- does **not** launch GUI actions
- is **not** a startup script (runs periodically, not at boot)
- avoids thrashing / restart storms

---

## 8. Stabilization Policy

### 8.1 Stuck Task Default Policy

**Status:** FROZEN (F1.4). Implemented in watchdog, preflight, health, repair.

#### Threshold model

All thresholds are centralized in `Get-OcRuntimeConfig`:

| Config key | Default | Purpose | Used by |
|------------|---------|---------|---------|
| `StuckWarningMinutes` | 30 | Early warning visibility | health |
| `StuckRecoveryMinutes` | 60 | Recovery decision boundary | watchdog, preflight |
| `StaleLeaseMinutes` | 30 | Lease age before recovery | watchdog, preflight |

Health surfaces stuck tasks earlier (30 min) for visibility.
Watchdog/preflight only act or classify at the recovery threshold (60 min).
This is intentional — warning before action.

#### Case A — Safe stuck (auto-resolved by watchdog)
Conditions:
- task is non-terminal (running/queued/cancel_requested)
- age exceeds recovery threshold (`StuckRecoveryMinutes`, default 60 min)
- worker is NOT active (no mutex)
- no lease exists for this task

Action:
- mark task as `failed` (or `cancelled` if `cancel_requested`)
- write structured `lastError` with policy reference
- append `stuck_task_auto_failed` / `stuck_task_auto_cancelled` event
- do **not** auto-retry
- log `[watchdog] Case A` entry

#### Case B — Ambiguous stuck (reported as degraded, no mutation)
Conditions:
- task is non-terminal, age exceeds threshold
- worker IS active OR lease exists for this task

Action:
- do not mutate silently
- report `degraded` status
- log `[watchdog] Case B` entry
- require `oc-task-repair.ps1` or manual action

#### Case C — Terminal task with stale lease (auto-cleaned by watchdog)
Conditions:
- task is terminal (succeeded/failed/cancelled)
- a lease file still references this task

Action:
- remove stale lease file
- append `stale_lease_removed` event to task
- log `[watchdog] Case C` entry

**Rule:** safe auto-fix is allowed; unsafe states must degrade visibly.

#### Preflight behavior
Preflight classifies stuck tasks into Case A/B but does **not** mutate.
It reports counts and logs for visibility. Watchdog handles actual resolution.

#### Health visibility
Health script reports `stuckCaseA` and `stuckCaseB` counts separately.

---

## 9. Runtime Rejection Contract

oc runtime does **not** interpret intent, but it **does** validate task contracts and reject invalid or disallowed requests.

**Status:** FROZEN (F1.3). Implemented in `oc-task-enqueue.ps1`, `oc-task-retry.ps1`, `oc-task-cancel.ps1`.

### Canonical rejection envelope

```json
{
  "status": "rejected",
  "reasonCode": "INVALID_TASK_INPUT",
  "message": "Missing required field: filename.",
  "taskName": "create_note",
  "source": "telegram"
}
```

Fields:
- `status` — always `"rejected"`
- `reasonCode` — one of the canonical codes below
- `message` — human-readable explanation
- `taskName` — present when known (optional)
- `taskId` — present when known (optional)
- `source` — present when provided by caller (optional)

### Canonical `reasonCode` values

| Code | Meaning | Used by |
|------|---------|---------|
| `UNKNOWN_TASK` | Task definition or task record not found | enqueue, retry, cancel |
| `INVALID_TASK_INPUT` | Bad format, empty name, invalid JSON, missing steps | enqueue, retry, cancel |
| `TASK_POLICY_DENIED` | Not enabled for queueing, retry limit reached | enqueue, retry |
| `SOURCE_NOT_ALLOWED` | Source not in allowlist (reserved for bridge) | (future) |
| `APPROVAL_REQUIRED` | Task requires approval not yet granted | enqueue, retry |
| `TASK_STATE_INVALID` | Wrong state for requested operation | retry, cancel |
| `RUNTIME_UNAVAILABLE` | Runtime cannot accept requests (reserved) | (future) |

### Implementation

Helper functions in `oc-task-common.ps1`:
- `New-OcRejection` — creates envelope object
- `Write-OcRejectionAndExit` — logs `[rejection]` to control-plane.log, outputs JSON, exits 1

All rejections are logged with `[rejection]` prefix in `control-plane.log`.

### Exit code invariant

- `status: "rejected"` => exit code **1** (always, no exceptions)
- `status: "queued"`, `"cancelled"`, `"cancel_requested"` => exit code **0**
- No canonical path may return `status: "rejected"` with exit code 0.

### Evidenced reason codes (F1.3-cleanup)

| Code | Evidenced | Script | Trigger |
|------|-----------|--------|---------|
| `UNKNOWN_TASK` | yes | enqueue, cancel | nonexistent task name / task ID |
| `INVALID_TASK_INPUT` | yes | enqueue | bad base64, bad JSON |
| `TASK_POLICY_DENIED` | yes | enqueue | `enqueueEnabled: false` |
| `APPROVAL_REQUIRED` | yes | enqueue | `approvalPolicy: manual` |
| `TASK_STATE_INVALID` | yes | retry, cancel | retry succeeded, cancel terminal |
| `SOURCE_NOT_ALLOWED` | reserved | — | bridge phase |
| `RUNTIME_UNAVAILABLE` | reserved | — | health-gate phase |

This contract is part of runtime stabilization and must remain stable once frozen.

---

## 10. Bridge Contract

### 10.1 OpenClaw -> Bridge input

```json
{
  "intent": "create_note",
  "arguments": {
    "filename": "note.txt",
    "content": "hello"
  },
  "source": "telegram",
  "sourceUserId": "123456789",
  "requestId": "req-001"
}
```

### 10.2 Bridge -> oc runtime input

```json
{
  "taskName": "create_note",
  "inputBase64": "...",
  "policyContext": {
    "source": "telegram",
    "sourceUserId": "123456789",
    "requestId": "req-001",
    "approvalMode": "auto"
  }
}
```

### 10.3 oc runtime -> Bridge response

Successful enqueue:

```json
{
  "status": "queued",
  "taskId": "task-...",
  "taskName": "create_note"
}
```

Structured rejection:

```json
{
  "status": "rejected",
  "reasonCode": "SOURCE_NOT_ALLOWED",
  "message": "Source user is not allowed.",
  "taskName": "create_note",
  "source": "telegram"
}
```

### 10.4 Bridge -> user response
Bridge translates runtime responses into user-facing language, such as:
- “Görev sıraya alındı.”
- “Bu komut için yetkin yok.”
- “Eksik parametre var.”
- “Runtime şu an uygun değil.”

---

## 11. Security Baseline

### 11.1 Telegram bot token policy
Minimum mandatory rules:
- token must not be committed to repo
- token must not be hardcoded in scripts
- token must be stored as a secret
- token must be rotatable
- token rotation procedure must be documented
- token access must be kept narrow

### 11.2 Telegram user allowlist
Minimum mandatory rules:
- allowlist outside users cannot access task surface
- allowlist check occurs at bridge entry
- rejected requests do not reach runtime
- authorization failures are logged/audited

### 11.3 Source trust
No external source is trusted by default.  
Every source, including Telegram, must be:
- authenticated
- authorized
- policy-limited

### 11.4 Future policy expansion
Later phases must define:
- task whitelist
- low-risk vs high-risk tasks
- approval-required tasks
- file-writing boundaries
- GUI-launch boundaries
- forbidden tasks

---

## 12. GUI Action Semantics

GUI-launching actions must be explicit.

Supported semantics:
- `launch_return`
- `launch_wait_exit`

### 12.1 launch_return
- launch GUI app
- return immediately
- task succeeds once launch is confirmed

### 12.2 launch_wait_exit
- launch GUI app
- wait for process exit
- task completion depends on process exit

The mode must be explicit in task definition or payload/wrapper contract.

`open_notepad` uses:
- `executionMode: launch_return`

This is the default verified behavior.

---

## 13. Canonical Health Model

Health output must support:
- `ok`
- `degraded`
- `error`

Minimum health questions the system must answer:
- Is runtime up?
- Is worker available?
- Are there stale leases?
- Are there stuck tasks?
- Did startup preflight / watchdog run?
- Are scheduled tasks present?
- Is the system healthy, degraded, or broken?

---

## 14. Phase Plan

### Phase 1 — Runtime Stabilization
Scope:
- task control plane stabilization
- retry
- bootstrap idempotency
- config centralization
- naming cleanup
- GUI action semantics
- startup/logon/watchdog responsibility split
- true startup preflight
- reboot smoke test
- stuck task policy
- structured runtime rejection

**Definition of done:**
- true `AtStartup` preflight exists
- `AtLogOn` interactive worker exists
- watchdog exists and is safe
- stale lease recovery exists in startup path
- stuck task policy is frozen
- runtime structured rejection is stable
- real reboot smoke test passes

### Phase 1.5 — Bridge Validation + Minimum Security Baseline
Scope:
- Telegram -> Vezir intent
- Vezir -> bridge contract
- bridge -> oc runtime task call
- result -> Telegram return
- Telegram allowlist
- token handling / rotation policy
- source authorization baseline

**Definition of done:**
- message -> task -> result path works end-to-end
- allowlist is enforced
- token policy is documented and used
- bridge calls only canonical task APIs
- runtime accept/reject is surfaced clearly

### Phase 2 — Security / Policy Hardening
Scope:
- task whitelist
- source-to-task authorization matrix
- risk classification
- approval routing
- file-system confinement
- unsafe request rejection
- auditability

### Phase 3 — Conversation-to-Execution Productization
Scope:
- deterministic intent -> task mapping
- user-facing result rendering
- standard task library
- retry/cancel guidance
- cleaner summaries and UX

### Phase 4 — Reproducibility / Disaster Recovery
Scope:
- clean-environment bootstrap
- fresh install smoke test
- backup/restore
- corrupted runtime recovery
- deterministic redeploy

---

## 15. Prioritized Backlog

### P0
- true `AtStartup` preflight
- startup/logon/watchdog responsibility split
- reboot smoke test
- freeze stuck task policy in code/docs
- standardize runtime rejection envelope

### P1
- Bridge Contract Freeze
- Telegram allowlist
- bot token storage + rotation policy
- Vezir -> oc runtime basic enqueue path
- structured rejection -> user-visible mapping

### P2
- task whitelist
- source/task authorization matrix
- approval model
- file system confinement
- unsafe task rejection expansion

### P3
- user-facing result rendering
- standard task library
- fresh install / disaster recovery
- runtime freeze / version discipline

---

## 16. Non-Goals

The following are explicitly out of scope unless later approved:
- second orchestration layer outside oc runtime
- raw external action execution
- broad service refactor that breaks GUI compatibility
- premature multi-step workflow expansion
- webhook-heavy productization before bridge stabilization
- broad architecture redesign

---

## 17. Phase 1.5-A Closure — Frozen Decisions

**Status:** FROZEN (Phase 1.5-A). These decisions are authoritative and must not be reopened.

### 17.1 Ownership Boundaries

| Owner | Responsibilities |
|-------|-----------------|
| **Vezir** | Conversation flow, intent extraction, approval UX, result narration |
| **Bridge** | Translation, trust boundary, allowlist enforcement. **Never an orchestrator.** |
| **oc runtime** | **Sole owner of task execution orchestration.** Queue, worker, runner, recovery, health. |

### 17.2 Integration Surface

- External integration surface is **task-centric only** (enqueue, get, list, cancel, retry, health).
- **Raw action invocation is forbidden** as an external integration path.
- Local manual operator CLI (`oc-run-action.ps1`, `oc-run-file.ps1`) is an admin maintenance exception, not a general integration path.

### 17.3 Worker Model Supersession

- The canonical worker model for Phase 1.5 is **ephemeral single-pass** (process pending tickets, then exit).
- Any earlier wording that implies a **persistent execution worker** (polling loop, long-running daemon) as the canonical model is **superseded**.
- The `-RunOnce` flag is accepted for backward compatibility; behavior is always single-pass.
- Worker activation paths: AtLogOn scheduled task, enqueue kick, retry kick, watchdog backstop kick.

---

## 18. Final Architecture Statement

This system is finalized around a simple rule:

**Vezir handles conversation and intent.
Bridge handles translation and trust boundaries.
oc runtime handles reliable local execution.**

Execution has one owner.
Security boundaries are explicit.
Recovery is conservative.
The external control surface is task-centric.
All future work must preserve these constraints.

---

## 19. Agent System Architecture (Phase 3-4)

This section documents the AI agent layer added in Phases 3 and 4, which sits above the oc runtime task system.

### 19.1 Overview

The agent system provides AI-powered automation where an LLM interprets user requests, selects from 24 named tools, and executes them via MCP on Windows. In mission mode, a Mission Controller orchestrates 9 governed specialist roles through quality gates and feedback loops.

### 19.2 Execution Modes

| Mode | Entry | Description |
|------|-------|-------------|
| Single-agent | `oc-agent-runner.py -m "..."` | One LLM + tools, direct execution |
| Mission | `oc-agent-runner.py --mission -m "..."` | MissionController + 9 roles + gates |

### 19.3 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Agent Runner | `agent/oc-agent-runner.py` | CLI entry point |
| Mission Controller | `agent/mission/controller.py` | Multi-agent orchestrator |
| Role Registry | `agent/mission/role_registry.py` | 9 role definitions |
| Skill Contracts | `agent/mission/skill_contracts.py` | 10 machine-readable contracts |
| Complexity Router | `agent/mission/complexity_router.py` | Tier 0/2 classification |
| Quality Gates | `agent/mission/quality_gates.py` | 3 gates between stages |
| Feedback Loops | `agent/mission/feedback_loops.py` | Dev↔Tester, Dev↔Reviewer |
| Mission State | `agent/mission/mission_state.py` | 10-state formal machine |
| Artifact Extractor | `agent/mission/artifact_extractor.py` | 3-tier structured field extraction |
| Context Assembler | `agent/context/assembler.py` | 5-tier artifact delivery |
| Working Set Enforcer | `agent/context/working_set_enforcer.py` | Bounded filesystem access |
| Policy Telemetry | `agent/context/policy_telemetry.py` | 20 event types, JSONL |

### 19.4 Design References

Detailed agent architecture is documented in:
- `docs/ai/DECISIONS.md` — 58 frozen decisions (D-001→D-058)
- `docs/ai/PHASE-4-DESIGN-INDEX.md` — Phase 4 design document index
- Phase 4 Sprint Reports in `docs/phase-reports/`

### 19.5 Relationship to oc runtime

The agent system is a CONSUMER of oc runtime, not a replacement.
- Agent Runner calls MCP tools which execute PowerShell via WMCP
- Mission mode uses the same tool catalog and risk engine
- oc runtime task queue remains the canonical execution layer for
  predefined tasks (Bridge path)
- Agent path is for interactive AI-driven requests (Telegram/CLI path)
