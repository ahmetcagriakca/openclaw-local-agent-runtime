# Task F1.1 — True AtStartup Preflight: Implementation Report

## Tasarim Ozeti

oc runtime icin makine boot aninda (`AtStartup`) tetiklenen, tamamen non-interactive bir preflight katmani eklendi.

**Temel tasarim kararlari:**

- Mevcut `oc-runtime-supervisor.ps1` AtLogon + 15dk tekrar ile calisiyor ve worker kick yapiyor. Preflight ise **sadece boot** aninda calisiyor, **kesinlikle worker baslatmiyor** ve **GUI acmiyor**.
- Preflight 10 ayri kontrol yapiyor: layout, script, manifest, task definition, scheduled task, stale lease recovery, stuck task detection, log rotation, worker status (observe-only).
- Tum log ciktilari `[preflight]` tag'i ile `control-plane.log` dosyasina yaziliyor.
- Script idempotent: kac kez calisirsa calissin guvenli. Queue history, task history, log veya result silmiyor.
- Config'e `PreflightScriptPath` ve `PreflightTaskName` eklendi, boylece tum runtime bilesenlerinden merkezi olarak erisilebilir.

**Preflight ile Supervisor farki:**

| Ozellik | Preflight (AtStartup) | Supervisor (AtLogon + 15dk) |
|---|---|---|
| Trigger | MSFT_TaskBootTrigger (boot) | AtLogon + RepetitionInterval |
| Worker kick | Hayir (observe-only) | Evet |
| GUI | Yok | Yok |
| Stale lease recovery | Evet | Evet |
| Task definition validation | Evet | Hayir |
| Log tag | `[preflight]` | `[supervisor]` |

---

## Degisen Dosyalar

| Dosya | Degisiklik | Satir |
|---|---|---|
| `bin/oc-runtime-startup-preflight.ps1` | **YENi DOSYA** — Startup preflight script | 243 satir |
| `bin/oc-task-common.ps1` | **GUNCELLEME** — Config'e `PreflightScriptPath` ve `PreflightTaskName` eklendi | 2 satir eklendi |
| Windows Task Scheduler | **YENi KAYIT** — `OpenClawStartupPreflight` scheduled task (AtStartup) | — |

---

## Tam Patch

### Dosya 1: `bin/oc-runtime-startup-preflight.ps1` (YENi — 243 satir)

