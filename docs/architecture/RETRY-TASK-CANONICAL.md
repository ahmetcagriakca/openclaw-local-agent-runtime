# retry_task — Canonical Runtime Documentation

**Status:** ACCEPTED (verified with live smoke tests)
**Version:** v3.3
**Date:** 2026-03-22

---

## 1. Overview

`retry_task` creates a NEW task linked to a failed (or cancelled) original. The original task is never mutated — only its event journal receives an append. The retry chain depth is tracked and limited to prevent infinite loops.

```
retry_task(taskId)
  -> validate status (must be failed or cancelled)
  -> check retry chain depth (max 3 by default)
  -> read original input snapshot
  -> read CURRENT task definition from defs/tasks/{taskName}.json
  -> create new task with retriedFromTaskId link
  -> enqueue new task
  -> append task_retried event to original
  -> kick worker
```

---

## 2. Retry semantics

### Definition resolution

**Retry uses the CURRENT task definition, not a historical snapshot.**

- `oc-task-retry.ps1` line 67: `$defPath = Join-Path $config.TaskDefsPath ($taskName + '.json')`
- Steps are rebuilt fresh from the current definition at retry time.
- The original task's embedded step snapshot is NOT copied to the new task.

**Implication:** If a task definition is updated between failure and retry, the retry task will execute with the updated definition.

### Input preservation

- The original task's `input` object is copied verbatim to the new task.
- No input transformation or modification occurs during retry.

### What retry does NOT do

- Does not replay the original task's historical step snapshot.
- Does not modify the original task's status, timestamps, or step data.
- Does not remove or move the dead-letter ticket of the original task.
- Does not copy artifacts from the original task.

---

## 3. Linkage fields and events

### Fields on new task (task.json)

| Field | Type | Description |
|-------|------|-------------|
| `retriedFromTaskId` | string | TaskId of the original failed task |
| `retriedAtUtc` | string (ISO 8601) | UTC timestamp of retry creation |
| `retryChainDepth` | int | Ancestry depth (0 = original, 1 = first retry, etc.) |

### Events

| Event | Where | Data |
|-------|-------|------|
| `task_created_by_retry` | New task's events.jsonl | `retriedFromTaskId`, `retryChainDepth`, `taskName`, `priority` |
| `task_retried` | Original task's events.jsonl | `newTaskId`, `retryChainDepth` |

---

## 4. Status validation

| Original status | Retry allowed? |
|-----------------|---------------|
| `failed` | Yes |
| `cancelled` | Only with `-AllowCancelled` flag |
| `succeeded` | No — "Cannot retry a succeeded task." |
| `running` | No — "Cannot retry a running task." |
| `queued` | No — "Cannot retry a queued task." |
| `cancel_requested` | No — "Cannot retry a task with pending cancellation." |

---

## 5. Chain depth limiting

- Default max: 3 (configurable via `-MaxRetries` parameter)
- Depth is calculated by walking the `retriedFromTaskId` chain backward to the root task.
- Depth reflects **ancestry**, not sibling count. All retries from the same source have the same depth.

---

## 6. Verified behaviors (smoke tested)

### R1: failed -> retry -> success (from Task 2 acceptance)

- Original task failed with known error.
- Retry created new task, worker executed it, status: `succeeded`.
- `retriedFromTaskId` linkage confirmed.

### R2: dead-letter -> retry -> success

**Source:** `task-20260322-062707606-6762` (failed, dead-lettered)
**Retry:** `task-20260322-062746023-3576` (succeeded)

- Task definition `dead_letter_probe` initially referenced `nonexistent_action_for_dl_test`.
- Task was enqueued, worker ran it, action not found → status `failed`, exit code 1.
- Ticket moved to `queue/dead-letter/p05-task-20260322-062707606-6762.json`.
- Task definition fixed to reference `write_file`.
- Retry created new task, worker executed it, `dl-probe.txt` written, status `succeeded`.
- Bidirectional linkage: original has `task_retried` event, new has `task_created_by_retry` event.

### R3: running -> retry rejected

- Confirmed via Task 2 smoke test: retry of a running task throws "Cannot retry a running task."

### R4: succeeded -> retry rejected

- Confirmed via Task 2 smoke test: retry of a succeeded task throws "Cannot retry a succeeded task."

### R5: repeated retries from same failed source — no corruption

**Source:** `task-20260322-062707606-6762` (failed)
**Retry-A:** `task-20260322-065922004-4168` (succeeded)
**Retry-B:** `task-20260322-065926712-9940` (succeeded)
**(Prior R2 retry):** `task-20260322-062746023-3576` (succeeded)

- Three retries from the same source, all succeeded.
- Original task.json unchanged: status `failed`, lastError, steps, timestamps all identical to pre-retry state.
- Only mutation on original: three `task_retried` events appended to events.jsonl.
- Both Retry-A and Retry-B have `retriedFromTaskId` pointing to the same source.
- Both have `retryChainDepth: 1` (ancestry depth, not sibling count).
- No orphan tickets in pending or leases after worker completion.
- Event journals coherent: no duplicates, no corruption.

---

## 7. Known non-blocking limitations

| Limitation | Description |
|------------|-------------|
| retryChainDepth counts ancestry, not fan-out | All sibling retries from the same source share the same depth value. Depth only increases when retrying a task that was itself a retry. |
| Unlimited sibling retries | There is no limit on how many times the same failed source can be retried. Each retry creates a new independent task. Future policy may add a sibling limit. |
| Dead-letter ticket not cleaned on retry | The original task's dead-letter ticket remains in `queue/dead-letter/` after retry. Manual cleanup or TTL-based purge is not yet implemented. |
| No automatic retry | Failed tasks are never automatically retried. Retry must be explicitly invoked via `oc-task-retry.ps1` or the `retry_task` action. |

---

## 8. Files

| File | Role |
|------|------|
| `bin/oc-task-retry.ps1` | Core retry logic |
| `actions/retry-task.ps1` | Action wrapper (called by oc-run-action) |
| `actions/manifest.json` | `retry_task` action entry (risk: medium) |

---

## 9. Commands

```
# Retry a failed task
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-retry.ps1 -TaskId <TASK_ID>

# Retry with no worker kick
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-retry.ps1 -TaskId <TASK_ID> -NoWorkerKick

# Retry a cancelled task
powershell.exe -ExecutionPolicy Bypass -File C:\Users\AKCA\oc\bin\oc-task-retry.ps1 -TaskId <TASK_ID> -AllowCancelled

# WSL wrapper
/home/akca/bin/oc-retry-task <TASK_ID>
```

---

## 10. Superseded documents

The following documents contained partial or stale retry information and have been archived to `olds/`:

| Document | Reason |
|----------|--------|
| `TASK2-GPT-RESPONSE.md` | Initial implementation report, superseded by this canonical doc |
| `TASK-R2-dead-letter-retry-report.md` | Smoke test evidence, consolidated here |
| `TASK-R3-repeated-retry-safety-report.md` | Smoke test evidence, consolidated here |
