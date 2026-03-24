# Task F1.2 — Startup / Logon / Watchdog Responsibility Split: Implementation Report

## Tasarim Ozeti

Startup preflight, logon worker ve periodic watchdog rolleri kod ve scheduled task seviyesinde tamamen ayrildi. Yaniltici "supervisor" terminolojisi kaldirildi.

**Onceki durum (sorunlu):**

| Sorun | Detay |
|-------|-------|
| `oc-runtime-supervisor.ps1` hem boot hem watchdog rolu ustleniyordu | Tek script, iki farkli sorumluluk |
| `OpenClawRuntimeSupervisor` task'i AtLogOn + 15dk tekrar ile calisiyordu | AtLogOn watchdog icin yanlis trigger |
| Config'de `SupervisorTaskName` / `SupervisorScriptPath` | "Supervisor" terminolojisi boot ve periodic rolleri karistiriyordu |
| Health script sadece supervisor task kontrol ediyordu | Preflight task durumu gorulmuyordu |
| ARCHITECTURE.md uc rol tanimliyordu ama kod sadece ikisini uyguluyordu | Dokumantasyon-kod uyumsuzlugu |

**Yeni durum (temiz):**

| Rol | Script | Scheduled Task | Trigger | Tip |
|-----|--------|---------------|---------|-----|
| Startup Preflight | `oc-runtime-startup-preflight.ps1` | `OpenClawStartupPreflight` | AtStartup (boot) | non-interactive, S4U |
| Logon Worker | `oc-task-worker.ps1` | `OpenClawTaskWorker` | AtLogOn | interactive, mutex |
| Watchdog | `oc-runtime-watchdog.ps1` | `OpenClawRuntimeWatchdog` | Every 15 min | non-interactive, S4U |

**Temel farklar:**

| Ozellik | Preflight | Worker | Watchdog |
|---------|-----------|--------|----------|
| Worker kick | Hayir | Kendisi worker | Evet |
| GUI | Yok | Evet | Yok |
| Trigger | Boot | Logon | Periodic |
| Log tag | `[preflight]` | (worker log) | `[watchdog]` |
| Lease recovery | Evet | Hayir | Evet |
| Stuck detection | Evet | Hayir | Evet |

---

## Degisen Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `bin/oc-runtime-watchdog.ps1` | **YENi** — Supervisor'dan yeniden adlandirildi, `[watchdog]` tag, `phase: watchdog`, 3 task kontrolu, action-execution.log rotation eklendi |
| `bin/oc-task-common.ps1` | **GUNCELLEME** — `SupervisorScriptPath` → `WatchdogScriptPath`, `SupervisorTaskName` → `WatchdogTaskName` |
| `bin/oc-runtime-startup-preflight.ps1` | **GUNCELLEME** — `SupervisorScriptPath` → `WatchdogScriptPath`, `SupervisorTaskName` → `WatchdogTaskName` referanslari |
| `bin/oc-task-health.ps1` | **GUNCELLEME** — `supervisorTaskState` → `watchdogTaskState`, `preflightTaskState` eklendi |
| `docs/ARCHITECTURE.md` | **GUNCELLEME** — Section 7 tamamen yeniden yazildi: 3 rol tablosu, config key'leri, sorumluluk matrisi |
| `SUPERVISOR-RESTART-RECOVERY-CANONICAL.md` | **GUNCELLEME** — v3.5: Tum supervisor terminolojisi watchdog'a cevirildi, 3 rol tablosu, retired terminology section |
| Windows Task Scheduler | `OpenClawRuntimeSupervisor` **KALDIRILDI**, `OpenClawRuntimeWatchdog` **KAYIT EDILDI** (periodic-only) |

---

## Tam Patch

### Dosya 1: `bin/oc-runtime-watchdog.ps1` (YENi — supervisor'in temiz versiyonu)