```powershell
# oc-runtime-startup-preflight.ps1
# True AtStartup preflight for oc runtime.
# Non-interactive. No GUI. No worker launch. Safe to run multiple times.
# Performs: layout validation, script validation, manifest validation,
#           scheduled task validation, stale lease recovery, stuck task
#           detection, log rotation, health/status logging.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout

function Write-PreflightLog {
    param(
        [Parameter(Mandatory = $true)][string]$Level,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-OcRuntimeLog -LogName 'control-plane.log' -Level $Level -Message ('[preflight] ' + $Message)
}

Write-PreflightLog -Level 'info' -Message 'Startup preflight started.'

$checks = New-Object System.Collections.ArrayList
$repairs = New-Object System.Collections.ArrayList
$overallStatus = 'ok'

function Set-Degraded { param([string]$Reason) if ($script:overallStatus -ne 'error') { $script:overallStatus = 'degraded' }; [void]$script:checks.Add($Reason) }
function Set-Error { param([string]$Reason) $script:overallStatus = 'error'; [void]$script:checks.Add($Reason) }
function Set-Ok { param([string]$Reason) [void]$script:checks.Add($Reason) }

# -- 1. Runtime layout validation -----------------------------------------------
$requiredDirs = @(
    $config.RuntimeRoot, $config.BinPath, $config.ActionsPath, $config.ResultsPath,
    $config.TaskDefsPath, $config.QueuePendingPath, $config.QueueLeasesPath,
    $config.QueueDeadLetterPath, $config.TasksPath, $config.LogsPath
)
$missingDirs = @($requiredDirs | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missingDirs.Count -eq 0) {
    Set-Ok -Reason 'layout: all directories present'
}
else {
    foreach ($d in $missingDirs) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
        [void]$repairs.Add('created missing directory: ' + $d)
    }
    Set-Degraded -Reason ('layout: ' + $missingDirs.Count + ' directories were missing and created')
    Write-PreflightLog -Level 'warn' -Message ($missingDirs.Count.ToString() + ' missing directories created.')
}

# -- 2. Required script validation ----------------------------------------------
$requiredScripts = @(
    $config.WorkerScriptPath,
    $config.RunnerScriptPath,
    $config.ActionRunnerPath,
    $config.SupervisorScriptPath
)
$missingScripts = @($requiredScripts | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missingScripts.Count -eq 0) {
    Set-Ok -Reason 'scripts: all required scripts present'
}
else {
    Set-Error -Reason ('scripts missing: ' + ($missingScripts -join ', '))
    Write-PreflightLog -Level 'error' -Message ('Missing scripts: ' + ($missingScripts -join ', '))
}

# -- 3. Manifest validation -----------------------------------------------------
if (Test-Path -LiteralPath $config.ManifestPath) {
    try {
        $manifest = Get-Content -Raw -LiteralPath $config.ManifestPath | ConvertFrom-Json
        $actionCount = 0
        if ($null -ne $manifest.actions) { $actionCount = @($manifest.actions).Count }
        Set-Ok -Reason ('manifest: parseable, ' + $actionCount + ' actions')
    }
    catch {
        Set-Error -Reason 'manifest: exists but not parseable'
        Write-PreflightLog -Level 'error' -Message ('Manifest parse error: ' + $_.Exception.Message)
    }
}
else {
    Set-Error -Reason 'manifest: not found'
    Write-PreflightLog -Level 'error' -Message 'Manifest file not found.'
}

# -- 4. Task definition validation ----------------------------------------------
$defFiles = @()
if (Test-Path -LiteralPath $config.TaskDefsPath) {
    $defFiles = @(Get-ChildItem -LiteralPath $config.TaskDefsPath -Filter '*.json' -File -ErrorAction SilentlyContinue)
}
$badDefs = 0
foreach ($df in $defFiles) {
    try {
        $null = Get-Content -Raw -LiteralPath $df.FullName | ConvertFrom-Json
    }
    catch {
        $badDefs++
        Write-PreflightLog -Level 'warn' -Message ('Unparseable task definition: ' + $df.Name)
    }
}
if ($badDefs -eq 0) {
    Set-Ok -Reason ('task definitions: ' + $defFiles.Count + ' valid')
}
else {
    Set-Degraded -Reason ('task definitions: ' + $badDefs + ' unparseable out of ' + $defFiles.Count)
}

# -- 5. Scheduled task validation -----------------------------------------------
$taskChecks = @(
    @{ Name = $config.SchedulerTaskName; Label = 'worker' },
    @{ Name = $config.SupervisorTaskName; Label = 'supervisor' },
    @{ Name = $config.PreflightTaskName; Label = 'preflight' }
)
foreach ($tc in $taskChecks) {
    try {
        $st = Get-ScheduledTask -TaskName $tc.Name -ErrorAction Stop
        if ($null -ne $st -and [string]$st.State -ne 'Disabled') {
            Set-Ok -Reason ($tc.Label + ' scheduled task: ' + $tc.Name + ' (' + $st.State + ')')
        }
        else {
            Set-Degraded -Reason ($tc.Label + ' scheduled task: ' + $tc.Name + ' is Disabled')
            Write-PreflightLog -Level 'warn' -Message ($tc.Label + ' scheduled task is Disabled: ' + $tc.Name)
        }
    }
    catch {
        Set-Degraded -Reason ($tc.Label + ' scheduled task: ' + $tc.Name + ' not registered')
        Write-PreflightLog -Level 'warn' -Message ($tc.Label + ' scheduled task not found: ' + $tc.Name)
    }
}

# -- 6. Stale lease recovery ----------------------------------------------------
$leaseFiles = @()
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $leaseFiles = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File)
}
$recoveredLeases = 0
foreach ($lf in $leaseFiles) {
    $leaseAge = 31
    try {
        $ticket = Get-Content -Raw -LiteralPath $lf.FullName | ConvertFrom-Json
        $leasedAt = $ticket.leasedAtUtc
        if (-not [string]::IsNullOrWhiteSpace([string]$leasedAt)) {
            $leaseAge = ([DateTime]::UtcNow - [DateTime]::Parse($leasedAt)).TotalMinutes
        }
        else {
            $leaseAge = ([DateTime]::UtcNow - $lf.LastWriteTimeUtc).TotalMinutes
        }
    }
    catch {
        $leaseAge = ([DateTime]::UtcNow - $lf.LastWriteTimeUtc).TotalMinutes
    }

    if ($leaseAge -ge 30) {
        $target = Join-Path $config.QueuePendingPath $lf.Name
        Move-Item -LiteralPath $lf.FullName -Destination $target -Force
        $recoveredLeases++
        Write-PreflightLog -Level 'warn' -Message ('Recovered stale lease: ' + $lf.Name + ' (age: ' + [math]::Round($leaseAge, 1) + ' min)')
    }
}
if ($recoveredLeases -gt 0) {
    [void]$repairs.Add('recovered ' + $recoveredLeases + ' stale leases')
    Set-Degraded -Reason ('stale leases recovered: ' + $recoveredLeases)
}
else {
    Set-Ok -Reason 'leases: no stale leases'
}

# -- 7. Stuck task detection ----------------------------------------------------
$stuckCount = 0
$stuckThreshold = 60
if (Test-Path -LiteralPath $config.TasksPath) {
    $taskDirs = @(Get-ChildItem -LiteralPath $config.TasksPath -Directory)
    foreach ($td in $taskDirs) {
        $tjp = Join-Path $td.FullName 'task.json'
        if (-not (Test-Path -LiteralPath $tjp)) { continue }
        try {
            $tj = Get-Content -Raw -LiteralPath $tjp | ConvertFrom-Json
            $tst = [string]$tj.status
            if ($tst -eq 'running' -or $tst -eq 'queued' -or $tst -eq 'cancel_requested') {
                $ref = $tj.startedUtc
                if ([string]::IsNullOrWhiteSpace([string]$ref)) { $ref = $tj.createdUtc }
                if (-not [string]::IsNullOrWhiteSpace([string]$ref)) {
                    if (([DateTime]::UtcNow - [DateTime]::Parse($ref)).TotalMinutes -ge $stuckThreshold) {
                        $stuckCount++
                        Write-PreflightLog -Level 'warn' -Message ('Stuck task: ' + $td.Name + ' (status: ' + $tst + ')')
                    }
                }
            }
        }
        catch { }
    }
}
if ($stuckCount -gt 0) {
    Set-Degraded -Reason ('stuck tasks: ' + $stuckCount + ' (threshold: ' + $stuckThreshold + ' min)')
    Write-PreflightLog -Level 'warn' -Message ($stuckCount.ToString() + ' stuck tasks detected.')
}
else {
    Set-Ok -Reason 'tasks: no stuck tasks'
}

# -- 8. Log rotation ------------------------------------------------------------
$logTargets = @(
    (Join-Path $config.LogsPath 'control-plane.log'),
    (Join-Path $config.LogsPath 'worker.log'),
    (Join-Path $config.LogsPath 'action-execution.log')
)
foreach ($logTarget in $logTargets) {
    Invoke-OcLogRotate -LogPath $logTarget -MaxSizeBytes 5242880 -KeepCount 3
}

# -- 9. Worker status (observe only, no kick) -----------------------------------
$workerActive = Test-OcWorkerActive -MutexName $config.WorkerMutexName
$pendingCount = 0
if (Test-Path -LiteralPath $config.QueuePendingPath) {
    $pendingCount = @(Get-ChildItem -LiteralPath $config.QueuePendingPath -Filter '*.json' -File).Count
}
if ($workerActive) {
    Set-Ok -Reason 'worker: active'
}
elseif ($pendingCount -gt 0) {
    Set-Degraded -Reason ('worker: not active with ' + $pendingCount + ' pending tickets (no kick at startup)')
    Write-PreflightLog -Level 'warn' -Message ('Worker not active with ' + $pendingCount + ' pending tickets. Not kicking at startup -- deferred to logon/supervisor.')
}
else {
    Set-Ok -Reason 'worker: not active (no pending tickets)'
}

# -- Summary --------------------------------------------------------------------
$summary = [ordered]@{
    phase       = 'startup-preflight'
    status      = $overallStatus
    timestamp   = [DateTime]::UtcNow.ToString('o')
    checks      = @($checks)
    repairs     = @($repairs)
    workerActive    = $workerActive
    pendingTickets  = $pendingCount
    stuckTasks      = $stuckCount
    recoveredLeases = $recoveredLeases
}

Write-PreflightLog -Level 'info' -Message ('Startup preflight finished. Status: ' + $overallStatus + '. Checks: ' + $checks.Count + '. Repairs: ' + $repairs.Count + '.')

$summary | ConvertTo-Json -Depth 10
exit 0
```

