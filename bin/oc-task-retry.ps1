param(
    [Parameter(Mandatory = $true)][string]$TaskId,
    [int]$Priority = 0,
    [int]$MaxRetries = 3,
    [string]$Source = '',
    [switch]$AllowCancelled,
    [switch]$NoWorkerKick
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

# --- Validate task exists ---
if (-not (Test-Path -LiteralPath $taskPaths.TaskJsonPath)) {
    Write-OcRejectionAndExit -ReasonCode 'UNKNOWN_TASK' -Message 'Original task was not found.' -TaskId $TaskId -Source $Source
}

$originalTask = Read-OcJson -Path $taskPaths.TaskJsonPath
$originalStatus = [string](Get-OcPropertyValue -Object $originalTask -Name 'status')
$taskName = [string](Get-OcPropertyValue -Object $originalTask -Name 'taskName')

# --- Validate status ---
if ($originalStatus -eq 'succeeded') {
    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message 'Cannot retry a succeeded task.' -TaskName $taskName -TaskId $TaskId -Source $Source
}
if ($originalStatus -eq 'running') {
    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message 'Cannot retry a running task. Cancel or wait for completion first.' -TaskName $taskName -TaskId $TaskId -Source $Source
}
if ($originalStatus -eq 'queued') {
    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message 'Cannot retry a queued task. It has not been executed yet.' -TaskName $taskName -TaskId $TaskId -Source $Source
}
if ($originalStatus -eq 'cancel_requested') {
    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message 'Cannot retry a task with pending cancellation.' -TaskName $taskName -TaskId $TaskId -Source $Source
}
if ($originalStatus -eq 'cancelled' -and -not $AllowCancelled) {
    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message 'Cannot retry a cancelled task without -AllowCancelled switch.' -TaskName $taskName -TaskId $TaskId -Source $Source
}

$allowedStatuses = @('failed')
if ($AllowCancelled) { $allowedStatuses += 'cancelled' }
if ($allowedStatuses -notcontains $originalStatus) {
    Write-OcRejectionAndExit -ReasonCode 'TASK_STATE_INVALID' -Message ('Cannot retry task in status: ' + $originalStatus) -TaskName $taskName -TaskId $TaskId -Source $Source
}

# --- Check retry chain depth ---
$retryChainDepth = 0
$checkId = $TaskId
while ($true) {
    $checkPaths = Get-OcTaskPaths -TaskId $checkId -RuntimeConfig $config
    if (-not (Test-Path -LiteralPath $checkPaths.TaskJsonPath)) { break }
    $checkTask = Read-OcJson -Path $checkPaths.TaskJsonPath
    $fromId = Get-OcPropertyValue -Object $checkTask -Name 'retriedFromTaskId'
    if ([string]::IsNullOrWhiteSpace([string]$fromId)) { break }
    $retryChainDepth++
    $checkId = [string]$fromId
    if ($retryChainDepth -gt $MaxRetries + 5) { break }
}
if ($retryChainDepth -ge $MaxRetries) {
    Write-OcRejectionAndExit -ReasonCode 'TASK_POLICY_DENIED' -Message ('Retry limit reached. This task is already ' + $retryChainDepth + ' retries deep (max ' + $MaxRetries + ').') -TaskName $taskName -TaskId $TaskId -Source $Source
}

# --- Validate task name ---
if ([string]::IsNullOrWhiteSpace($taskName) -or $taskName -notmatch '^[A-Za-z0-9_-]+$') {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'Original task has invalid taskName.' -TaskId $TaskId -Source $Source
}

# --- Read task definition ---
$defPath = Join-Path $config.TaskDefsPath ($taskName + '.json')
if (-not (Test-Path -LiteralPath $defPath)) {
    Write-OcRejectionAndExit -ReasonCode 'UNKNOWN_TASK' -Message ('Task definition not found for retry: ' + $taskName) -TaskName $taskName -TaskId $TaskId -Source $Source
}
$def = Read-OcJson -Path $defPath

if ((Get-OcPropertyValue -Object $def -Name 'enqueueEnabled') -ne $true) {
    Write-OcRejectionAndExit -ReasonCode 'TASK_POLICY_DENIED' -Message 'Task definition is not enabled for queueing.' -TaskName $taskName -TaskId $TaskId -Source $Source
}
$approvalPolicy = [string](Get-OcPropertyValue -Object $def -Name 'approvalPolicy')
if ($approvalPolicy -ne 'preapproved') {
    Write-OcRejectionAndExit -ReasonCode 'APPROVAL_REQUIRED' -Message 'Only preapproved task definitions can be retried.' -TaskName $taskName -TaskId $TaskId -Source $Source
}

# --- Resolve priority ---
if ($Priority -le 0) {
    $originalPriority = Get-OcPropertyValue -Object $originalTask -Name 'queuePriority'
    if ($null -ne $originalPriority -and [int]$originalPriority -gt 0) {
        $Priority = [int]$originalPriority
    }
    else {
        $defaultPriority = Get-OcPropertyValue -Object $def -Name 'defaultPriority'
        if ($null -ne $defaultPriority) { $Priority = [int]$defaultPriority } else { $Priority = 5 }
    }
}
if ($Priority -lt 1) { $Priority = 1 }
if ($Priority -gt 9) { $Priority = 9 }

# --- Preserve original input ---
$inputObject = Get-OcPropertyValue -Object $originalTask -Name 'input'
if ($null -eq $inputObject) { $inputObject = [ordered]@{} }

# --- Build new task ---
$stepDefs = @((Get-OcPropertyValue -Object $def -Name 'steps'))
if ($stepDefs.Count -eq 0) {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'Task definition has no steps.' -TaskName $taskName -TaskId $TaskId -Source $Source
}

$newTaskId = New-OcTaskId
$newTaskPaths = Get-OcTaskPaths -TaskId $newTaskId -RuntimeConfig $config
Ensure-OcDirectory -Path $newTaskPaths.TaskDir
Ensure-OcDirectory -Path $newTaskPaths.ArtifactsDir

$steps = New-Object System.Collections.ArrayList
for ($i = 0; $i -lt $stepDefs.Count; $i++) {
    $stepDef = $stepDefs[$i]
    $stepIndex = $i + 1
    $stepId = [string](Get-OcPropertyValue -Object $stepDef -Name 'id')
    if ([string]::IsNullOrWhiteSpace($stepId)) { $stepId = ('step-' + ('{0:D2}' -f $stepIndex)) }
    $actionName = [string](Get-OcPropertyValue -Object $stepDef -Name 'action')
    if ([string]::IsNullOrWhiteSpace($actionName)) {
        Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message ('Step action missing at index ' + $stepIndex) -TaskName $taskName -TaskId $TaskId -Source $Source
    }
    $stepSnapshot = [ordered]@{
        index = $stepIndex
        id = $stepId
        action = $actionName
        status = 'pending'
        approved = ((Get-OcPropertyValue -Object $stepDef -Name 'approved') -eq $true)
        startedUtc = $null
        finishedUtc = $null
        exitCode = $null
        logPath = (Join-Path $newTaskPaths.TaskDir ('step-{0:D2}-output.log' -f $stepIndex))
        outputPreview = ''
        errorMessage = $null
    }
    [void]$steps.Add([pscustomobject]$stepSnapshot)
}

$ticketName = ('p{0:D2}-{1}.json' -f $Priority, $newTaskId)
$ticketPath = Join-Path $config.QueuePendingPath $ticketName

$newTask = [ordered]@{
    taskId = $newTaskId
    taskName = $taskName
    description = [string](Get-OcPropertyValue -Object $def -Name 'description')
    status = 'queued'
    createdUtc = [DateTime]::UtcNow.ToString('o')
    startedUtc = $null
    finishedUtc = $null
    queuePriority = $Priority
    queueTicketName = $ticketName
    currentStepIndex = 0
    currentStepId = $null
    lastError = $null
    artifactPaths = @()
    retriedFromTaskId = $TaskId
    retriedAtUtc = [DateTime]::UtcNow.ToString('o')
    retryChainDepth = $retryChainDepth + 1
    source = $Source
    input = $inputObject
    definition = [ordered]@{
        approvalPolicy = $approvalPolicy
        stepCount = $stepDefs.Count
    }
    steps = @($steps)
}

Save-OcJson -Path $newTaskPaths.TaskJsonPath -Object $newTask
Append-OcTaskEvent -EventsPath $newTaskPaths.EventsPath -EventName 'task_created_by_retry' -TaskId $newTaskId -Data @{
    retriedFromTaskId = $TaskId
    retryChainDepth = $retryChainDepth + 1
    taskName = $taskName
    priority = $Priority
    source = $Source
}

$ticket = [ordered]@{
    taskId = $newTaskId
    taskName = $taskName
    priority = $Priority
    createdUtc = [DateTime]::UtcNow.ToString('o')
}
Save-OcJson -Path $ticketPath -Object $ticket
Append-OcTaskEvent -EventsPath $newTaskPaths.EventsPath -EventName 'task_queued' -TaskId $newTaskId -Data @{
    ticket = $ticketName
}

# Record retry event on original task
if (Test-Path -LiteralPath $taskPaths.EventsPath) {
    Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_retried' -TaskId $TaskId -Data @{
        newTaskId = $newTaskId
        retryChainDepth = $retryChainDepth + 1
    }
}

Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'info' -Message ('Task retried: ' + $TaskId + ' -> ' + $newTaskId)

if (-not $NoWorkerKick) {
    try { Invoke-OcWorkerKick -RuntimeConfig $config -Source 'retry' } catch {
        Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('Worker kick failed for retry ' + $newTaskId + ': ' + $_.Exception.Message)
    }
}

$result = [ordered]@{
    status = 'queued'
    newTaskId = $newTaskId
    retriedFromTaskId = $TaskId
    taskName = $taskName
    priority = $Priority
    retryChainDepth = $retryChainDepth + 1
    taskPath = $newTaskPaths.TaskJsonPath
}
$result | ConvertTo-Json -Depth 10
exit 0
