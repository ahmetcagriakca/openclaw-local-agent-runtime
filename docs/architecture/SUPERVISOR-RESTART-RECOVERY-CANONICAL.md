# Runtime Startup / Logon / Watchdog — Canonical Documentation

**Status:** ACCEPTED (verified with live smoke tests)
**Version:** v3.5 (updated — F1.2 responsibility split)
**Date:** 2026-03-22

---

## 1. Design summary

Three distinct operational roles protect the runtime:

| Role | Script | Scheduled Task | Trigger | Purpose |
|------|--------|---------------|---------|---------|
| Startup Preflight | `oc-runtime-startup-preflight.ps1` | `OpenClawStartupPreflight` | AtStartup (boot) | Layout/script/manifest validation, stale lease recovery, stuck task detection, log rotation. No worker kick. |
| Logon Worker | `oc-task-worker.ps1` | `OpenClawTaskWorker` | AtLogOn | Process task queue, GUI-compatible, single-instance |
| Watchdog | `oc-runtime-watchdog.ps1` | `OpenClawRuntimeWatchdog` | Every 15 min | Health checks, stale lease recovery, stuck task detection, worker kick, log rotation |

Additional on-demand:
| Health reporter | `oc-task-health.ps1` | (none) | On demand | Status levels (ok/degraded/error), diagnostics |

### Scheduled tasks

| Task name | Config key | Trigger | Principal | Action |
|-----------|-----------|---------|-----------|--------|
| `OpenClawStartupPreflight` | `PreflightTaskName` | AtStartup (boot) | S4U (non-interactive) | Preflight |
| `OpenClawTaskWorker` | `SchedulerTaskName` | AtLogOn | Interactive | Worker -RunOnce |
| `OpenClawRuntimeWatchdog` | `WatchdogTaskName` | Every 15 min | S4U (non-interactive) | Watchdog |

All tasks: IgnoreNew (no duplicates), StartWhenAvailable, battery-safe.

### Config keys in `Get-OcRuntimeConfig`

| Key | Value |
|-----|-------|
| `PreflightScriptPath` | `bin\oc-runtime-startup-preflight.ps1` |
| `PreflightTaskName` | `OpenClawStartupPreflight` |
| `WorkerScriptPath` | `bin\oc-task-worker.ps1` |
| `SchedulerTaskName` | `OpenClawTaskWorker` |
| `WatchdogScriptPath` | `bin\oc-runtime-watchdog.ps1` |
| `WatchdogTaskName` | `OpenClawRuntimeWatchdog` |

---

## 2. Startup Preflight behavior (oc-runtime-startup-preflight.ps1)

Runs at machine boot. Non-interactive. Does NOT kick worker.

| Phase | Check | Repair action |
|-------|-------|---------------|
| 1. Runtime layout | All 10 required directories exist | Creates missing directories |
| 2. Key scripts | worker, runner, action runner, watchdog exist | Reports error (cannot self-fix) |
| 3. Manifest | Present and JSON-parseable | Reports error (cannot self-fix) |
| 4. Task definitions | All defs/*.json parseable | Reports degraded |
| 5. Scheduled tasks | All 3 tasks registered and not disabled | Reports degraded |
| 6. Stale leases | Leases older than 30 min | Moves back to pending |
| 7. Stuck tasks | Non-terminal tasks older than 60 min | Reports degraded |
| 8. Log rotation | control-plane.log, worker.log, action-execution.log | Rotates at 5MB, keeps 3 |
| 9. Worker status | Mutex check (observe only) | Reports degraded if pending tickets, no kick |

Log prefix: `[preflight]`

---

## 3. Watchdog behavior (oc-runtime-watchdog.ps1)

Runs every 15 minutes. Non-interactive. DOES kick worker when needed.

| Phase | Check | Repair action |
|-------|-------|---------------|
| 1. Runtime layout | All 10 required directories exist | Creates missing directories |
| 2. Key scripts | worker, runner, action runner exist | Reports error (cannot self-fix) |
| 3. Manifest | Present and JSON-parseable | Reports error (cannot self-fix) |
| 4. Scheduled tasks | All 3 tasks registered and not disabled | Reports degraded |
| 5. Stale leases | Leases older than 30 min | Moves back to pending |
| 6. Stuck tasks | Non-terminal tasks older than 60 min | Reports degraded |
| 7. Worker alive | Mutex check + pending ticket count | **Kicks worker** if pending tickets exist but no worker active |
| 8. Log rotation | control-plane.log, worker.log, action-execution.log | Rotates at 5MB, keeps 3 |

Log prefix: `[watchdog]`

---

## 4. Health status levels (oc-task-health.ps1)

| Level | Meaning |
|-------|---------|
| `ok` | All checks pass, no stuck tasks, scripts present |
| `degraded` | Operational but attention needed: stuck tasks, scheduled task disabled, pending tickets with no worker |
| `error` | Critical: key scripts missing |

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | ok / degraded / error |
| `statusReasons` | string[] | List of reasons for non-ok status |
| `workerActive` | bool | Is worker mutex held (worker running) |
| `scheduledTaskState` | string | Worker scheduled task state |
| `watchdogTaskState` | string | Watchdog scheduled task state |
| `preflightTaskState` | string | Preflight scheduled task state |

---

## 5. Retired terminology

| Old term | New term | Reason |
|----------|----------|--------|
| `oc-runtime-supervisor.ps1` | `oc-runtime-watchdog.ps1` | "Supervisor" conflated boot and periodic roles |
| `OpenClawRuntimeSupervisor` | `OpenClawRuntimeWatchdog` | Clear periodic-only identity |
| `SupervisorScriptPath` | `WatchdogScriptPath` | Config key alignment |
| `SupervisorTaskName` | `WatchdogTaskName` | Config key alignment |
| `supervisorTaskState` | `watchdogTaskState` | Health output field alignment |
| `[supervisor]` log tag | `[watchdog]` log tag | Log clarity |

The old `oc-runtime-supervisor.ps1` file has been removed (Phase 1.5-B cleanup). It is fully superseded by `oc-runtime-watchdog.ps1`.

---

## 6. Remaining limitations

| Limitation | Description |
|------------|-------------|
| Watchdog auto-resolves Case A stuck tasks | Case A (no worker, no lease) tasks are auto-failed/cancelled. Case B (ambiguous) requires `oc-task-repair.ps1`. See ARCHITECTURE.md section 8.1. |
| No restart simulation | Scheduled task behavior at boot was not directly tested via reboot. |
| Dead-letter queue passive | Watchdog does not auto-clean dead-letter tickets. |
| Worker zombie detection limited | If worker becomes zombie holding mutex, watchdog cannot detect this. Only system restart clears it. |
| 15-minute watchdog interval | Pending tickets could wait up to 15 min if no worker kick happens otherwise. |
| Bootstrap supervisor cleanup | Legacy supervisor removal block cleaned in Phase 1.5-B. Bootstrap v3.4 correctly registers watchdog + preflight tasks. |
