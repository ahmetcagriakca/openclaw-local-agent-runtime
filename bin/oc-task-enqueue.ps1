param(
    [Parameter(Mandatory = $true)][string]$TaskName,
    [string]$InputJson = '{}',
    [string]$InputBase64 = '',
    [int]$Priority = 0,
    [string]$Source = '',
    [switch]$NoWorkerKick
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Initialize-OcRuntimeLayout

# --- Validate task name ---
if ([string]::IsNullOrWhiteSpace($TaskName)) {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'TaskName cannot be empty.' -TaskName $TaskName -Source $Source
}
if ($TaskName -notmatch '^[A-Za-z0-9_-]+$') {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'TaskName contains invalid characters.' -TaskName $TaskName -Source $Source
}
if ($TaskName.Length -gt 128) {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'TaskName exceeds maximum length of 128 characters.' -TaskName $TaskName -Source $Source
}

# --- Validate task definition exists ---
$defPath = Join-Path $config.TaskDefsPath ($TaskName + '.json')
if (-not (Test-Path -LiteralPath $defPath)) {
    Write-OcRejectionAndExit -ReasonCode 'UNKNOWN_TASK' -Message ('Task definition not found: ' + $TaskName) -TaskName $TaskName -Source $Source
}

$def = $null
try {
    $def = Read-OcJson -Path $defPath
}
catch {
    Write-OcRejectionAndExit -ReasonCode 'UNKNOWN_TASK' -Message ('Task definition is not valid JSON: ' + $TaskName) -TaskName $TaskName -Source $Source
}

# --- Validate enqueue policy ---
if ((Get-OcPropertyValue -Object $def -Name 'enqueueEnabled') -ne $true) {
    Write-OcRejectionAndExit -ReasonCode 'TASK_POLICY_DENIED' -Message 'Task definition is not enabled for queueing.' -TaskName $TaskName -Source $Source
}

$approvalPolicy = [string](Get-OcPropertyValue -Object $def -Name 'approvalPolicy')
if ($approvalPolicy -ne 'preapproved') {
    Write-OcRejectionAndExit -ReasonCode 'APPROVAL_REQUIRED' -Message 'Only preapproved task definitions can be enqueued by this interface.' -TaskName $TaskName -Source $Source
}

# --- Validate input ---
$inputObject = $null
if (-not [string]::IsNullOrWhiteSpace($InputBase64)) {
    try {
        $inputObject = Decode-OcBase64Json -Base64String $InputBase64
    }
    catch {
        Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'InputBase64 is not valid base64-encoded JSON.' -TaskName $TaskName -Source $Source
    }
}
else {
    try {
        $inputObject = $InputJson | ConvertFrom-Json
    }
    catch {
        Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'InputJson is not valid JSON.' -TaskName $TaskName -Source $Source
    }
}

# --- Validate steps ---
$stepDefs = @((Get-OcPropertyValue -Object $def -Name 'steps'))
if ($stepDefs.Count -eq 0) {
    Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message 'Task definition has no steps.' -TaskName $TaskName -Source $Source
}

# --- Resolve priority ---
$defaultPriority = Get-OcPropertyValue -Object $def -Name 'defaultPriority'
if ($Priority -le 0) {
    if ($null -ne $defaultPriority) {
        $Priority = [int]$defaultPriority
    }
    else {
        $Priority = 5
    }
}

if ($Priority -lt 1) { $Priority = 1 }
if ($Priority -gt 9) { $Priority = 9 }

# --- Build task ---
$taskId = New-OcTaskId
$taskPaths = Get-OcTaskPaths -TaskId $taskId -RuntimeConfig $config
Ensure-OcDirectory -Path $taskPaths.TaskDir
Ensure-OcDirectory -Path $taskPaths.ArtifactsDir

$steps = New-Object System.Collections.ArrayList
for ($i = 0; $i -lt $stepDefs.Count; $i++) {
    $stepDef = $stepDefs[$i]
    $stepIndex = $i + 1
    $stepId = [string](Get-OcPropertyValue -Object $stepDef -Name 'id')
    if ([string]::IsNullOrWhiteSpace($stepId)) {
        $stepId = ('step-' + ('{0:D2}' -f $stepIndex))
    }

    $actionName = [string](Get-OcPropertyValue -Object $stepDef -Name 'action')
    if ([string]::IsNullOrWhiteSpace($actionName)) {
        Write-OcRejectionAndExit -ReasonCode 'INVALID_TASK_INPUT' -Message ('Task step action is missing at index ' + $stepIndex + '.') -TaskName $TaskName -Source $Source
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
        logPath = (Join-Path $taskPaths.TaskDir ('step-{0:D2}-output.log' -f $stepIndex))
        outputPreview = ''
        errorMessage = $null
    }
    [void]$steps.Add([pscustomobject]$stepSnapshot)
}

$ticketName = ('p{0:D2}-{1}.json' -f $Priority, $taskId)
$ticketPath = Join-Path $config.QueuePendingPath $ticketName

$task = [ordered]@{
    taskId = $taskId
    taskName = $TaskName
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
    source = $Source
    input = $inputObject
    definition = [ordered]@{
        approvalPolicy = $approvalPolicy
        stepCount = $stepDefs.Count
    }
    steps = @($steps)
}

Save-OcJson -Path $taskPaths.TaskJsonPath -Object $task
Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_created' -TaskId $taskId -Data @{
    taskName = $TaskName
    priority = $Priority
    source = $Source
}

$ticket = [ordered]@{
    taskId = $taskId
    taskName = $TaskName
    priority = $Priority
    createdUtc = [DateTime]::UtcNow.ToString('o')
}
Save-OcJson -Path $ticketPath -Object $ticket
Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_queued' -TaskId $taskId -Data @{
    ticket = $ticketName
}
Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'info' -Message ('Task queued: ' + $taskId + ' (' + $TaskName + ')')

if (-not $NoWorkerKick) {
    try {
        Invoke-OcWorkerKick -RuntimeConfig $config -Source 'enqueue'
    }
    catch {
        Write-OcRuntimeLog -LogName 'control-plane.log' -Level 'warn' -Message ('Worker kick failed for ' + $taskId + ': ' + $_.Exception.Message)
    }
}

$result = [ordered]@{
    status = 'queued'
    taskId = $taskId
    taskName = $TaskName
    priority = $Priority
    taskPath = $taskPaths.TaskJsonPath
}
$result | ConvertTo-Json -Depth 10
exit 0
