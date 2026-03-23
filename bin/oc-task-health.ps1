$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout
$pendingCount = 0
$leaseCount = 0
$deadLetterCount = 0
$taskCount = 0

if (Test-Path -LiteralPath $config.QueuePendingPath) {
    $pendingCount = @(Get-ChildItem -LiteralPath $config.QueuePendingPath -Filter '*.json' -File).Count
}
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $leaseCount = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File).Count
}
if (Test-Path -LiteralPath $config.QueueDeadLetterPath) {
    $deadLetterCount = @(Get-ChildItem -LiteralPath $config.QueueDeadLetterPath -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
}
if (Test-Path -LiteralPath $config.TasksPath) {
    $taskCount = @(Get-ChildItem -LiteralPath $config.TasksPath -Directory).Count
}

$nonTerminalTasks = 0
$stuckTasks = 0
$stuckCaseA = 0
$stuckCaseB = 0
$stuckThresholdMinutes = $config.StuckWarningMinutes

$workerActive = Test-OcWorkerActive -MutexName $config.WorkerMutexName

# Build lease index for classification
$healthLeaseIndex = @{}
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    foreach ($lf in @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File)) {
        try {
            $ticket = Get-Content -Raw -LiteralPath $lf.FullName | ConvertFrom-Json
            $tid = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
            if (-not [string]::IsNullOrWhiteSpace($tid)) { $healthLeaseIndex[$tid] = $true }
        }
        catch { }
    }
}

if (Test-Path -LiteralPath $config.TasksPath) {
    $taskDirs = @(Get-ChildItem -LiteralPath $config.TasksPath -Directory)
    foreach ($td in $taskDirs) {
        $tjp = Join-Path $td.FullName 'task.json'
        if (-not (Test-Path -LiteralPath $tjp)) { continue }
        try {
            $tj = Get-Content -Raw -LiteralPath $tjp | ConvertFrom-Json
            $st = [string]$tj.status
            if ($st -eq 'running' -or $st -eq 'queued' -or $st -eq 'cancel_requested') {
                $nonTerminalTasks++
                $ref = $tj.startedUtc
                if ([string]::IsNullOrWhiteSpace([string]$ref)) { $ref = $tj.createdUtc }
                if (-not [string]::IsNullOrWhiteSpace([string]$ref)) {
                    $taskAge = (Get-OcUtcAgeMinutes -IsoString $ref)
                    if ($taskAge -ge $stuckThresholdMinutes) {
                        $stuckTasks++
                        $taskId = [string]$tj.taskId
                        if ($workerActive -or $healthLeaseIndex.ContainsKey($taskId)) {
                            $stuckCaseB++
                        }
                        else {
                            $stuckCaseA++
                        }
                    }
                }
            }
        }
        catch { }
    }
}

$scheduledTaskState = 'not_registered'
try {
    $scheduledTask = Get-ScheduledTask -TaskName $config.SchedulerTaskName -ErrorAction Stop
    if ($null -ne $scheduledTask) {
        $scheduledTaskState = [string]$scheduledTask.State
    }
}
catch {
}

$watchdogTaskState = 'not_registered'
try {
    $watchdogTask = Get-ScheduledTask -TaskName $config.WatchdogTaskName -ErrorAction Stop
    if ($null -ne $watchdogTask) {
        $watchdogTaskState = [string]$watchdogTask.State
    }
}
catch {
}

$preflightTaskState = 'not_registered'
try {
    $preflightTask = Get-ScheduledTask -TaskName $config.PreflightTaskName -ErrorAction Stop
    if ($null -ne $preflightTask) {
        $preflightTaskState = [string]$preflightTask.State
    }
}
catch {
}