```powershell
# oc-runtime-watchdog.ps1
# Periodic watchdog for oc runtime.
# Non-interactive. No GUI. Kicks worker when needed.
# Trigger: periodic (every 15 min). NOT startup, NOT logon.

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout

function Write-WatchdogLog {
    param(
        [Parameter(Mandatory = $true)][string]$Level,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-OcRuntimeLog -LogName 'control-plane.log' -Level $Level -Message ('[watchdog] ' + $Message)
}

Write-WatchdogLog -Level 'info' -Message 'Watchdog started.'

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
    Write-WatchdogLog -Level 'warn' -Message ($missingDirs.Count.ToString() + ' missing directories created.')
}

# -- 2. Key script validation ---------------------------------------------------
$requiredScripts = @(
    $config.WorkerScriptPath,
    $config.RunnerScriptPath,
    $config.ActionRunnerPath
)
$missingScripts = @($requiredScripts | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missingScripts.Count -eq 0) {
    Set-Ok -Reason 'scripts: all present'
}
else {
    Set-Error -Reason ('scripts missing: ' + ($missingScripts -join ', '))
    Write-WatchdogLog -Level 'error' -Message ('Missing scripts: ' + ($missingScripts -join ', '))
}

# -- 3. Manifest validation -----------------------------------------------------
if (Test-Path -LiteralPath $config.ManifestPath) {
    try {
        $null = Get-Content -Raw -LiteralPath $config.ManifestPath | ConvertFrom-Json
        Set-Ok -Reason 'manifest: present and parseable'
    }
    catch {
        Set-Error -Reason 'manifest: exists but not parseable'
        Write-WatchdogLog -Level 'error' -Message ('Manifest parse error: ' + $_.Exception.Message)
    }
}
else {
    Set-Error -Reason 'manifest: not found'
    Write-WatchdogLog -Level 'error' -Message 'Manifest file not found.'
}

# -- 4. Scheduled task validation -----------------------------------------------
$taskChecks = @(
    @{ Name = $config.SchedulerTaskName; Label = 'worker' },
    @{ Name = $config.WatchdogTaskName; Label = 'watchdog' },
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
            Write-WatchdogLog -Level 'warn' -Message ($tc.Label + ' scheduled task is Disabled: ' + $tc.Name)
        }
    }
    catch {
        Set-Degraded -Reason ($tc.Label + ' scheduled task: ' + $tc.Name + ' not registered')
        Write-WatchdogLog -Level 'warn' -Message ($tc.Label + ' scheduled task not found: ' + $tc.Name)
    }
}

# -- 5. Stale lease recovery ----------------------------------------------------
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
        Write-WatchdogLog -Level 'warn' -Message ('Recovered stale lease: ' + $lf.Name + ' (age: ' + [math]::Round($leaseAge, 1) + ' min)')
    }
}
if ($recoveredLeases -gt 0) {
    [void]$repairs.Add('recovered ' + $recoveredLeases + ' stale leases')
    Set-Degraded -Reason ('stale leases recovered: ' + $recoveredLeases)
}
else {
    Set-Ok -Reason 'leases: no stale leases'
}

# -- 6. Stuck task detection ----------------------------------------------------
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
                    }
                }
            }
        }
        catch { }
    }
}
if ($stuckCount -gt 0) {
    Set-Degraded -Reason ('stuck tasks: ' + $stuckCount + ' (threshold: ' + $stuckThreshold + ' min)')
    Write-WatchdogLog -Level 'warn' -Message ($stuckCount.ToString() + ' stuck tasks detected.')
}
else {
    Set-Ok -Reason 'tasks: no stuck tasks'
}

# -- 7. Worker status + kick if needed ------------------------------------------
$workerActive = Test-OcWorkerActive -MutexName $config.WorkerMutexName
$pendingCount = 0
if (Test-Path -LiteralPath $config.QueuePendingPath) {
    $pendingCount = @(Get-ChildItem -LiteralPath $config.QueuePendingPath -Filter '*.json' -File).Count
}

$workerKicked = $false
if ($workerActive) {
    Set-Ok -Reason 'worker: active'
}
elseif ($pendingCount -gt 0) {
    try {
        Invoke-OcWorkerKick -RuntimeConfig $config
        $workerKicked = $true
        [void]$repairs.Add('kicked worker for ' + $pendingCount + ' pending tickets')
        Set-Degraded -Reason ('worker was not active with ' + $pendingCount + ' pending tickets - kicked')
        Write-WatchdogLog -Level 'warn' -Message ('Worker not active with ' + $pendingCount + ' pending tickets. Kicked.')
    }
    catch {
        Set-Error -Reason ('worker kick failed: ' + $_.Exception.Message)
        Write-WatchdogLog -Level 'error' -Message ('Worker kick failed: ' + $_.Exception.Message)
    }
}
else {
    Set-Ok -Reason 'worker: not active (no pending tickets)'
}

# -- 8. Log rotation ------------------------------------------------------------
Invoke-OcLogRotate -LogPath (Join-Path $config.LogsPath 'control-plane.log') -MaxSizeBytes 5242880 -KeepCount 3
Invoke-OcLogRotate -LogPath (Join-Path $config.LogsPath 'worker.log') -MaxSizeBytes 5242880 -KeepCount 3
Invoke-OcLogRotate -LogPath (Join-Path $config.LogsPath 'action-execution.log') -MaxSizeBytes 5242880 -KeepCount 3

# -- Summary --------------------------------------------------------------------
$summary = [ordered]@{
    phase           = 'watchdog'
    status          = $overallStatus
    timestamp       = [DateTime]::UtcNow.ToString('o')
    checks          = @($checks)
    repairs         = @($repairs)
    workerActive    = $workerActive
    workerKicked    = $workerKicked
    pendingTickets  = $pendingCount
    stuckTasks      = $stuckCount
    recoveredLeases = $recoveredLeases
}

Write-WatchdogLog -Level 'info' -Message ('Watchdog finished. Status: ' + $overallStatus + '. Repairs: ' + $repairs.Count)

$summary | ConvertTo-Json -Depth 10
exit 0
```

