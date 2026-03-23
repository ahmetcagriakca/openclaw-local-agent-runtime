# Naming Drift Cleanup + GUI Action Semantics — Canonical Documentation

**Status:** ACCEPTED (verified with live smoke tests)
**Version:** v3.4 (updated)
**Date:** 2026-03-22

---

## Part 1 — Naming drift cleanup

### What changed

| Identifier | Before | After |
|-----------|--------|-------|
| Scheduled task name | `OpenClawTaskWorkerV2` | `OpenClawTaskWorker` |
| Worker mutex name | `Global\OpenClawTaskWorkerV2` | `Global\OpenClawTaskWorker` |

Both values are defined in one place: `Get-OcRuntimeConfig` in `oc-task-common.ps1`.

### Migration

Bootstrap v3.4 handles migration automatically:
1. Checks for legacy `OpenClawTaskWorkerV2` scheduled task
2. If found, unregisters it (`Unregister-ScheduledTask -Confirm:$false`)
3. Registers new `OpenClawTaskWorker` task

This is a one-time migration. Subsequent bootstrap runs find no legacy task.

### Files changed

| File | Change |
|------|--------|
| `bin/oc-task-common.ps1` | `SchedulerTaskName` and `WorkerMutexName` updated (via bootstrap heredoc) |
| `oc-task-runtime-bootstrap-v3.4.ps1` | Config heredoc updated + legacy task removal logic added |

### Verification

Legacy task `OpenClawTaskWorkerV2`: not found (exit code 1 from Get-ScheduledTask).
New task `OpenClawTaskWorker`: State = Ready.
Zero `WorkerV2` or `TaskWorkerV2` references remain in `bin/*.ps1`.

---

## Part 2 — GUI action semantics

### Execution modes

| Mode | Behavior | Task terminal state |
|------|----------|-------------------|
| `launch_return` (default) | Launch GUI process, return immediately. Task succeeds when launch is confirmed. | `succeeded` on launch |
| `launch_wait_exit` | Launch GUI process, block until it exits. Task exit code = process exit code. | `succeeded` if exit 0, `failed` otherwise |

### How modes are specified

The `executionMode` parameter is passed via the task definition step `map`:

```json
{
  "map": {
    "app": "notepad",
    "executionMode": "launch_return"
  }
}
```

Default (if omitted): `launch_return`.

### Implementation

`actions/open-app.ps1` accepts optional `-ExecutionMode` parameter:
- `launch_return`: `Start-Process -FilePath $target | Out-Null` then `exit 0`
- `launch_wait_exit`: `Start-Process -FilePath $target -PassThru` then `$proc.WaitForExit()` then `exit $proc.ExitCode`

Output includes mode label:
- `launch_return`: `OK:notepad MODE:launch_return`
- `launch_wait_exit`: `LAUNCHED:notepad PID:1234 MODE:launch_wait_exit` then `EXITED:notepad PID:1234 EXIT_CODE:0`

### Manifest update

`open_app` action now has optional `executionMode` parameter in manifest:
```json
{
  "name": "executionMode",
  "type": "string",
  "required": false,
  "description": "launch_return (default): succeed on launch. launch_wait_exit: wait for process exit."
}
```

### Task definitions updated

`open_notepad.json`:
```json
"map": { "app": "notepad", "executionMode": "launch_return" }
```

### Bug fix: runner null artifact crash

During testing, a pre-existing bug was discovered: `oc-task-runner.ps1` crashed on tasks without `artifacts` in step definition. `@((Get-OcPropertyValue ... 'artifacts'))` wraps null into `[null]` array, causing `Resolve-OcTemplateValue -Value $null` to fail.

Fix: null-safe artifact resolution in runner (line 189-193).

### Files changed

| File | Change |
|------|--------|
| `actions/open-app.ps1` | Added `-ExecutionMode` parameter with `launch_return`/`launch_wait_exit` support |
| `actions/manifest.json` | Added `executionMode` optional parameter to `open_app` action |
| `defs/tasks/open_notepad.json` | Explicit `executionMode: launch_return` in map |
| `bin/oc-task-runner.ps1` | Null-safe artifact template resolution |
| `oc-task-runtime-bootstrap-v3.4.ps1` | All above changes in heredocs + `open-app.ps1` heredoc added |

---

## Smoke tests and observed outputs

