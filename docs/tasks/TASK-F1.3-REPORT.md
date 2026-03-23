# Task F1.3 — Runtime Rejection Envelope Freeze: Consolidated Report

## Tasarim Ozeti

oc runtime'da gecersiz, izinsiz veya kullanilamaz task isteklerinin reddi yapisal JSON envelope formatinda standartlastirildi. Tum canonical task control script'leri (enqueue, retry, cancel) ve bootstrap deployment akisi guncellendi.

### Canonical Rejection Envelope

```json
{
  "status": "rejected",
  "reasonCode": "UNKNOWN_TASK",
  "message": "Task definition not found: nonexistent_xyz",
  "taskName": "nonexistent_xyz",
  "source": "smoke"
}
```

### Reason Code Tablosu

| Code | Anlam | Kullanan |
|------|-------|----------|
| UNKNOWN_TASK | Task definition veya task record bulunamadi | enqueue, retry, cancel |
| INVALID_TASK_INPUT | Format hatasi, bos isim, gecersiz JSON, eksik step | enqueue, retry, cancel |
| TASK_POLICY_DENIED | Enqueue icin aktif degil, retry limiti asildi | enqueue, retry |
| SOURCE_NOT_ALLOWED | Kaynak allowlist'te degil (bridge icin ayrilmis) | (gelecek) |
| APPROVAL_REQUIRED | Task onay gerektiriyor, henuz onaylanmamis | enqueue, retry |
| TASK_STATE_INVALID | Yanlis durum (retry succeeded, cancel terminal) | retry, cancel |
| RUNTIME_UNAVAILABLE | Runtime istek kabul edemiyor (ayrilmis) | (gelecek) |

---

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| bin/oc-task-common.ps1 | New-OcRejection ve Write-OcRejectionAndExit helper fonksiyonlari eklendi |
| bin/oc-task-enqueue.ps1 | Tum throw'lar Write-OcRejectionAndExit ile degistirildi, -Source parametresi eklendi, task record'a source alani eklendi |
| bin/oc-task-retry.ps1 | Tum throw'lar Write-OcRejectionAndExit ile degistirildi, -Source parametresi eklendi |
| bin/oc-task-cancel.ps1 | Mevcut JSON ciktilari canonical envelope'a hizalandi, -Source parametresi eklendi |
| oc-task-runtime-bootstrap-v3.4.ps1 | Common heredoc'a New-OcRejection + Write-OcRejectionAndExit eklendi. Deploy blogu: enqueue, cancel, retry, common, health, repair, worker live-file read ile override edildi — heredoc'lar artik dead code. |
| docs/ARCHITECTURE.md | Section 9: FROZEN (F1.3) etiketi, field aciklamalari, reason code tablosu, implementation detaylari |

---

## Tam Patch

### Helper fonksiyonlar (oc-task-common.ps1)

```powershell
function New-OcRejection {
    param(
        [Parameter(Mandatory = $true)][string]$ReasonCode,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$TaskName = '', [string]$Source = '', [string]$TaskId = ''
    )
    $envelope = [ordered]@{ status = 'rejected'; reasonCode = $ReasonCode; message = $Message }
    if (-not [string]::IsNullOrWhiteSpace($TaskName)) { $envelope['taskName'] = $TaskName }
    if (-not [string]::IsNullOrWhiteSpace($TaskId))   { $envelope['taskId'] = $TaskId }
    if (-not [string]::IsNullOrWhiteSpace($Source))    { $envelope['source'] = $Source }
    return $envelope
}

function Write-OcRejectionAndExit {
    param(
        [Parameter(Mandatory = $true)][string]$ReasonCode,
        [Parameter(Mandatory = $true)][string]$Message,
        [string]$TaskName = '', [string]$Source = '', [string]$TaskId = '',
        [string]$LogName = 'control-plane.log'
    )
    $envelope = New-OcRejection -ReasonCode $ReasonCode -Message $Message -TaskName $TaskName -Source $Source -TaskId $TaskId
    Write-OcRuntimeLog -LogName $LogName -Level 'warn' -Message ('[rejection] ' + $ReasonCode + ': ' + $Message)
    $envelope | ConvertTo-Json -Depth 10
    exit 1
}
```