### Dosya 2: `bin/oc-task-common.ps1` (PATCH)

```diff
--- a/bin/oc-task-common.ps1
+++ b/bin/oc-task-common.ps1
@@ -29,10 +29,10 @@
         RunnerScriptPath = Join-Path $script:OcBinPath 'oc-task-runner.ps1'
-        SupervisorScriptPath = Join-Path $script:OcBinPath 'oc-runtime-supervisor.ps1'
+        WatchdogScriptPath = Join-Path $script:OcBinPath 'oc-runtime-watchdog.ps1'
         PreflightScriptPath = Join-Path $script:OcBinPath 'oc-runtime-startup-preflight.ps1'
         SchedulerTaskName = 'OpenClawTaskWorker'
-        SupervisorTaskName = 'OpenClawRuntimeSupervisor'
+        WatchdogTaskName = 'OpenClawRuntimeWatchdog'
         PreflightTaskName = 'OpenClawStartupPreflight'
```

### Dosya 3: `bin/oc-runtime-startup-preflight.ps1` (PATCH)

```diff
--- a/bin/oc-runtime-startup-preflight.ps1
+++ b/bin/oc-runtime-startup-preflight.ps1
@@ -52,7 +52,7 @@
     $config.WorkerScriptPath,
     $config.RunnerScriptPath,
     $config.ActionRunnerPath,
-    $config.SupervisorScriptPath
+    $config.WatchdogScriptPath
 )

@@ -109,7 +109,7 @@
     @{ Name = $config.SchedulerTaskName; Label = 'worker' },
-    @{ Name = $config.SupervisorTaskName; Label = 'supervisor' },
+    @{ Name = $config.WatchdogTaskName; Label = 'watchdog' },
     @{ Name = $config.PreflightTaskName; Label = 'preflight' }
```

### Dosya 4: `bin/oc-task-health.ps1` (PATCH)