### Dosya 2: `bin/oc-task-common.ps1` (PATCH — 2 satir eklendi)

```diff
--- a/bin/oc-task-common.ps1
+++ b/bin/oc-task-common.ps1
@@ -28,8 +28,10 @@
         WorkerScriptPath = Join-Path $script:OcBinPath 'oc-task-worker.ps1'
         RunnerScriptPath = Join-Path $script:OcBinPath 'oc-task-runner.ps1'
         SupervisorScriptPath = Join-Path $script:OcBinPath 'oc-runtime-supervisor.ps1'
+        PreflightScriptPath = Join-Path $script:OcBinPath 'oc-runtime-startup-preflight.ps1'
         SchedulerTaskName = 'OpenClawTaskWorker'
         SupervisorTaskName = 'OpenClawRuntimeSupervisor'
+        PreflightTaskName = 'OpenClawStartupPreflight'
         WorkerMutexName = 'Global\OpenClawTaskWorker'
     }
 }
```

### Scheduled Task Registration (elle veya bootstrap'a eklenebilir)

```powershell
$PreflightPath = Join-Path $env:USERPROFILE "oc\bin\oc-runtime-startup-preflight.ps1"
$TaskName = "OpenClawStartupPreflight"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $PreflightPath + '"')
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType S4U -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null
```

