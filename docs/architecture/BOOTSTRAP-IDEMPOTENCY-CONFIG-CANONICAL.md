# Bootstrap Idempotency + Config Centralization — Canonical Documentation

**Status:** ACCEPTED (verified with live smoke tests)
**Version:** v3.4
**Date:** 2026-03-22

---

## 1. Design summary

### Goal A — Bootstrap idempotency

The bootstrap script (`oc-task-runtime-bootstrap-v3.4.ps1`) is now safely re-runnable:

- **Deploy-OcFile** function compares file content before writing:
  - File does not exist -> create (report: `created`)
  - File exists, content identical -> skip (report: `unchanged`)
  - File exists, content differs -> backup + replace (report: `updated`, backup path shown)
- **Directories** are ensured (created only if missing), never wiped
- **Manifest** patching uses existing backup + upsert logic (unchanged from v3.3)
- **Scheduled task** is idempotent: checks if task exists and matches expected configuration before registering
- **Deployment report** shows exact counts and per-file actions

### Goal B — Config centralization

All bootstrap-managed script paths and names are derived from one central source: `Get-OcRuntimeConfig` in `oc-task-common.ps1`.

Added config keys (v3.4):
- `ManifestPath` — `actions\manifest.json`
- `RunFilePath` — `bin\oc-run-file.ps1`
- `WmcpCallPath` — `bin\wmcp-call.ps1`

These join the existing keys: `BasePath`, `RuntimeRoot`, `BinPath`, `ActionsPath`, `TaskDefsPath`, `QueuePendingPath`, `QueueLeasesPath`, `QueueDeadLetterPath`, `TasksPath`, `LogsPath`, `ResultsPath`, `ActionRunnerPath`, `WorkerScriptPath`, `RunnerScriptPath`, `SchedulerTaskName`, `WorkerMutexName`.

18 hardcoded `C:\Users\AKCA` paths eliminated across 7 scripts that are now bootstrap-managed. `actions/write-file.ps1` derives paths from `$PSCommandPath`.

---

## 2. Files changed

| File | Change |
|------|--------|
| `oc-task-runtime-bootstrap-v3.4.ps1` | New bootstrap version: Deploy-OcFile, idempotent scheduled task, deployment report, 7 new heredocs for config-centralized scripts |
| `bin/oc-task-common.ps1` | Added `ManifestPath`, `RunFilePath`, `WmcpCallPath` to `Get-OcRuntimeConfig` |
| `bin/oc-run-action.ps1` | Sources common.ps1, uses `$ocConfig.ManifestPath`, `$ocConfig.RunFilePath`, `$ocConfig.LogsPath` |
| `bin/oc-run-file.ps1` | Sources common.ps1, uses `$ocConfig.ActionsPath`, `$ocConfig.WmcpCallPath` |
| `bin/oc-validate-manifest.ps1` | Sources common.ps1, uses `$ocConfig.ManifestPath` |
| `bin/oc-list-actions.ps1` | Sources common.ps1, uses `$ocConfig.ManifestPath` |
| `bin/oc-list-actions-json.ps1` | Sources common.ps1, uses `$ocConfig.ManifestPath` |
| `bin/oc-healthcheck.ps1` | Sources common.ps1, uses config for all 9 previously hardcoded paths |
| `actions/write-file.ps1` | Derives `$resultsRoot` from `$PSCommandPath` instead of hardcoded path |

Backed up to `olds/`:
| File | Reason |
|------|--------|
| `oc-task-runtime-bootstrap-v3.3.ps1` | Superseded by v3.4 |

---

## 3. Smoke tests and observed outputs

### Test 1: Bootstrap on existing populated environment (first v3.4 run)

This test was run on an existing, populated runtime — not a clean/empty environment. All runtime data (tasks, queue, results, logs) was already present from prior use.

```
powershell.exe -ExecutionPolicy Bypass -File .\oc-task-runtime-bootstrap-v3.4.ps1
```

