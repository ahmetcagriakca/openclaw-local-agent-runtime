# Task F1.3-cleanup — Rejection Exit-Code Consistency + Missing Reason-Code Evidence: Report

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-task-cancel.ps1` | Terminal state rejection: `exit 0` -> `exit 1`, `[rejection]` log eklendi |
| `docs/ARCHITECTURE.md` | Section 9: exit code invariant tablosu, evidenced reason codes tablosu eklendi |

---

## Tam Patch

### oc-task-cancel.ps1 — exit code fix

```diff
     $result | ConvertTo-Json -Depth 10
-    exit 0
+    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('[rejection] TASK_STATE_INVALID: Task ' + $TaskId + ' already in terminal state: ' + $currentStatus)
+    $result | ConvertTo-Json -Depth 10
+    exit 1
 }
```

### ARCHITECTURE.md — exit code invariant + evidence tablosu

```
### Exit code invariant

- status: "rejected" => exit code 1 (always, no exceptions)
- status: "queued", "cancelled", "cancel_requested" => exit code 0
- No canonical path may return status: "rejected" with exit code 0.

### Evidenced reason codes (F1.3-cleanup)

| Code               | Evidenced | Script          | Trigger                        |
|--------------------|-----------|-----------------|--------------------------------|
| UNKNOWN_TASK       | yes       | enqueue, cancel | nonexistent task name / task ID|
| INVALID_TASK_INPUT | yes       | enqueue         | bad base64, bad JSON           |
| TASK_POLICY_DENIED | yes       | enqueue         | enqueueEnabled: false          |
| APPROVAL_REQUIRED  | yes       | enqueue         | approvalPolicy: manual         |
| TASK_STATE_INVALID | yes       | retry, cancel   | retry succeeded, cancel terminal|
| SOURCE_NOT_ALLOWED | reserved  | --              | bridge phase                   |
| RUNTIME_UNAVAILABLE| reserved  | --              | health-gate phase              |
```

---

## Smoke Test Komutlari ve Observed Output

### Test 1: TASK_STATE_INVALID (cancel terminal task)

```powershell
& "$env:USERPROFILE\oc\bin\oc-task-cancel.ps1" -TaskId "<succeeded-task-id>" -Source "evidence"
```

```json
{
    "status": "rejected",
    "reasonCode": "TASK_STATE_INVALID",
    "message": "Task already in terminal state: succeeded",
    "taskId": "task-20260322-174348901-9758",
    "taskName": "create_note",
    "taskStatus": "succeeded"
}
```
Exit: **1** (onceki: 0, simdi duzeltildi)

### Test 2: TASK_STATE_INVALID (retry succeeded task)

```powershell
& "$env:USERPROFILE\oc\bin\oc-task-retry.ps1" -TaskId "<succeeded-task-id>" -Source "evidence"
```

```json
{
    "status": "rejected",
    "reasonCode": "TASK_STATE_INVALID",
    "message": "Cannot retry a succeeded task.",
    "taskName": "create_note",
    "taskId": "task-20260322-174348901-9758",
    "source": "evidence"
}
```
Exit: **1**

### Test 3: TASK_POLICY_DENIED (enqueueEnabled: false)

```powershell
# Gecici task def: { "enqueueEnabled": false, "approvalPolicy": "preapproved", ... }
& "$env:USERPROFILE\oc\bin\oc-task-enqueue.ps1" -TaskName "policy_denied_probe" -Source "evidence"
```

```json
{
    "status": "rejected",
    "reasonCode": "TASK_POLICY_DENIED",
    "message": "Task definition is not enabled for queueing.",
    "taskName": "policy_denied_probe",
    "source": "evidence"
}
```
Exit: **1**

### Test 4: APPROVAL_REQUIRED (approvalPolicy: manual)

```powershell
# Gecici task def: { "enqueueEnabled": true, "approvalPolicy": "manual", ... }
& "$env:USERPROFILE\oc\bin\oc-task-enqueue.ps1" -TaskName "approval_required_probe" -Source "evidence"
```

```json
{
    "status": "rejected",
    "reasonCode": "APPROVAL_REQUIRED",
    "message": "Only preapproved task definitions can be enqueued by this interface.",
    "taskName": "approval_required_probe",
    "source": "evidence"
}
```
Exit: **1**

---

## Evidence Ozeti

| Reason Code | Exit Code | Kanitlandi | Test # |
|---|---|---|---|
| UNKNOWN_TASK | 1 | F1.3'te kanitlandi | (onceki rapor) |
| INVALID_TASK_INPUT | 1 | F1.3'te kanitlandi | (onceki rapor) |
| TASK_STATE_INVALID | **1** (onceki: 0, duzeltildi) | Bu rapor | Test 1, 2 |
| TASK_POLICY_DENIED | 1 | Bu rapor | Test 3 |
| APPROVAL_REQUIRED | 1 | Bu rapor | Test 4 |
| SOURCE_NOT_ALLOWED | reserved | — | — |
| RUNTIME_UNAVAILABLE | reserved | — | — |

5/7 reason code dogrudan kanitlandi. 2/7 gelecek phase icin ayrilmis (documented as reserved).

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | SOURCE_NOT_ALLOWED reserved | Bridge/Telegram allowlist Phase 1.5'te uygulanacak |
| 2 | RUNTIME_UNAVAILABLE reserved | Health-gate rejection Phase 1.5+ icin planli |