### Test 1: Bootstrap — naming migration

```
powershell.exe -ExecutionPolicy Bypass -File .\oc-task-runtime-bootstrap-v3.4.ps1
```

Output (relevant lines):
```
Files updated  : 2
Updated files:
  bin/oc-task-common.ps1 -> ...bak-20260322-082443
  actions/open-app.ps1 -> ...bak-20260322-082443
Scheduled task : Legacy task OpenClawTaskWorkerV2 removed. Logon scheduled task created: OpenClawTaskWorker.
```

### Test 2: Bootstrap idempotency after migration

```
powershell.exe -ExecutionPolicy Bypass -File .\oc-task-runtime-bootstrap-v3.4.ps1
```

Output:
```
Files unchanged: 30
Files updated  : 0
Scheduled task : Logon scheduled task already registered and unchanged: OpenClawTaskWorker.
```

### Test 3: No legacy V2 naming in runtime

```
powershell.exe -Command "Get-ScheduledTask -TaskName 'OpenClawTaskWorkerV2'"
```
Result: exit code 1 (not found)

```
grep -r 'WorkerV2\|TaskWorkerV2' C:\Users\AKCA\oc\bin\*.ps1
```
Result: no matches

### Test 4: Healthcheck — aligned naming

```
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-health.ps1
```

Output: `"scheduledTaskState": "Ready"` (queries `OpenClawTaskWorker`)

### Test 5: open_notepad in launch_return mode

```
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-enqueue.ps1 -TaskName open_notepad -NoWorkerKick
pwsh.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-worker.ps1 -RunOnce
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-get.ps1 -TaskId task-20260322-083842647-6598
```

Result:
```json
{
  "status": "succeeded",
  "steps": [{
    "action": "open_app",
    "status": "succeeded",
    "exitCode": 0,
    "outputPreview": "...OK:notepad MODE:launch_return Status Code: 0"
  }]
}
```

Notepad GUI launched. Task succeeded immediately. Mode visible in output.

### Test 6: create_note regression test

```
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-enqueue.ps1 -TaskName create_note -InputBase64 ... -NoWorkerKick
pwsh.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-worker.ps1 -RunOnce
```

Result: `task-20260322-083548991-8229` succeeded. Runner artifact null fix confirmed safe for existing tasks.

---

## Known limitations

| Limitation | Description |
|------------|-------------|
| `launch_wait_exit` not smoke-tested end-to-end | The mode is implemented and reachable but was not tested as a task because it requires manual GUI interaction (close notepad) which cannot be automated in this context. |
| `notepad_test` action not updated | `actions/notepad-test.ps1` remains fire-and-forget without `executionMode` parameter. It is a standalone smoke action, not a parameterized action like `open_app`. |
| Legacy migration is one-time | After first v3.4 bootstrap run, the legacy removal code is inert (no V2 task exists). The code remains for safety in case bootstrap is run on a fresh machine that somehow has the old task. |
| Bootstrap `legacyTaskName` is hardcoded | `OpenClawTaskWorkerV2` string in bootstrap is the only remaining V2 reference. This is intentional — it must match the exact old name to remove it. |

---

## Acceptance criteria

### Part 1 — Naming drift cleanup

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | No misleading V2 naming in canonical runtime | PASS | Test 3: zero matches in bin/*.ps1 |
| 2 | Scheduled task naming aligned | PASS | Test 1: OpenClawTaskWorker created, V2 removed |
| 3 | Worker mutex naming centralized | PASS | Single definition in Get-OcRuntimeConfig |
| 4 | Health/bootstrap/log surfaces consistent | PASS | Test 2 + 4: aligned naming throughout |

### Part 2 — GUI action semantics

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 5 | GUI action semantics explicitly documented | PASS | This document, section "Execution modes" |
| 6 | open_notepad behavior unambiguous | PASS | Test 5: launch_return, succeeded immediately, mode in output |
| 7 | At least one smoke test proves semantics | PASS | Test 5: full task lifecycle |
| 8 | No misleading "task hung" behavior | PASS | launch_return mode documented and visible in output |
| 9 | Mode visible in task output | PASS | `MODE:launch_return` in outputPreview |

**Result: 9 of 9 criteria PASSED. launch_wait_exit implemented but not end-to-end tested (requires manual GUI interaction).**