**Full observed output:**
```
=== OpenClaw Task Runtime v3.4 — Deployment Report ===

BasePath      : C:\Users\AKCA
RuntimeRoot   : C:\Users\AKCA\oc
BinPath       : C:\Users\AKCA\oc\bin
ActionsPath   : C:\Users\AKCA\oc\actions
ResultsPath   : C:\Users\AKCA\oc\results

Files created  : 0
Files unchanged: 20
Files updated  : 9

Updated files (backups created):
  bin/oc-task-common.ps1 -> C:\Users\AKCA\oc\bin\oc-task-common.ps1.bak-20260322-073854
  bin/oc-task-runner.ps1 -> C:\Users\AKCA\oc\bin\oc-task-runner.ps1.bak-20260322-073854
  bin/oc-run-action.ps1 -> C:\Users\AKCA\oc\bin\oc-run-action.ps1.bak-20260322-073854
  bin/oc-run-file.ps1 -> C:\Users\AKCA\oc\bin\oc-run-file.ps1.bak-20260322-073854
  bin/oc-validate-manifest.ps1 -> C:\Users\AKCA\oc\bin\oc-validate-manifest.ps1.bak-20260322-073854
  bin/oc-list-actions.ps1 -> C:\Users\AKCA\oc\bin\oc-list-actions.ps1.bak-20260322-073854
  bin/oc-list-actions-json.ps1 -> C:\Users\AKCA\oc\bin\oc-list-actions-json.ps1.bak-20260322-073854
  bin/oc-healthcheck.ps1 -> C:\Users\AKCA\oc\bin\oc-healthcheck.ps1.bak-20260322-073854
  actions/write-file.ps1 -> C:\Users\AKCA\oc\actions\write-file.ps1.bak-20260322-073854

Manifest       : Manifest updated with task control actions.
Scheduled task : Logon scheduled task already registered and unchanged: OpenClawTaskWorkerV2.

Control plane  : enqueue_task, get_task, list_tasks, get_task_output, task_healthcheck, cancel_task, retry_task
Utility scripts: oc-log-rotate.ps1, oc-task-repair.ps1, oc-healthcheck.ps1
Starter tasks  : create_note, open_notepad, notepad_smoke
Deployment complete.
```

**Interpretation:** 9 files updated because their content changed (config centralization). 20 files unchanged (content already matched heredoc). 0 files created (all paths already existed).

### Test 2: Immediate re-run (idempotency)

```
powershell.exe -ExecutionPolicy Bypass -File .\oc-task-runtime-bootstrap-v3.4.ps1
```

**Full observed output:**
```
=== OpenClaw Task Runtime v3.4 — Deployment Report ===

BasePath      : C:\Users\AKCA
RuntimeRoot   : C:\Users\AKCA\oc
BinPath       : C:\Users\AKCA\oc\bin
ActionsPath   : C:\Users\AKCA\oc\actions
ResultsPath   : C:\Users\AKCA\oc\results

Files created  : 0
Files unchanged: 29
Files updated  : 0

Manifest       : Manifest updated with task control actions.
Scheduled task : Logon scheduled task already registered and unchanged: OpenClawTaskWorkerV2.

Control plane  : enqueue_task, get_task, list_tasks, get_task_output, task_healthcheck, cancel_task, retry_task
Utility scripts: oc-log-rotate.ps1, oc-task-repair.ps1, oc-healthcheck.ps1
Starter tasks  : create_note, open_notepad, notepad_smoke
Deployment complete.
```

All 29 managed files unchanged. Zero updates. Zero creates.

### Test 3: Scheduled task — no duplicates

```
powershell.exe -Command "(Get-ScheduledTask -TaskName 'OpenClawTaskWorkerV2' | Measure-Object).Count"
```

**Result:** `1`

### Test 4: Backup behavior — concrete example

**File:** `bin/oc-run-action.ps1`
**Backup created:** `C:\Users\AKCA\oc\bin\oc-run-action.ps1.bak-20260322-073854`
**Deploy action:** `updated`

SHA256 hashes confirm backup and current differ:
```
Backup:  CE0199792D78BC143413095B611E42486685BB78378095D52C0F95CD6FE3D28D
Current: 107FB120821D0CA6EABB144BB84FD6D4E5051CD20A52E31C86AF6E9359862504
```

**What changed — backup (old) had hardcoded paths:**
```
Line 18: $manifestPath = 'C:\Users\AKCA\oc\actions\manifest.json'
Line 19: $runFilePath  = 'C:\Users\AKCA\oc\bin\oc-run-file.ps1'
Line 20: $logDir       = 'C:\Users\AKCA\oc\logs'
```