### Enqueue — throw -> rejection ornekleri

```diff
-$defPath = Join-Path $config.TaskDefsPath ($TaskName + '.json')
-$def = Read-OcJson -Path $defPath
+if (-not (Test-Path -LiteralPath $defPath)) {
+    Write-OcRejectionAndExit -ReasonCode 'UNKNOWN_TASK' -Message ('Task definition not found: ' + $TaskName) -TaskName $TaskName -Source $Source
+}

-if ((Get-OcPropertyValue -Object $def -Name 'enqueueEnabled') -ne $true) {
-    throw 'Task definition is not enabled for queueing.'
-}
+    Write-OcRejectionAndExit -ReasonCode 'TASK_POLICY_DENIED' -Message 'Task definition is not enabled for queueing.' -TaskName $TaskName -Source $Source

-if ($approvalPolicy -ne 'preapproved') {
-    throw 'Only preapproved task definitions can be enqueued by this interface.'
-}
+    Write-OcRejectionAndExit -ReasonCode 'APPROVAL_REQUIRED' -Message 'Only preapproved task definitions can be enqueued by this interface.' -TaskName $TaskName -Source $Source
```

### Retry — status validation ornegi

```diff
-if ($originalStatus -eq 'succeeded') {
-    throw 'Cannot retry a succeeded task.'
-}
+    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message 'Cannot retry a succeeded task.' -TaskName $taskName -TaskId $TaskId -Source $Source
```

### Cancel — terminal state ornegi

```diff
-$result = [ordered]@{ status = 'no_change'; taskId = $TaskId; ... }
+$result = [ordered]@{ status = 'rejected'; reasonCode = 'TASK_STATE_INVALID'; message = 'Task already in terminal state: ' + $currentStatus; ... }
```

### Bootstrap — live-file deploy override

```powershell
# Override heredoc variables with live files for scripts that have diverged
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$commonScript     = [System.IO.File]::ReadAllText($CommonPath, $utf8NoBom)
$enqueueScript    = [System.IO.File]::ReadAllText($EnqueuePath, $utf8NoBom)
$cancelTaskScript = [System.IO.File]::ReadAllText($CancelTaskPath, $utf8NoBom)
$retryScript      = [System.IO.File]::ReadAllText($RetryPath, $utf8NoBom)
$healthScript     = [System.IO.File]::ReadAllText($HealthPath, $utf8NoBom)
$repairScript     = [System.IO.File]::ReadAllText($RepairPath, $utf8NoBom)
$workerScript     = [System.IO.File]::ReadAllText($WorkerPath, $utf8NoBom)
```

---

## Grep Evidence

### Live canonical scripts — zero throw in task control surface

```
grep -n "^\s*throw " bin/oc-task-enqueue.ps1 bin/oc-task-retry.ps1 bin/oc-task-cancel.ps1
```
Sonuc: 0 match.

### Bootstrap — rejection helpers present in common heredoc

```
grep -n "New-OcRejection\|Write-OcRejectionAndExit" oc-task-runtime-bootstrap-v3.4.ps1
```
Sonuc: helper fonksiyonlar common heredoc icinde (satir ~534-564).

### Bootstrap — live-file override at deploy time

```
grep -n "ReadAllText.*Path" oc-task-runtime-bootstrap-v3.4.ps1
```
Sonuc: 9 live-file read (common, enqueue, cancel, retry, health, repair, worker, watchdog, preflight).

---

## Smoke Test Komutlari

