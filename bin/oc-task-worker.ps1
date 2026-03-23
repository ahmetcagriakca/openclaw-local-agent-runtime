# oc-task-worker.ps1
# Canonical execution model: ephemeral single-pass (Phase 1.5-A).
# Processes all pending tickets in one pass, then exits.
# Any earlier persistent-poll-loop default behavior is superseded.
param(
    [switch]$RunOnce  # Accepted for backward compatibility; behavior is always single-pass.
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout


$mutexCreated = $false
$mutex = New-Object System.Threading.Mutex($false, $config.WorkerMutexName, [ref]$mutexCreated)
$lockTaken = $false

try {
    $lockTaken = $mutex.WaitOne(0)
    if (-not $lockTaken) {
        Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message 'Worker invocation skipped because another instance is active.'
        exit 0
    }

    Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message 'Worker started.'

    Invoke-OcLogRotate -LogPath (Join-Path $config.LogsPath 'worker.log') -MaxSizeBytes 5242880 -KeepCount 3
    Invoke-OcLogRotate -LogPath (Join-Path $config.LogsPath 'control-plane.log') -MaxSizeBytes 5242880 -KeepCount 3

    $pendingTickets = @()
    if (Test-Path -LiteralPath $config.QueuePendingPath) {
        $pendingTickets = @(Get-ChildItem -LiteralPath $config.QueuePendingPath -Filter '*.json' -File | Sort-Object Name, LastWriteTimeUtc)
    }

    foreach ($ticketFile in $pendingTickets) {
        $leasePath = Join-Path $config.QueueLeasesPath $ticketFile.Name
        try {
            Move-Item -LiteralPath $ticketFile.FullName -Destination $leasePath -Force
        }
        catch {
            continue
        }

        $ticket = $null
        $taskId = $null
        $runnerExitCode = -99
        $runnerSuccess = $false

        try {
            $ticket = Read-OcJson -Path $leasePath
            $ticket | Add-Member -NotePropertyName 'leasedAtUtc' -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
            Save-OcJson -Path $leasePath -Object $ticket
            $taskId = [string](Get-OcPropertyValue -Object $ticket -Name 'taskId')
            if ([string]::IsNullOrWhiteSpace($taskId)) {
                throw 'Queue ticket is missing taskId.'
            }

            $taskPaths = Get-OcTaskPaths -TaskId $taskId -RuntimeConfig $config
            if (Test-Path -LiteralPath $taskPaths.EventsPath) {
                Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_claimed' -TaskId $taskId -Data @{
                    ticket = $ticketFile.Name
                }
            }

            Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message ('Claimed task: ' + $taskId)

            $pwshExe = 'C:\Program Files\PowerShell\7\pwsh.exe'
            if (-not (Test-Path -LiteralPath $pwshExe)) { $pwshExe = 'pwsh' }
            & $pwshExe -NoProfile -ExecutionPolicy Bypass -File $config.RunnerScriptPath -TaskId $taskId
            $runnerExitCode = $LASTEXITCODE

            if ($runnerExitCode -eq 0) {
                $runnerSuccess = $true
                Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message ('Task completed: ' + $taskId)
            }
            else {
                Write-OcRuntimeLog -LogName 'worker.log' -Level 'error' -Message ('Task runner exited with code ' + $runnerExitCode + ' for ' + $taskId)
            }
        }
        catch {
            Write-OcRuntimeLog -LogName 'worker.log' -Level 'error' -Message ('Worker failed on ticket ' + $ticketFile.Name + ': ' + $_.Exception.Message)
        }

        # Post-run validation: ensure task is in terminal state regardless of exit code
        if (-not [string]::IsNullOrWhiteSpace($taskId)) {
            try {
                $taskPaths = Get-OcTaskPaths -TaskId $taskId -RuntimeConfig $config
                if (Test-Path -LiteralPath $taskPaths.TaskJsonPath) {
                    $taskSnap = Read-OcJson -Path $taskPaths.TaskJsonPath
                    $taskStatus = [string](Get-OcPropertyValue -Object $taskSnap -Name 'status')

                    $isTerminal = ($taskStatus -eq 'failed' -or $taskStatus -eq 'succeeded' -or $taskStatus -eq 'cancelled')

                    if (-not $isTerminal) {
                        if ($runnerSuccess) {
                            $taskSnap.status = 'succeeded'
                            $taskSnap.finishedUtc = [DateTime]::UtcNow.ToString('o')
                            $taskSnap.lastError = $null
                            Save-OcJson -Path $taskPaths.TaskJsonPath -Object $taskSnap
                            Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_succeeded_recovered' -TaskId $taskId -Data @{
                                reason = 'Runner exited 0 but task was still non-terminal. Forced to succeeded.'
                                previousStatus = $taskStatus
                            }
                            Write-OcRuntimeLog -LogName 'worker.log' -Level 'warn' -Message ('Task recovered to succeeded: ' + $taskId + ' (was ' + $taskStatus + ')')
                        }
                        else {
                            $errMsg = 'Worker-level failure: runner exited with code ' + $runnerExitCode
                            if ($runnerExitCode -eq -99) {
                                $errMsg = 'Worker-level failure: runner did not execute (possible path or config error).'
                            }
                            $taskSnap.status = 'failed'
                            $taskSnap.finishedUtc = [DateTime]::UtcNow.ToString('o')
                            $taskSnap.lastError = $errMsg
                            Save-OcJson -Path $taskPaths.TaskJsonPath -Object $taskSnap
                            Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_failed_recovered' -TaskId $taskId -Data @{
                                reason = $errMsg
                                runnerExitCode = $runnerExitCode
                                previousStatus = $taskStatus
                            }
                            Write-OcRuntimeLog -LogName 'worker.log' -Level 'warn' -Message ('Task force-failed by worker: ' + $taskId + ' (was ' + $taskStatus + ', exit ' + $runnerExitCode + ')')
                        }
                    }
                }
            }
            catch {
                Write-OcRuntimeLog -LogName 'worker.log' -Level 'error' -Message ('Post-run validation failed for task ' + $taskId + ': ' + $_.Exception.Message)
            }
        }

        if (Test-Path -LiteralPath $leasePath) {
            if ($runnerSuccess) {
                Remove-Item -LiteralPath $leasePath -Force -ErrorAction SilentlyContinue
            }
            else {
                Ensure-OcDirectory -Path $config.QueueDeadLetterPath
                $dlPath = Join-Path $config.QueueDeadLetterPath $ticketFile.Name
                try {
                    Move-Item -LiteralPath $leasePath -Destination $dlPath -Force
                    Write-OcRuntimeLog -LogName 'worker.log' -Level 'warn' -Message ('Ticket moved to dead-letter: ' + $ticketFile.Name)
                }
                catch {
                    Remove-Item -LiteralPath $leasePath -Force -ErrorAction SilentlyContinue
                    Write-OcRuntimeLog -LogName 'worker.log' -Level 'error' -Message ('Failed to move to dead-letter, deleted: ' + $ticketFile.Name)
                }
            }
        }
    }

    Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message 'Worker finished.'
    exit 0
}
finally {
    if ($lockTaken) {
        $mutex.ReleaseMutex() | Out-Null
    }
    $mutex.Dispose()
}