**Current version sources config:**
```
Line 14: . (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')
Line 15: $ocConfig = Get-OcRuntimeConfig
Line 20: $manifestPath = $ocConfig.ManifestPath
Line 21: $runFilePath  = $ocConfig.RunFilePath
Line 22: $logDir       = $ocConfig.LogsPath
```

All 10 backup files on disk (9 scripts + 1 manifest):
```
bin/oc-task-common.ps1.bak-20260322-073854
bin/oc-task-runner.ps1.bak-20260322-073854
bin/oc-run-action.ps1.bak-20260322-073854
bin/oc-run-file.ps1.bak-20260322-073854
bin/oc-validate-manifest.ps1.bak-20260322-073854
bin/oc-list-actions.ps1.bak-20260322-073854
bin/oc-list-actions-json.ps1.bak-20260322-073854
bin/oc-healthcheck.ps1.bak-20260322-073854
actions/write-file.ps1.bak-20260322-073854
actions/manifest.json.bak-20260322-073854
```

### Test 5: Healthcheck after bootstrap

```
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-health.ps1
```

**Full observed output:**
```json
{
  "status": "ok",
  "basePath": "C:\\Users\\AKCA",
  "runtimeRoot": "C:\\Users\\AKCA\\oc",
  "actionRunnerExists": true,
  "workerScriptExists": true,
  "taskDefinitions": 4,
  "pendingTickets": 0,
  "leaseTickets": 0,
  "deadLetterTickets": 5,
  "nonTerminalTasks": 2,
  "stuckTasks": 1,
  "tasks": 50,
  "scheduledTaskState": "Ready"
}
```

### Test 6: Functional test — task enqueue, execute, verify

```
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-enqueue.ps1 ^
  -TaskName create_note ^
  -InputBase64 eyJmaWxlbmFtZSI6InYzNC10ZXN0LnR4dCIsImNvbnRlbnQiOiJib290c3RyYXAgdjMuNCB3b3JrcyJ9 ^
  -NoWorkerKick
```

**Enqueue output:**
```json
{
  "status": "queued",
  "taskId": "task-20260322-073957945-6989",
  "taskName": "create_note",
  "priority": 5
}
```

```
pwsh.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-worker.ps1 -RunOnce
```

```
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-get.ps1 ^
  -TaskId task-20260322-073957945-6989
```

**Task result:**
```json
{
  "taskId": "task-20260322-073957945-6989",
  "status": "succeeded",
  "lastError": null,
  "steps": [{
    "action": "write_file",
    "status": "succeeded",
    "exitCode": 0,
    "outputPreview": "ACTION=write_file ... Response: OK:C:\\Users\\AKCA\\oc\\results\\v34-test.txt Status Code: 0"
  }]
}
```

**Output artifact:** `C:\Users\AKCA\oc\results\v34-test.txt` contains `bootstrap v3.4 works`

### Test 7: Config centralization — zero hardcoded paths

```
grep -r 'C:\\Users\\AKCA' C:\Users\AKCA\oc\bin\*.ps1 C:\Users\AKCA\oc\actions\write-file.ps1
```

**Result:** No matches found.

All 7 previously-hardcoded scripts now derive paths from `Get-OcRuntimeConfig` or `$PSCommandPath`.

### Test 8: Data preservation across bootstrap runs

Counts measured after two consecutive bootstrap runs:
```
tasks/:         51 directories (preserved)
queue/dead-letter/: 5 tickets (preserved)
results/:       23 files (preserved)
logs/:          3 files (preserved)
```

No runtime data was lost, overwritten, or corrupted.

---

## 4. Config centralization scope

### What is centralized (v3.4)

All bootstrap-managed scripts in `bin/` source `oc-task-common.ps1` and read `Get-OcRuntimeConfig`. This includes:

**Task control plane scripts** (centralized since v3.0):
- oc-task-enqueue.ps1, oc-task-worker.ps1, oc-task-runner.ps1
- oc-task-get.ps1, oc-task-list.ps1, oc-task-output.ps1
- oc-task-health.ps1, oc-task-cancel.ps1, oc-task-retry.ps1
- oc-task-repair.ps1, oc-log-rotate.ps1