```powershell
# Test 1: UNKNOWN_TASK
& "$env:USERPROFILE\oc\bin\oc-task-enqueue.ps1" -TaskName "nonexistent_xyz" -Source "smoke"
# Expected: { "status": "rejected", "reasonCode": "UNKNOWN_TASK", ... }

# Test 2: INVALID_TASK_INPUT
& "$env:USERPROFILE\oc\bin\oc-task-enqueue.ps1" -TaskName "create_note" -InputBase64 "!!!" -Source "smoke"
# Expected: { "status": "rejected", "reasonCode": "INVALID_TASK_INPUT", ... }

# Test 3: UNKNOWN_TASK (cancel)
& "$env:USERPROFILE\oc\bin\oc-task-cancel.ps1" -TaskId "task-99999999-999999999-9999" -Source "smoke"
# Expected: { "status": "rejected", "reasonCode": "UNKNOWN_TASK", ... }

# Test 4: Successful enqueue still works
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"test.txt","content":"ok"}'))
& "$env:USERPROFILE\oc\bin\oc-task-enqueue.ps1" -TaskName "create_note" -InputBase64 $b64 -Source "smoke" -NoWorkerKick
# Expected: { "status": "queued", ... }

# Test 5: Rejection logs
Get-Content "$env:USERPROFILE\oc\logs\control-plane.log" -Tail 10 | Where-Object { $_ -match '\[rejection\]' }
```

---

## Observed Output

### Test 1: UNKNOWN_TASK
```json
{
    "status": "rejected",
    "reasonCode": "UNKNOWN_TASK",
    "message": "Task definition not found: nonexistent_xyz",
    "taskName": "nonexistent_xyz",
    "source": "smoke"
}
```
Exit: 1

### Test 2: INVALID_TASK_INPUT
```json
{
    "status": "rejected",
    "reasonCode": "INVALID_TASK_INPUT",
    "message": "InputBase64 is not valid base64-encoded JSON.",
    "taskName": "create_note",
    "source": "smoke"
}
```
Exit: 1

### Test 3: UNKNOWN_TASK (cancel)
```json
{
    "status": "rejected",
    "reasonCode": "UNKNOWN_TASK",
    "message": "Task was not found.",
    "taskId": "task-99999999-999999999-9999",
    "source": "smoke"
}
```
Exit: 1

### Test 4: Successful enqueue
```json
{
    "status": "queued",
    "taskId": "task-20260322-174348901-9758",
    "taskName": "create_note",
    "priority": 5
}
```
Exit: 0

### Test 5: Rejection logs
```json
{"level":"warn","message":"[rejection] UNKNOWN_TASK: Task definition not found: nonexistent_xyz"}
{"level":"warn","message":"[rejection] UNKNOWN_TASK: Task was not found."}
```

---

## Remaining Limitations

| # | Limitation | Aciklama |
|---|---|---|
| 1 | SOURCE_NOT_ALLOWED henuz kullanilmiyor | Source allowlist/policy henuz yok. Parametre kabul ediliyor ama filtreleme yapilmiyor. Phase 1.5 bridge entegrasyonunda uygulanacak. |
| 2 | RUNTIME_UNAVAILABLE henuz kullanilmiyor | Runtime health check sonucuna gore reject mekanizmasi yok. |
| 3 | oc-run-action.ps1 guncellenmedi | Internal action runner hala throw kullaniyor. Bridge'e dogrudan acik degil, sadece runner uzerinden cagriliyor. |
| 4 | oc-task-runner.ps1 guncellenmedi | Runner execution-time hatalari rejection degil, execution failure. Farkli kategori. |
| 5 | Cancel terminal state exit 0 donuyor | Terminal task cancel edildiginde TASK_STATE_INVALID envelope donuyor ama exit 0 (idempotent no-op). |
| 6 | PowerShell Mandatory binding | Bos string -TaskName "" PowerShell seviyesinde engelleniyor, rejection envelope uretilemiyor. |
| 7 | Bootstrap heredoc'lar dead code | Eski throw-based heredoc'lar bootstrap'ta duruyor ama deploy aninda live-file read ile override ediliyor. Temizlik icin silinebilir. |