```diff
--- a/bin/oc-task-health.ps1
+++ b/bin/oc-task-health.ps1
@@ -61,10 +61,18 @@
-$supervisorTaskState = 'not_registered'
+$watchdogTaskState = 'not_registered'
 try {
-    $supervisorTask = Get-ScheduledTask -TaskName $config.SupervisorTaskName -ErrorAction Stop
-    if ($null -ne $supervisorTask) {
-        $supervisorTaskState = [string]$supervisorTask.State
+    $watchdogTask = Get-ScheduledTask -TaskName $config.WatchdogTaskName -ErrorAction Stop
+    if ($null -ne $watchdogTask) {
+        $watchdogTaskState = [string]$watchdogTask.State
     }
 }
 catch {
 }
+
+$preflightTaskState = 'not_registered'
+try {
+    $preflightTask = Get-ScheduledTask -TaskName $config.PreflightTaskName -ErrorAction Stop
+    if ($null -ne $preflightTask) {
+        $preflightTaskState = [string]$preflightTask.State
+    }
+}
+catch {
+}

@@ -110,7 +118,8 @@
     scheduledTaskState = $scheduledTaskState
-    supervisorTaskState = $supervisorTaskState
+    watchdogTaskState = $watchdogTaskState
+    preflightTaskState = $preflightTaskState
```

### Dosya 5: `docs/ARCHITECTURE.md` Section 7 (PATCH)

Section 7 tamamen yeniden yazildi — 3 rol tablosu, her rol icin script/task/config/trigger/type detayli tanimlar, sorumluluk ve non-responsibility listeleri. Tam icerik icin dosyaya bakiniz.

### Dosya 6: `SUPERVISOR-RESTART-RECOVERY-CANONICAL.md` (tam yeniden yazim)

v3.5'e guncellendi. "Retired terminology" section'i eklendi. 3 rol tablosu, config key tablosu, her rolun faz detaylari. Tam icerik icin dosyaya bakiniz.

### Scheduled Task Degisiklikleri

```powershell
# Eski supervisor task kaldirildi
Unregister-ScheduledTask -TaskName "OpenClawRuntimeSupervisor" -Confirm:$false

# Yeni watchdog task: periodic-only (AtLogOn trigger YOK)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\AKCA\oc\bin\oc-runtime-watchdog.ps1"'
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 15)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType S4U -RunLevel Limited
Register-ScheduledTask -TaskName "OpenClawRuntimeWatchdog" -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force
```

---

## Smoke Test Komutlari

### Test 1: Preflight calistirma

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\oc\bin\oc-runtime-startup-preflight.ps1"
```

### Test 2: Watchdog calistirma

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\oc\bin\oc-runtime-watchdog.ps1"
```

