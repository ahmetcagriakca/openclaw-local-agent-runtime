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

# -- 6. Terminal task stale lease/ticket cleanup (Case C) -----------------------
$staleLeaseCleaned = 0
$currentLeaseFiles = @()
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $currentLeaseFiles = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File)
}
foreach ($lf in $currentLeaseFiles) {
    try {
        $ticket = Get-Content -Raw -LiteralPath $lf.FullName | ConvertFrom-Json
        $leaseTaskId = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
        if ([string]::IsNullOrWhiteSpace($leaseTaskId)) { continue }
        $tp = Get-OcTaskPaths -TaskId $leaseTaskId -RuntimeConfig $config
        if (-not (Test-Path -LiteralPath $tp.TaskJsonPath)) { continue }
        $leaseTask = Get-Content -Raw -LiteralPath $tp.TaskJsonPath | ConvertFrom-Json
        $leaseStatus = [string](Get-OcPropertyValue -Object $leaseTask -Name 'status')
        if ($leaseStatus -eq 'failed' -or $leaseStatus -eq 'succeeded' -or $leaseStatus -eq 'cancelled') {
            Remove-Item -LiteralPath $lf.FullName -Force
            if (Test-Path -LiteralPath $tp.EventsPath) {
                Append-OcTaskEvent -EventsPath $tp.EventsPath -EventName 'stale_lease_removed' -TaskId $leaseTaskId -Data @{
                    ticket = $lf.Name; taskStatus = $leaseStatus; recoveredBy = 'watchdog'
                }
            }
            Write-WatchdogLog -Level 'warn' -Message ('Case C: removed stale lease for terminal task ' + $leaseTaskId + ' (' + $leaseStatus + ')')
            $staleLeaseCleaned++
        }
    }
    catch { }
}
if ($staleLeaseCleaned -gt 0) {
    [void]$repairs.Add('Case C: cleaned ' + $staleLeaseCleaned + ' stale leases on terminal tasks')
    Set-Degraded -Reason ('Case C: ' + $staleLeaseCleaned + ' stale leases cleaned on terminal tasks')
}

# -- 7. Stuck task policy (Case A / Case B) ------------------------------------
$workerActive = Test-OcWorkerActive -MutexName $config.WorkerMutexName

# Build lease index: taskId -> lease file name
$leaseIndex = @{}
$freshLeaseFiles = @()
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $freshLeaseFiles = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File)
}
foreach ($lf in $freshLeaseFiles) {
    try {
        $ticket = Get-Content -Raw -LiteralPath $lf.FullName | ConvertFrom-Json
        $tid = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
        if (-not [string]::IsNullOrWhiteSpace($tid)) { $leaseIndex[$tid] = $lf.Name }
    }
    catch { }
}