---

## Smoke Test Komutlari

### Test 1: Dogrudan calistirma

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\oc\bin\oc-runtime-startup-preflight.ps1"
```

### Test 2: Scheduled task durumu

```powershell
Get-ScheduledTask -TaskName "OpenClawStartupPreflight" | Format-List TaskName, State
Get-ScheduledTaskInfo -TaskName "OpenClawStartupPreflight" | Format-List LastRunTime, NextRunTime
```

### Test 3: Trigger tipini dogrulama

```powershell
(Get-ScheduledTask -TaskName "OpenClawStartupPreflight").Triggers[0].CimClass.CimClassName
# Beklenen: MSFT_TaskBootTrigger
```

### Test 4: Log ciktisini kontrol

```powershell
Get-Content -LiteralPath "$env:USERPROFILE\oc\logs\control-plane.log" -Tail 10 | Where-Object { $_ -match '\[preflight\]' }
```

### Test 5: Idempotency — art arda 2 calistirma

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\oc\bin\oc-runtime-startup-preflight.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\oc\bin\oc-runtime-startup-preflight.ps1"
# Her iki calistirma da ayni sonucu donmeli, repair tekrari olmamali
```

---

## Observed Output

### Test 1 ciktisi: Dogrudan calistirma

```json
{
    "phase":  "startup-preflight",
    "status":  "degraded",
    "timestamp":  "2026-03-22T16:04:35.7278802Z",
    "checks":  [
                   "layout: all directories present",
                   "scripts: all required scripts present",
                   "manifest: parseable, 13 actions",
                   "task definitions: 4 valid",
                   "worker scheduled task: OpenClawTaskWorker (Ready)",
                   "supervisor scheduled task: OpenClawRuntimeSupervisor (Ready)",
                   "preflight scheduled task: OpenClawStartupPreflight (Ready)",
                   "leases: no stale leases",
                   "stuck tasks: 1 (threshold: 60 min)",
                   "worker: not active (no pending tickets)"
               ],
    "repairs":  [],
    "workerActive":  false,
    "pendingTickets":  0,
    "stuckTasks":  1,
    "recoveredLeases":  0
}
```