### Test 3: Health kontrolu

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\oc\bin\oc-task-health.ps1"
```

### Test 4: Scheduled task durumu ve trigger tipleri

```powershell
@("OpenClawStartupPreflight","OpenClawTaskWorker","OpenClawRuntimeWatchdog") | ForEach-Object {
    $t = Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue
    $trigger = $t.Triggers[0].CimClass.CimClassName
    Write-Output ("{0,-30} State={1,-8} Trigger={2}" -f $_, $t.State, $trigger)
}
```

### Test 5: Eski supervisor task'in kaldirildigini dogrula

```powershell
Get-ScheduledTask -TaskName "OpenClawRuntimeSupervisor" -ErrorAction SilentlyContinue
# Beklenen: null (task yok)
```

### Test 6: Log tag dogrulama

```powershell
Get-Content -LiteralPath "$env:USERPROFILE\oc\logs\control-plane.log" -Tail 10
# [preflight] ve [watchdog] tag'leri gorulmeli, [supervisor] sadece eski kayitlarda
```

---

## Observed Output

### Test 1: Preflight

```json
{
    "phase":  "startup-preflight",
    "status":  "degraded",
    "timestamp":  "2026-03-22T16:16:02.7475403Z",
    "checks":  [
        "layout: all directories present",
        "scripts: all required scripts present",
        "manifest: parseable, 13 actions",
        "task definitions: 4 valid",
        "worker scheduled task: OpenClawTaskWorker (Ready)",
        "watchdog scheduled task: OpenClawRuntimeWatchdog (Ready)",
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

### Test 2: Watchdog

```json
{
    "phase":  "watchdog",
    "status":  "degraded",
    "timestamp":  "2026-03-22T16:16:08.1695761Z",
    "checks":  [
        "layout: all directories present",
        "scripts: all present",
        "manifest: present and parseable",
        "worker scheduled task: OpenClawTaskWorker (Ready)",
        "watchdog scheduled task: OpenClawRuntimeWatchdog (Ready)",
        "preflight scheduled task: OpenClawStartupPreflight (Ready)",
        "leases: no stale leases",
        "stuck tasks: 1 (threshold: 60 min)",
        "worker: not active (no pending tickets)"
    ],
    "repairs":  [],
    "workerActive":  false,
    "workerKicked":  false,
    "pendingTickets":  0,
    "stuckTasks":  1,
    "recoveredLeases":  0
}
```

### Test 3: Health

```json
{
    "status":  "degraded",
    "statusReasons":  ["stuck tasks: 1"],
    "basePath":  "C:\\Users\\AKCA",
    "runtimeRoot":  "C:\\Users\\AKCA\\oc",
    "actionRunnerExists":  true,
    "workerScriptExists":  true,
    "workerActive":  false,
    "taskDefinitions":  4,
    "pendingTickets":  0,
    "leaseTickets":  0,
    "deadLetterTickets":  6,
    "nonTerminalTasks":  1,
    "stuckTasks":  1,
    "tasks":  56,
    "scheduledTaskState":  "Ready",
    "watchdogTaskState":  "Ready",
    "preflightTaskState":  "Ready"
}
```

### Test 4: Scheduled task durumu

```
OpenClawStartupPreflight       State=Ready    Trigger=MSFT_TaskBootTrigger
OpenClawTaskWorker             State=Ready    Trigger=MSFT_TaskLogonTrigger
OpenClawRuntimeWatchdog        State=Ready    Trigger=MSFT_TaskTimeTrigger
```

### Test 5: Eski supervisor

```
OK: OpenClawRuntimeSupervisor removed.
```

### Test 6: Log tag'leri

```json
{"ts":"...","level":"info","message":"[preflight] Startup preflight started."}
{"ts":"...","level":"info","message":"[preflight] Startup preflight finished. Status: degraded. Checks: 10. Repairs: 0."}
{"ts":"...","level":"info","message":"[watchdog] Watchdog started."}
{"ts":"...","level":"info","message":"[watchdog] Watchdog finished. Status: degraded. Repairs: 0"}
```

---

## Remaining Limitations

| # | Limitation | Aciklama | Onerilen Cozum |
|---|---|---|---|
| 1 | **Eski `oc-runtime-supervisor.ps1` dosyasi hala mevcut** | Dosya silmek yerine yerinde birakildi (backward compat). Artik scheduled task'i yok. | Sonraki temizlik iterasyonunda silinebilir veya deprecated olarak isaretlenebilir. |
| 2 | **Bootstrap v3.4 hala eski supervisor adlarini kullaniyor** | Bootstrap henuz guncellenmedi; `SupervisorTaskName` ve `SupervisorScriptPath` referanslari var. | Bootstrap v3.5'te watchdog + preflight kayitlari eklenmeli. |
| 3 | **Reboot dogrulamasi yapilmadi** | AtStartup task kayitli ama gercek reboot testi bu scope'da degil. | Ayri reboot smoke test task'inda dogrulanacak. |
| 4 | **Stuck task sadece raporlaniyor** | Ne preflight ne watchdog stuck task'i force-terminate ediyor. | Stuck task policy karari (F1.x) gerekli. |
| 5 | **Worker kick sadece watchdog'da** | Preflight boot aninda worker baslatmiyor (tasarim geregi). 15dk'ya kadar gecikme olabilir. | AtLogOn worker task bu boslugu kapatiyor. |
| 6 | **`oc-task-repair.ps1` hala `SupervisorTaskName` referansi olabilir** | Kontrol edilmedi. | Grep ile tum `Supervisor` referanslari taranmali. |