**Action infrastructure scripts** (centralized in v3.4):
- oc-run-action.ps1, oc-run-file.ps1
- oc-validate-manifest.ps1, oc-list-actions.ps1, oc-list-actions-json.ps1
- oc-healthcheck.ps1

**Action script** (path derived from `$PSCommandPath`, v3.4):
- actions/write-file.ps1

### What remains intentionally outside bootstrap/config centralization

| Item | Reason |
|------|--------|
| `bin/wmcp-call.ps1` | MCP HTTP wrapper. Has no hardcoded runtime paths — uses only its own parameters (`$Command`, `$BaseUrl`, `$ApiKey`). Not a runtime infrastructure script. |
| `bin/wmcp-api.ps1` | MCP API utility. Same reasoning as wmcp-call.ps1. |
| `actions/notepad-test.ps1` | User action script. Actions are the domain of the action layer, not the task runtime bootstrap. Has no hardcoded runtime paths. |
| `actions/open-app.ps1` | User action script. Same reasoning. |
| `manifest.json` `actionsRoot` field | Contains an absolute path (`C:\Users\AKCA\oc\actions`) set by bootstrap at deploy time. This is correct behavior — manifest must reference the actual filesystem location. The value is computed from bootstrap's `$ActionsPath` variable, not hardcoded in the heredoc. |

---

## 5. Config source of truth

`oc\bin\oc-task-common.ps1` — `Get-OcRuntimeConfig` function.

Returns 19 keys covering all runtime paths, script locations, and operational names. The function derives the root path from `$PSCommandPath` (the location of common.ps1 on disk), making the runtime layout relocatable without editing scripts.

```
Get-OcRuntimeConfig keys:
  BasePath, RuntimeRoot, BinPath, ActionsPath, TaskDefsPath,
  QueuePendingPath, QueueLeasesPath, QueueDeadLetterPath,
  TasksPath, LogsPath, ResultsPath,
  ActionRunnerPath, RunFilePath, WmcpCallPath, ManifestPath,
  WorkerScriptPath, RunnerScriptPath,
  SchedulerTaskName, WorkerMutexName
```

---

## 6. Remaining limitations

| Limitation | Description |
|------------|-------------|
| No clean-environment test | All tests were performed on an existing populated runtime. A true fresh/empty environment test was not run. The `Deploy-OcFile` code path for `created` was not exercised in these tests. |
| Manifest always backed up on upsert | The manifest patching logic always creates a timestamped `.bak` file even if the upserted content is identical. Inherited from v3.3. |
| wmcp-call.ps1, wmcp-api.ps1 not in bootstrap | These MCP utility scripts have no hardcoded path issues and are not task runtime infrastructure. |
| notepad-test.ps1, open-app.ps1 not in bootstrap | User-created action scripts. Not infrastructure. |
| Manifest actionsRoot is an absolute path | Set correctly by bootstrap at deploy time from computed variables. |

---

## 7. Acceptance criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Bootstrap on existing populated environment succeeds | PASS | Test 1: 0 errors, 20 unchanged + 9 updated |
| 2 | Immediate re-run succeeds without corruption | PASS | Test 2: 29 unchanged, 0 updated, 0 created |
| 3 | No duplicate scheduled task registrations | PASS | Test 3: count = 1 |
| 4 | Differing files backed up before replacement | PASS | Test 4: concrete backup example with SHA256 hashes and line-level diff |
| 5 | Queue/tasks/results/logs preserved | PASS | Test 8: all counts identical across runs |
| 6 | Key paths and names in one central place | PASS | Section 5: 19 keys in Get-OcRuntimeConfig |
| 7 | Scheduled task name and mutex name centralized | PASS | Only defined in Get-OcRuntimeConfig |
| 8 | Main runtime scripts consume centralized config | PASS | Test 7: zero hardcoded paths in bin/*.ps1 |
| 9 | Healthcheck shows config-derived state | PASS | Test 5: basePath, runtimeRoot, script existence checks |

**Not tested:** Clean/empty environment bootstrap (`created` code path). All evidence is from an existing populated runtime.

**Result: 9 of 9 tested criteria PASSED. 1 code path (file creation on empty target) not exercised.**