# Read preflight state file (boot-correlated, atomic)
$lastPreflightUtc = $null
$preflightBootTimeUtc = $null
$preflightResult = $null
$preflightStatePath = Join-Path $config.LogsPath 'preflight-state.json'
if (Test-Path -LiteralPath $preflightStatePath) {
    try {
        $pfState = Get-Content -Raw -LiteralPath $preflightStatePath | ConvertFrom-Json
        $lastPreflightUtc = [string]$pfState.preflightRanUtc
        $preflightBootTimeUtc = [string]$pfState.bootTimeUtc
        $preflightResult = [string]$pfState.result
    }
    catch { }
}

# Get current boot time for correlation
$currentBootTimeUtc = $null
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $currentBootTimeUtc = $os.LastBootUpTime.ToUniversalTime().ToString('o')
}
catch { }

$preflightBootCorrelated = ($null -ne $preflightBootTimeUtc -and $null -ne $currentBootTimeUtc -and $preflightBootTimeUtc -eq $currentBootTimeUtc)

# Detect last watchdog run from log (watchdog has no state file)
$lastWatchdogUtc = $null
$cpLogPath = Join-Path $config.LogsPath 'control-plane.log'
if (Test-Path -LiteralPath $cpLogPath) {
    $recentLines = Get-Content -LiteralPath $cpLogPath -Tail 200
    for ($li = $recentLines.Count - 1; $li -ge 0; $li--) {
        if ($recentLines[$li] -match '\[watchdog\] Watchdog finished') {
            try { $parsed = $recentLines[$li] | ConvertFrom-Json; $lastWatchdogUtc = $parsed.ts } catch { }
            break
        }
    }
}

$statusLevel = 'ok'
$statusReasons = New-Object System.Collections.ArrayList

if (-not (Test-Path -LiteralPath $config.ActionRunnerPath)) {
    $statusLevel = 'error'
    [void]$statusReasons.Add('action runner script missing')
}
if (-not (Test-Path -LiteralPath $config.WorkerScriptPath)) {
    $statusLevel = 'error'
    [void]$statusReasons.Add('worker script missing')
}
if ($scheduledTaskState -eq 'not_registered' -or $scheduledTaskState -eq 'Disabled') {
    if ($statusLevel -ne 'error') { $statusLevel = 'degraded' }
    [void]$statusReasons.Add('worker scheduled task: ' + $scheduledTaskState)
}
if ($stuckTasks -gt 0) {
    if ($statusLevel -ne 'error') { $statusLevel = 'degraded' }
    [void]$statusReasons.Add('stuck tasks: ' + $stuckTasks)
}
if ($pendingCount -gt 0 -and -not $workerActive) {
    if ($statusLevel -ne 'error') { $statusLevel = 'degraded' }
    [void]$statusReasons.Add('pending tickets but worker not active')
}

$result = [ordered]@{
    status = $statusLevel
    statusReasons = @($statusReasons)
    basePath = $config.BasePath
    runtimeRoot = $config.RuntimeRoot
    actionRunnerExists = (Test-Path -LiteralPath $config.ActionRunnerPath)
    workerScriptExists = (Test-Path -LiteralPath $config.WorkerScriptPath)
    workerActive = $workerActive
    taskDefinitions = @(Get-ChildItem -LiteralPath $config.TaskDefsPath -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
    pendingTickets = $pendingCount
    leaseTickets = $leaseCount
    deadLetterTickets = $deadLetterCount
    nonTerminalTasks = $nonTerminalTasks
    stuckTasks = $stuckTasks
    stuckCaseA = $stuckCaseA
    stuckCaseB = $stuckCaseB
    tasks = $taskCount
    scheduledTaskState = $scheduledTaskState
    watchdogTaskState = $watchdogTaskState
    preflightTaskState = $preflightTaskState
    lastPreflightUtc = $lastPreflightUtc
    preflightBootTimeUtc = $preflightBootTimeUtc
    preflightResult = $preflightResult
    preflightBootCorrelated = $preflightBootCorrelated
    currentBootTimeUtc = $currentBootTimeUtc
    lastWatchdogUtc = $lastWatchdogUtc
}

$result | ConvertTo-Json -Depth 20
exit 0