$stuckThreshold = $config.StuckRecoveryMinutes
$safeRecovered = 0
$ambiguousCount = 0
$stuckTotal = 0

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

            $stuckTotal++
            $taskId = [string]$tj.taskId
            $hasLease = $leaseIndex.ContainsKey($taskId)

            # Case B — Ambiguous: worker active or lease still held
            if ($workerActive -or $hasLease) {
                $ambiguousCount++
                Write-WatchdogLog -Level 'warn' -Message ('Case B (ambiguous): ' + $taskId + ' status=' + $tst + ' age=' + [math]::Round($age) + 'min workerActive=' + $workerActive + ' hasLease=' + $hasLease)
                continue
            }

            # Case A — Safe stuck: no worker, no lease, abandoned
            $targetStatus = 'failed'
            $eventName = 'stuck_task_auto_failed'
            $reason = 'Stuck task auto-failed by watchdog (Case A). Status was ' + $tst + ', age ' + [math]::Round($age) + ' min. No active worker, no lease.'
            if ($tst -eq 'cancel_requested') {
                $targetStatus = 'cancelled'
                $eventName = 'stuck_task_auto_cancelled'
                $reason = 'Stuck task auto-cancelled by watchdog (Case A). Status was cancel_requested, age ' + [math]::Round($age) + ' min. No active worker, no lease.'
            }

            $tj.status = $targetStatus
            $tj.finishedUtc = [DateTime]::UtcNow.ToString('o')
            $tj.lastError = $reason
            Save-OcJson -Path $tjp -Object $tj

            $eventsPath = Join-Path $td.FullName 'events.jsonl'
            if (Test-Path -LiteralPath $eventsPath) {
                Append-OcTaskEvent -EventsPath $eventsPath -EventName $eventName -TaskId $taskId -Data @{
                    previousStatus = $tst
                    stuckMinutes = [math]::Round($age)
                    recoveredBy = 'watchdog'
                    policy = 'Case A - safe stuck'
                }
            }

            Write-WatchdogLog -Level 'warn' -Message ('Case A (safe stuck): ' + $taskId + ' ' + $tst + ' -> ' + $targetStatus + ' (age=' + [math]::Round($age) + 'min)')
            [void]$repairs.Add('Case A: ' + $taskId + ' ' + $tst + ' -> ' + $targetStatus)
            $safeRecovered++
        }
        catch { }
    }
}

if ($stuckTotal -eq 0) {
    Set-Ok -Reason 'stuck tasks: none'
}
else {
    $parts = @()
    if ($safeRecovered -gt 0) { $parts += ('Case A auto-resolved: ' + $safeRecovered) }
    if ($ambiguousCount -gt 0) { $parts += ('Case B ambiguous: ' + $ambiguousCount) }
    Set-Degraded -Reason ('stuck tasks: ' + $stuckTotal + ' (' + ($parts -join ', ') + ')')
    Write-WatchdogLog -Level 'warn' -Message ('Stuck tasks: total=' + $stuckTotal + ' safeRecovered=' + $safeRecovered + ' ambiguous=' + $ambiguousCount)
}

# -- 8. Worker status + kick if needed ------------------------------------------
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
        Invoke-OcWorkerKick -RuntimeConfig $config -Source 'watchdog'
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
    workerActive        = $workerActive
    workerKicked        = $workerKicked
    pendingTickets      = $pendingCount
    stuckTasks          = $stuckTotal
    stuckSafeRecovered  = $safeRecovered
    stuckAmbiguous      = $ambiguousCount
    staleLeaseCleaned   = $staleLeaseCleaned
    recoveredLeases     = $recoveredLeases
}

Write-WatchdogLog -Level 'info' -Message ('Watchdog finished. Status: ' + $overallStatus + '. Repairs: ' + $repairs.Count)

# -- 9. System health snapshot (Phase 1.6 additive) ----------------------------
try {
    $healthSnapshotScript = Join-Path (Split-Path -Parent $PSCommandPath) 'oc-health-snapshot.ps1'
    if (Test-Path -LiteralPath $healthSnapshotScript) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $healthSnapshotScript 2>&1 | Out-Null
        Write-WatchdogLog -Level 'info' -Message 'Health snapshot written.'
    }
} catch {
    Write-WatchdogLog -Level 'warn' -Message ('Health snapshot failed: ' + $_.Exception.Message)
}

# -- 10. Proactive Telegram notifications (Phase 1.7) --------------------------
try {
    $healthNotifyScript = Join-Path (Split-Path -Parent $PSCommandPath) 'oc-health-notify.ps1'
    if (Test-Path -LiteralPath $healthNotifyScript) {
        & pwsh -NoProfile -ExecutionPolicy Bypass -File $healthNotifyScript -Mode watchdog 2>&1 | Out-Null
        Write-WatchdogLog -Level 'info' -Message 'Health notification check completed.'
    }
} catch {
    Write-WatchdogLog -Level 'warn' -Message ('Health notification failed: ' + $_.Exception.Message)
}

$summary | ConvertTo-Json -Depth 10
exit 0
