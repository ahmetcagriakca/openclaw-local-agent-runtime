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

# ── 1. Runtime layout validation ──────────────────────────────────────────────
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

# ── 2. Required script validation ─────────────────────────────────────────────
$requiredScripts = @(
    $config.WorkerScriptPath,
    $config.RunnerScriptPath,
    $config.ActionRunnerPath,
    $config.WatchdogScriptPath
)
$missingScripts = @($requiredScripts | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missingScripts.Count -eq 0) {
    Set-Ok -Reason 'scripts: all required scripts present'
}
else {
    Set-Error -Reason ('scripts missing: ' + ($missingScripts -join ', '))
    Write-PreflightLog -Level 'error' -Message ('Missing scripts: ' + ($missingScripts -join ', '))
}

# ── 3. Manifest validation ────────────────────────────────────────────────────
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

# ── 4. Task definition validation ─────────────────────────────────────────────
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

# ── 5. Scheduled task validation ──────────────────────────────────────────────
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
            Write-PreflightLog -Level 'warn' -Message ($tc.Label + ' scheduled task is Disabled: ' + $tc.Name)
        }
    }
    catch {
        Set-Degraded -Reason ($tc.Label + ' scheduled task: ' + $tc.Name + ' not registered')
        Write-PreflightLog -Level 'warn' -Message ($tc.Label + ' scheduled task not found: ' + $tc.Name)
    }
}

# ── 6. Stale lease recovery ──────────────────────────────────────────────────
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
            $leaseAge = (Get-OcUtcAgeMinutes -IsoString $leasedAt)
        }
        else {
            $leaseAge = ([DateTime]::UtcNow - $lf.LastWriteTimeUtc).TotalMinutes
        }
    }
    catch {
        $leaseAge = ([DateTime]::UtcNow - $lf.LastWriteTimeUtc).TotalMinutes
    }

    if ($leaseAge -ge $config.StaleLeaseMinutes) {
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

# ── 7. Stuck task classification (observe-only, no mutations at boot) ────────
$workerActiveForStuck = Test-OcWorkerActive -MutexName $config.WorkerMutexName

# Build lease index
$preflightLeaseIndex = @{}
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    foreach ($lf in @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File)) {
        try {
            $ticket = Get-Content -Raw -LiteralPath $lf.FullName | ConvertFrom-Json
            $tid = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
            if (-not [string]::IsNullOrWhiteSpace($tid)) { $preflightLeaseIndex[$tid] = $lf.Name }
        }
        catch { }
    }
}

$stuckThreshold = $config.StuckRecoveryMinutes
$stuckCount = 0
$caseACount = 0
$caseBCount = 0
if (Test-Path -LiteralPath $config.TasksPath) {
    $taskDirs = @(Get-ChildItem -LiteralPath $config.TasksPath -Directory)
    foreach ($td in $taskDirs) {
        $tjp = Join-Path $td.FullName 'task.json'
        if (-not (Test-Path -LiteralPath $tjp)) { continue }
        try {
            $tj = Get-Content -Raw -LiteralPath $tjp | ConvertFrom-Json
            $tst = [string]$tj.status
            if ($tst -ne 'running' -and $tst -ne 'queued' -and $tst -ne 'cancel_requested') { continue }
            $ref = $tj.startedUtc
            if ([string]::IsNullOrWhiteSpace([string]$ref)) { $ref = $tj.createdUtc }
            if ([string]::IsNullOrWhiteSpace([string]$ref)) { continue }
            $age = (Get-OcUtcAgeMinutes -IsoString $ref)
            if ($age -lt $stuckThreshold) { continue }

            $stuckCount++
            $taskId = [string]$tj.taskId
            $hasLease = $preflightLeaseIndex.ContainsKey($taskId)

            if ($workerActiveForStuck -or $hasLease) {
                $caseBCount++
                Write-PreflightLog -Level 'warn' -Message ('Stuck task (Case B ambiguous): ' + $td.Name + ' status=' + $tst + ' age=' + [math]::Round($age) + 'min')
            }
            else {
                $caseACount++
                Write-PreflightLog -Level 'warn' -Message ('Stuck task (Case A safe): ' + $td.Name + ' status=' + $tst + ' age=' + [math]::Round($age) + 'min - deferred to watchdog')
            }
        }
        catch { }
    }
}
if ($stuckCount -eq 0) {
    Set-Ok -Reason 'stuck tasks: none'
}
else {
    $parts = @()
    if ($caseACount -gt 0) { $parts += ('Case A safe: ' + $caseACount) }
    if ($caseBCount -gt 0) { $parts += ('Case B ambiguous: ' + $caseBCount) }
    Set-Degraded -Reason ('stuck tasks: ' + $stuckCount + ' (' + ($parts -join ', ') + ')')
    Write-PreflightLog -Level 'warn' -Message ($stuckCount.ToString() + ' stuck tasks detected. Case A=' + $caseACount + ' Case B=' + $caseBCount)
}

