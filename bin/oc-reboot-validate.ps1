# oc-reboot-validate.ps1
# Reboot readiness and post-reboot validation script.
# Usage:
#   -Phase pre    : check readiness before reboot
#   -Phase post   : validate runtime after boot + login
#   -Phase smoke  : run known-good create_note task end-to-end

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('pre', 'post', 'smoke')]
    [string]$Phase
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout
$pass = 0
$fail = 0
$checks = New-Object System.Collections.ArrayList

function Add-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    if ($Ok) { $script:pass++ } else { $script:fail++ }
    [void]$script:checks.Add([ordered]@{
        check = $Name
        result = if ($Ok) { 'PASS' } else { 'FAIL' }
        detail = $Detail
    })
}

# ==================== PRE-REBOOT ====================
if ($Phase -eq 'pre') {
    # 1. Scheduled tasks registered
    $taskNames = @(
        @{ Name = $config.PreflightTaskName; Label = 'preflight' },
        @{ Name = $config.SchedulerTaskName; Label = 'worker' },
        @{ Name = $config.WatchdogTaskName; Label = 'watchdog' }
    )
    foreach ($tn in $taskNames) {
        $task = Get-ScheduledTask -TaskName $tn.Name -ErrorAction SilentlyContinue
        $ok = ($null -ne $task -and [string]$task.State -ne 'Disabled')
        $state = if ($null -ne $task) { [string]$task.State } else { 'not_registered' }
        Add-Check -Name ($tn.Label + ' task') -Ok $ok -Detail ($tn.Name + ' = ' + $state)
    }

    # 2. Key scripts exist
    $scripts = @($config.WorkerScriptPath, $config.RunnerScriptPath, $config.ActionRunnerPath, $config.WatchdogScriptPath, $config.PreflightScriptPath)
    $missing = @($scripts | Where-Object { -not (Test-Path -LiteralPath $_) })
    $allExist = $missing.Count -eq 0
    Add-Check -Name 'key scripts' -Ok $allExist -Detail ('' + $scripts.Count + ' checked')

    # 3. Manifest parseable
    $manifestOk = $false
    try { $null = Get-Content -Raw -LiteralPath $config.ManifestPath | ConvertFrom-Json; $manifestOk = $true } catch { }
    Add-Check -Name 'manifest' -Ok $manifestOk -Detail $config.ManifestPath

    # 4. No stuck tasks
    $health = & (Join-Path $config.BinPath 'oc-task-health.ps1') | ConvertFrom-Json
    Add-Check -Name 'no stuck tasks' -Ok ($health.stuckTasks -eq 0) -Detail ('stuck=' + $health.stuckTasks)

    # 5. No pending tickets
    Add-Check -Name 'no pending tickets' -Ok ($health.pendingTickets -eq 0) -Detail ('pending=' + $health.pendingTickets)

    # 6. No active leases
    Add-Check -Name 'no active leases' -Ok ($health.leaseTickets -eq 0) -Detail ('leases=' + $health.leaseTickets)
}

# ==================== POST-REBOOT ====================
if ($Phase -eq 'post') {
    $health = & (Join-Path $config.BinPath 'oc-task-health.ps1') | ConvertFrom-Json

    # 1. Preflight ran in current boot session (boot-correlated)
    $preflightRan = -not [string]::IsNullOrWhiteSpace($health.lastPreflightUtc)
    Add-Check -Name 'preflight ran' -Ok $preflightRan -Detail ('lastPreflightUtc=' + $health.lastPreflightUtc)

    # 2. Preflight boot-correlated to current session
    $bootCorrelated = ($health.preflightBootCorrelated -eq $true)
    Add-Check -Name 'preflight boot-correlated' -Ok $bootCorrelated -Detail ('preflightBoot=' + $health.preflightBootTimeUtc + ' currentBoot=' + $health.currentBootTimeUtc)

    # 3. Health status
    Add-Check -Name 'health status' -Ok ($health.status -eq 'ok') -Detail ('status=' + $health.status)

    # 3. Scheduled tasks still registered
    $taskNames = @(
        @{ Name = $config.PreflightTaskName; Label = 'preflight' },
        @{ Name = $config.SchedulerTaskName; Label = 'worker' },
        @{ Name = $config.WatchdogTaskName; Label = 'watchdog' }
    )
    foreach ($tn in $taskNames) {
        $task = Get-ScheduledTask -TaskName $tn.Name -ErrorAction SilentlyContinue
        $ok = ($null -ne $task -and [string]$task.State -ne 'Disabled')
        $state = if ($null -ne $task) { [string]$task.State } else { 'not_registered' }
        Add-Check -Name ($tn.Label + ' task') -Ok $ok -Detail ($tn.Name + ' = ' + $state)
    }

    # 4. Worker active (after login)
    Add-Check -Name 'worker active' -Ok $health.workerActive -Detail ('workerActive=' + $health.workerActive)

    # 5. No stuck tasks
    Add-Check -Name 'no stuck tasks' -Ok ($health.stuckTasks -eq 0) -Detail ('stuck=' + $health.stuckTasks)
}

# ==================== SMOKE TEST ====================
if ($Phase -eq 'smoke') {
    $smokeFilename = 'reboot-smoke-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss') + '.txt'
    $smokeContent = 'Reboot smoke test at ' + [DateTime]::UtcNow.ToString('o')
    $b64 = Encode-OcJsonToBase64 -JsonString ('{"filename":"' + $smokeFilename + '","content":"' + $smokeContent + '"}')

    # 1. Enqueue
    $enqueueResult = & (Join-Path $config.BinPath 'oc-task-enqueue.ps1') -TaskName 'create_note' -InputBase64 $b64 -Source 'reboot-validate' | ConvertFrom-Json
    $enqueueOk = ($enqueueResult.status -eq 'queued')
    Add-Check -Name 'enqueue' -Ok $enqueueOk -Detail ('taskId=' + $enqueueResult.taskId)

    if ($enqueueOk) {
        $taskId = $enqueueResult.taskId

        # 2. Wait for completion (max 30s)
        $timeout = 30
        $elapsed = 0
        $finalStatus = 'unknown'
        while ($elapsed -lt $timeout) {
            Start-Sleep -Seconds 2
            $elapsed += 2
            $taskState = & (Join-Path $config.BinPath 'oc-task-get.ps1') -TaskId $taskId | ConvertFrom-Json
            $finalStatus = [string]$taskState.status
            if ($finalStatus -eq 'succeeded' -or $finalStatus -eq 'failed' -or $finalStatus -eq 'cancelled') { break }
        }

        Add-Check -Name 'task completed' -Ok ($finalStatus -eq 'succeeded') -Detail ('status=' + $finalStatus + ' elapsed=' + $elapsed + 's')

        # 3. Result file exists
        $resultPath = Join-Path $config.ResultsPath $smokeFilename
        $fileExists = Test-Path -LiteralPath $resultPath
        Add-Check -Name 'result file' -Ok $fileExists -Detail $resultPath
    }
}

# ==================== SUMMARY ====================
$overall = if ($fail -eq 0) { 'READY' } else { 'NOT_READY' }
if ($Phase -eq 'post' -and $fail -eq 0) { $overall = 'VERIFIED' }
if ($Phase -eq 'smoke' -and $fail -eq 0) { $overall = 'VERIFIED' }

$summary = [ordered]@{
    phase = $Phase
    result = $overall
    pass = $pass
    fail = $fail
    timestamp = [DateTime]::UtcNow.ToString('o')
    checks = @($checks)
}
$summary | ConvertTo-Json -Depth 10
if ($fail -gt 0) { exit 1 } else { exit 0 }
