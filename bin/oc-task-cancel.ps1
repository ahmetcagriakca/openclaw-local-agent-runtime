param(
    [Parameter(Mandatory = $true)][string]$TaskId,
    [string]$Source = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

# --- Validate TaskId format ---
if ($TaskId -notmatch '^task-[0-9]{8}-[0-9]{9}-[0-9]{4}$') {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message ('Invalid TaskId format: ' + $TaskId) -TaskId $TaskId -Source $Source
}

$config = Initialize-OcRuntimeLayout
$taskPaths = Get-OcTaskPaths -TaskId $TaskId -RuntimeConfig $config

if (-not (Test-Path -LiteralPath $taskPaths.TaskJsonPath)) {
    Write-OcRejectionAndExit -ReasonCode 'UNKNOWN_TASK' -Message 'Task was not found.' -TaskId $TaskId -Source $Source
}

$task = Read-OcJson -Path $taskPaths.TaskJsonPath
$currentStatus = [string](Get-OcPropertyValue -Object $task -Name 'status')
$taskName = [string](Get-OcPropertyValue -Object $task -Name 'taskName')

# --- Terminal state: no-op ---
if ($currentStatus -eq 'succeeded' -or $currentStatus -eq 'failed' -or $currentStatus -eq 'cancelled') {
    $result = [ordered]@{
        status     = 'rejected'
        reasonCode = 'TASK_STATE_INVALID'
        message    = 'Task already in terminal state: ' + $currentStatus
        taskId     = $TaskId
        taskName   = $taskName
        taskStatus = $currentStatus
    }
    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('[rejection] TASK_STATE_INVALID: Task ' + $TaskId + ' already in terminal state: ' + $currentStatus)
    $result | ConvertTo-Json -Depth 10
    exit 1
}

# --- Queued: remove from queue and cancel ---
if ($currentStatus -eq 'queued') {
    $ticketName = [string](Get-OcPropertyValue -Object $task -Name 'queueTicketName')
    if (-not [string]::IsNullOrWhiteSpace($ticketName)) {
        $pendingTicketPath = Join-Path $config.QueuePendingPath $ticketName
        if (Test-Path -LiteralPath $pendingTicketPath) {
            Remove-Item -LiteralPath $pendingTicketPath -Force -ErrorAction SilentlyContinue
        }
    }
    $task.status = 'cancelled'
    $task.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $task.lastError = 'Cancelled by user before execution.'
    Save-OcJson -Path $taskPaths.TaskJsonPath -Object $task
    Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_cancelled' -TaskId $TaskId -Data @{
        previousStatus = $currentStatus
        source = $Source
    }
    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'info' -Message ('Task cancelled: ' + $TaskId)

    $result = [ordered]@{
        status   = 'cancelled'
        taskId   = $TaskId
        taskName = $taskName
        message  = 'Task removed from queue and cancelled.'
    }
    $result | ConvertTo-Json -Depth 10
    exit 0
}

# --- Running: set cancel flag ---
if ($currentStatus -eq 'running') {
    $task.cancelRequested = $true
    Save-OcJson -Path $taskPaths.TaskJsonPath -Object $task
    Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'cancel_requested' -TaskId $TaskId -Data @{
        source = $Source
    }
    Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'info' -Message ('Cancel requested for running task: ' + $TaskId)

    $result = [ordered]@{
        status   = 'cancel_requested'
        taskId   = $TaskId
        taskName = $taskName
        message  = 'Cancel flag set. Task will stop before the next step.'
    }
    $result | ConvertTo-Json -Depth 10
    exit 0
}

# --- Unexpected state ---
Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message ('Task is in an unexpected state: ' + $currentStatus) -TaskName $taskName -TaskId $TaskId -Source $Source