# ── 8. Log rotation ─────────────────────────────────────────────────────────
$logTargets = @(
    (Join-Path $config.LogsPath 'control-plane.log'),
    (Join-Path $config.LogsPath 'worker.log'),
    (Join-Path $config.LogsPath 'action-execution.log')
)
foreach ($logTarget in $logTargets) {
    Invoke-OcLogRotate -LogPath $logTarget -MaxSizeBytes 5242880 -KeepCount 3
}

# ── 9. Worker status (observe only, no kick) ────────────────────────────────
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
    Write-PreflightLog -Level 'warn' -Message ('Worker not active with ' + $pendingCount + ' pending tickets. Not kicking at startup — deferred to logon worker and watchdog.')
}
else {
    Set-Ok -Reason 'worker: not active (no pending tickets)'
}

# ── Summary ──────────────────────────────────────────────────────────────────
$summary = [ordered]@{
    phase       = 'startup-preflight'
    status      = $overallStatus
    timestamp   = [DateTime]::UtcNow.ToString('o')
    checks      = @($checks)
    repairs     = @($repairs)
    workerActive        = $workerActive
    pendingTickets      = $pendingCount
    stuckTasks          = $stuckCount
    stuckCaseA          = $caseACount
    stuckCaseB          = $caseBCount
    recoveredLeases     = $recoveredLeases
}

Write-PreflightLog -Level 'info' -Message ('Startup preflight finished. Status: ' + $overallStatus + '. Checks: ' + $checks.Count + '. Repairs: ' + $repairs.Count + '.')

# ── Write atomic state file for boot-correlated verification ────────────────
$bootTimeUtc = $null
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $bootTimeUtc = $os.LastBootUpTime.ToUniversalTime().ToString('o')
}
catch { }

$stateFile = [ordered]@{
    preflightRanUtc = [DateTime]::UtcNow.ToString('o')
    bootTimeUtc     = $bootTimeUtc
    result          = $overallStatus
    checksCount     = $checks.Count
    repairsCount    = $repairs.Count
}
$statePath = Join-Path $config.LogsPath 'preflight-state.json'
Save-OcJson -Path $statePath -Object $stateFile

# ── 10. System health snapshot (Phase 1.6 — immediate snapshot at boot) ───────
try {
    $healthSnapshotScript = Join-Path (Split-Path -Parent $PSCommandPath) 'oc-health-snapshot.ps1'
    if (Test-Path -LiteralPath $healthSnapshotScript) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $healthSnapshotScript 2>&1 | Out-Null
        Write-PreflightLog -Level 'info' -Message 'Health snapshot written at boot.'
    }
} catch {
    Write-PreflightLog -Level 'warn' -Message ('Health snapshot failed at boot: ' + $_.Exception.Message)
}

$summary | ConvertTo-Json -Depth 10
exit 0
