param(
    [int]$StuckMinutes = 60,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout
$repairedTasks = 0
$repairedLeases = 0
$skipped = 0

Write-Output ('Repair scan started. StuckMinutes=' + $StuckMinutes + ' DryRun=' + $DryRun)

# 1) Scan tasks for stuck non-terminal states
Write-Output '--- Phase 1: Stuck tasks ---'
if (Test-Path -LiteralPath $config.TasksPath) {
    $taskDirs = @(Get-ChildItem -LiteralPath $config.TasksPath -Directory)
    foreach ($taskDir in $taskDirs) {
        $taskJsonPath = Join-Path $taskDir.FullName 'task.json'
        if (-not (Test-Path -LiteralPath $taskJsonPath)) { continue }

        try { $task = Read-OcJson -Path $taskJsonPath } catch { continue }

        $status = [string](Get-OcPropertyValue -Object $task -Name 'status')
        $isTerminal = ($status -eq 'failed' -or $status -eq 'succeeded' -or $status -eq 'cancelled')
        if ($isTerminal) { continue }

        $startedUtc = Get-OcPropertyValue -Object $task -Name 'startedUtc'
        $createdUtc = Get-OcPropertyValue -Object $task -Name 'createdUtc'
        $refTime = $null
        if (-not [string]::IsNullOrWhiteSpace([string]$startedUtc)) { $refTime = ConvertTo-OcUtcDateTime -IsoString $startedUtc }
        elseif (-not [string]::IsNullOrWhiteSpace([string]$createdUtc)) { $refTime = ConvertTo-OcUtcDateTime -IsoString $createdUtc }
        if ($null -eq $refTime) { continue }

        $age = ([DateTime]::UtcNow - $refTime).TotalMinutes
        if ($age -lt $StuckMinutes) { $skipped++; continue }

        $taskId = [string](Get-OcPropertyValue -Object $task -Name 'taskId')
        $eventsPath = Join-Path $taskDir.FullName 'events.jsonl'

        $targetStatus = 'failed'
        $eventName = 'task_failed_recovered'
        $reason = 'Repaired: stuck in ' + $status + ' for ' + [math]::Round($age) + ' minutes.'

        if ($status -eq 'cancel_requested') {
            $targetStatus = 'cancelled'
            $eventName = 'task_cancelled_recovered'
            $reason = 'Repaired: stuck in cancel_requested for ' + [math]::Round($age) + ' minutes.'
        }

        if ($DryRun) {
            Write-Output ('DRY: Would set ' + $taskId + ' from ' + $status + ' to ' + $targetStatus + ' (age=' + [math]::Round($age) + 'min)')
            $repairedTasks++
            continue
        }

        $task.status = $targetStatus
        $task.finishedUtc = [DateTime]::UtcNow.ToString('o')
        $task.lastError = $reason
        Save-OcJson -Path $taskJsonPath -Object $task

        if (Test-Path -LiteralPath $eventsPath) {
            Append-OcTaskEvent -EventsPath $eventsPath -EventName $eventName -TaskId $taskId -Data @{
                previousStatus = $status
                stuckMinutes = [math]::Round($age)
            }
        }

        Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('Task repaired: ' + $taskId + ' ' + $status + ' -> ' + $targetStatus)
        Write-Output ('REPAIRED: ' + $taskId + ' (' + $status + ' -> ' + $targetStatus + ', ' + [math]::Round($age) + 'min)')
        $repairedTasks++
    }
}

# 2) Clean orphan leases (lease exists but task is already terminal)
Write-Output '--- Phase 2: Orphan leases ---'
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $leaseFiles = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File -ErrorAction SilentlyContinue)
    foreach ($lf in $leaseFiles) {
        try {
            $ticket = Read-OcJson -Path $lf.FullName
            $leaseTaskId = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
            if ([string]::IsNullOrWhiteSpace($leaseTaskId)) {
                if ($DryRun) { Write-Output ('DRY: Would remove orphan lease (no taskId): ' + $lf.Name) }
                else {
                    Ensure-OcDirectory -Path $config.QueueDeadLetterPath
                    Move-Item -LiteralPath $lf.FullName -Destination (Join-Path $config.QueueDeadLetterPath $lf.Name) -Force
                    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('Orphan lease removed (no taskId): ' + $lf.Name)
                    Write-Output ('REMOVED: orphan lease (no taskId) ' + $lf.Name)
                }
                $repairedLeases++
                continue
            }

            $tp = Get-OcTaskPaths -TaskId $leaseTaskId -RuntimeConfig $config
            if (-not (Test-Path -LiteralPath $tp.TaskJsonPath)) {
                if ($DryRun) { Write-Output ('DRY: Would remove orphan lease (task missing): ' + $lf.Name) }
                else {
                    Ensure-OcDirectory -Path $config.QueueDeadLetterPath
                    Move-Item -LiteralPath $lf.FullName -Destination (Join-Path $config.QueueDeadLetterPath $lf.Name) -Force
                    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('Orphan lease removed (task missing): ' + $lf.Name)
                    Write-Output ('REMOVED: orphan lease (task missing) ' + $lf.Name)
                }
                $repairedLeases++
                continue
            }

            $leaseTask = Read-OcJson -Path $tp.TaskJsonPath
            $leaseTaskStatus = [string](Get-OcPropertyValue -Object $leaseTask -Name 'status')
            $leaseTaskTerminal = ($leaseTaskStatus -eq 'failed' -or $leaseTaskStatus -eq 'succeeded' -or $leaseTaskStatus -eq 'cancelled')

            if ($leaseTaskTerminal) {
                if ($DryRun) { Write-Output ('DRY: Would remove stale lease on terminal task: ' + $lf.Name + ' (task ' + $leaseTaskId + ' is ' + $leaseTaskStatus + ')') }
                else {
                    Remove-Item -LiteralPath $lf.FullName -Force
                    if (Test-Path -LiteralPath $tp.EventsPath) {
                        Append-OcTaskEvent -EventsPath $tp.EventsPath -EventName 'stale_lease_removed' -TaskId $leaseTaskId -Data @{
                            ticket = $lf.Name
                            taskStatus = $leaseTaskStatus
                        }
                    }
                    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('Stale lease removed: ' + $lf.Name + ' (task ' + $leaseTaskId + ' is ' + $leaseTaskStatus + ')')
                    Write-Output ('REMOVED: stale lease ' + $lf.Name + ' (task is ' + $leaseTaskStatus + ')')
                }
                $repairedLeases++
            }
        }
        catch {
            Write-Output ('ERROR: Could not process lease ' + $lf.Name + ': ' + $_.Exception.Message)
        }
    }
}

# 3) Summary
$dlCount = 0
if (Test-Path -LiteralPath $config.QueueDeadLetterPath) {
    $dlCount = @(Get-ChildItem -LiteralPath $config.QueueDeadLetterPath -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
}
$pendingCount = 0
if (Test-Path -LiteralPath $config.QueuePendingPath) {
    $pendingCount = @(Get-ChildItem -LiteralPath $config.QueuePendingPath -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
}
$remainingLeases = 0
if (Test-Path -LiteralPath $config.QueueLeasesPath) {
    $remainingLeases = @(Get-ChildItem -LiteralPath $config.QueueLeasesPath -Filter '*.json' -File -ErrorAction SilentlyContinue).Count
}

Write-Output ('--- Summary ---')
Write-Output ('Tasks repaired: ' + $repairedTasks)
Write-Output ('Tasks skipped (too recent): ' + $skipped)
Write-Output ('Leases repaired: ' + $repairedLeases)
Write-Output ('Pending tickets: ' + $pendingCount)
Write-Output ('Remaining leases: ' + $remainingLeases)
Write-Output ('Dead-letter tickets: ' + $dlCount)
exit 0