> **Not:** `status: degraded` cunku sistemde onceden kalmis 1 stuck task var (`task-20260322-082753368-4778`, status: running, >60 dk). Bu preflight'in olusturdugu bir sorun degil, mevcut durumu dogru raporluyor.

### Test 2 ciktisi: Scheduled task durumu

```
TaskName : OpenClawStartupPreflight
State    : Ready
```

### Test 3 ciktisi: Trigger tipi

```
MSFT_TaskBootTrigger
```

### Test 4 ciktisi: Log kayitlari

```json
{"ts":"2026-03-22T16:04:32.0658870Z","level":"info","message":"[preflight] Startup preflight started."}
{"ts":"2026-03-22T16:04:35.6809188Z","level":"warn","message":"[preflight] Stuck task: task-20260322-082753368-4778 (status: running)"}
{"ts":"2026-03-22T16:04:35.6948789Z","level":"warn","message":"[preflight] 1 stuck tasks detected."}
{"ts":"2026-03-22T16:04:35.7329150Z","level":"info","message":"[preflight] Startup preflight finished. Status: degraded. Checks: 10. Repairs: 0."}
```

---

## Remaining Limitations

| # | Limitation | Aciklama | Onerilen Cozum |
|---|---|---|---|
| 1 | **Reboot dogrulamasi yapilmadi** | Scheduled task kayitli ve `MSFT_TaskBootTrigger` dogrulandi ancak gercek bir reboot testi yapilmadi. | Bir sonraki bakim penceresinde manuel reboot ile dogrulama. |
| 2 | **Stuck task sadece raporlaniyor** | Preflight stuck tasklari tespit edip logluyor ancak force-terminate veya dead-letter yapmiyor. | Ayri bir stuck-task-policy karari gerekiyor (F1.x). |
| 3 | **Worker kick yok (tasarim geregi)** | Preflight boot aninda worker baslatmiyor. Pending ticket varsa sadece logluyor. | Worker baslatma AtLogon task'ina ve supervisor'a birakildi. |
| 4 | **Bootstrap'a entegre edilmedi** | Scheduled task elle kaydedildi; `oc-task-runtime-bootstrap-v3.4.ps1` henuz preflight kaydi icermiyor. | Sonraki bootstrap versiyonunda (v3.5) eklenmeli. |
| 5 | **Manifest deep validation yok** | Manifest parseable mi diye bakiyor ama action scriptlerinin var olup olmadigini kontrol etmiyor (bunu `oc-validate-manifest.ps1` yapiyor). | Gerekirse preflight icinden `oc-validate-manifest.ps1` cagirilabilir, ancak bu startup suresini uzatir. |
| 6 | **Tek log dosyasi** | Tum preflight loglari `control-plane.log` icinde `[preflight]` tag'i ile. Ayri bir `preflight.log` yok. | Mevcut yaklasim supervisor ile tutarli. Ayri log istenirse eklenebilir. |
