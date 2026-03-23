param(
    [Parameter(Mandatory = $true)][string]$TaskId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

Assert-OcTaskId -TaskId $TaskId
$config = Initialize-OcRuntimeLayout
$taskPaths = Get-OcTaskPaths -TaskId $TaskId -RuntimeConfig $config
$task = Read-OcJson -Path $taskPaths.TaskJsonPath
$preflightError = $null
$defPath = Join-Path $config.TaskDefsPath (([string](Get-OcPropertyValue -Object $task -Name 'taskName')) + '.json')
if (-not (Test-Path -LiteralPath $config.ActionRunnerPath)) {
    $preflightError = 'Action runner was not found.'
}
elseif (-not (Test-Path -LiteralPath $defPath)) {
    $preflightError = 'Task definition was not found.'
}
$def = $null
if (-not [string]::IsNullOrWhiteSpace($preflightError)) {
}
else {
    $def = Read-OcJson -Path $defPath
}

function Save-TaskSnapshot {
    param([Parameter(Mandatory = $true)][object]$TaskObject)
    Save-OcJson -Path $taskPaths.TaskJsonPath -Object $TaskObject
}

function Fail-Task {
    param(
        [Parameter(Mandatory = $true)][object]$TaskObject,
        [Parameter(Mandatory = $true)][string]$ErrorMessage,
        [int]$ExitCode = 1,
        [int]$StepIndex = 0
    )

    $TaskObject.status = 'failed'
    $TaskObject.finishedUtc = [DateTime]::UtcNow.ToString('o')
    $TaskObject.lastError = $ErrorMessage
    Save-TaskSnapshot -TaskObject $TaskObject
    Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_failed' -TaskId $TaskId -Data @{
        stepIndex = $StepIndex
        error = $ErrorMessage
        exitCode = $ExitCode
    }
    Write-OcRuntimeLog -LogName 'worker.log' -Level 'error' -Message ('Task failed: ' + $TaskId + ' - ' + $ErrorMessage)
    exit 1
}

if (-not [string]::IsNullOrWhiteSpace($preflightError)) {
    Fail-Task -TaskObject $task -ErrorMessage $preflightError
}

$approvalPolicy = [string](Get-OcPropertyValue -Object $def -Name 'approvalPolicy')
if ($approvalPolicy -ne 'preapproved') {
    Fail-Task -TaskObject $task -ErrorMessage 'Task definition approvalPolicy must be preapproved for this runtime.'
}

$defSteps = @((Get-OcPropertyValue -Object $def -Name 'steps'))
if ($defSteps.Count -eq 0) {
    Fail-Task -TaskObject $task -ErrorMessage 'Task definition has no steps.'
}

$task.status = 'running'
if (-not (Get-OcPropertyValue -Object $task -Name 'startedUtc')) {
    $task.startedUtc = [DateTime]::UtcNow.ToString('o')
}
$task.finishedUtc = $null
$task.lastError = $null
Save-TaskSnapshot -TaskObject $task
Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_started' -TaskId $TaskId -Data @{
    taskName = [string](Get-OcPropertyValue -Object $task -Name 'taskName')
}
Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message ('Task started: ' + $TaskId)

for ($i = 0; $i -lt $defSteps.Count; $i++) {
    $stepIndex = $i + 1
    $stepDef = $defSteps[$i]
    $actionName = [string](Get-OcPropertyValue -Object $stepDef -Name 'action')
    if ([string]::IsNullOrWhiteSpace($actionName)) {
        Fail-Task -TaskObject $task -ErrorMessage ('Task step action is missing at index ' + $stepIndex + '.') -StepIndex $stepIndex
    }

    $task.currentStepIndex = $stepIndex
    $task.currentStepId = [string](Get-OcPropertyValue -Object $task.steps[$i] -Name 'id')
    $task.steps[$i].status = 'running'
    $task.steps[$i].startedUtc = [DateTime]::UtcNow.ToString('o')
    $task.steps[$i].finishedUtc = $null
    $task.steps[$i].exitCode = $null
    $task.steps[$i].errorMessage = $null
    $task.steps[$i].outputPreview = ''
    Save-TaskSnapshot -TaskObject $task
    Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'step_started' -TaskId $TaskId -Data @{
        stepIndex = $stepIndex
        stepId = [string](Get-OcPropertyValue -Object $task.steps[$i] -Name 'id')
        action = $actionName
    }

    $payloadMap = Get-OcPropertyValue -Object $stepDef -Name 'map'
    if ($null -eq $payloadMap) {
        $payloadMap = [ordered]@{}
    }
    $payloadObject = Resolve-OcTemplateValue -Value $payloadMap -TaskObject $task -RuntimeConfig $config
    $payloadJson = $payloadObject | ConvertTo-Json -Depth 20 -Compress
    $payloadB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payloadJson))

    $stepApproved = ((Get-OcPropertyValue -Object $stepDef -Name 'approved') -eq $true)

    $stepTimeoutSec = Get-OcPropertyValue -Object $stepDef -Name 'timeoutSec'
    if ($null -eq $stepTimeoutSec -or [int]$stepTimeoutSec -le 0) {
        $stepTimeoutSec = 120
    }
    else {
        $stepTimeoutSec = [int]$stepTimeoutSec
    }

    $cancelRequested = (Get-OcPropertyValue -Object (Read-OcJson -Path $taskPaths.TaskJsonPath) -Name 'cancelRequested')
    if ($cancelRequested -eq $true) {
        $task.steps[$i].status = 'cancelled'
        $task.steps[$i].finishedUtc = [DateTime]::UtcNow.ToString('o')
        $task.steps[$i].exitCode = -1
        $task.steps[$i].errorMessage = 'Task was cancelled before this step started.'
        Save-TaskSnapshot -TaskObject $task
        Fail-Task -TaskObject $task -ErrorMessage 'Task cancelled by user.' -ExitCode -1 -StepIndex $stepIndex
    }

    $exitCode = 1
    $outputText = ''
    $stepLogPath = [string](Get-OcPropertyValue -Object $task.steps[$i] -Name 'logPath')

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = 'powershell.exe'
        $argString = '-NoProfile -ExecutionPolicy Bypass -File "' + $config.ActionRunnerPath + '" ' + $actionName + ' ' + $payloadB64
        if ($stepApproved) { $argString += ' -Approved' }
        $psi.Arguments = $argString
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true

        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
        $stderrTask = $proc.StandardError.ReadToEndAsync()
        $finished = $proc.WaitForExit($stepTimeoutSec * 1000)

        if (-not $finished) {
            try { $proc.Kill() } catch {}
            $proc.WaitForExit(5000)
            $exitCode = -2
            $outputText = 'Step timed out after ' + $stepTimeoutSec + ' seconds and was terminated.'
        }
        else {
            $exitCode = $proc.ExitCode
            $stdOut = $stdoutTask.Result
            $stdErr = $stderrTask.Result
            if (-not [string]::IsNullOrWhiteSpace($stdErr)) {
                $outputText = ($stdOut + [Environment]::NewLine + '--- STDERR ---' + [Environment]::NewLine + $stdErr).Trim()
            }
            else {
                $outputText = $stdOut.Trim()
            }
        }
    }
    catch {
        $exitCode = 1
        $outputText = $_.Exception.Message
    }

    Write-OcUtf8NoBom -Path $stepLogPath -Content $outputText

    $task.steps[$i].finishedUtc = [DateTime]::UtcNow.ToString('o')
    $task.steps[$i].exitCode = $exitCode
    $task.steps[$i].outputPreview = Get-OcSingleLinePreview -Text $outputText

    if ($exitCode -eq 0) {
        $task.steps[$i].status = 'succeeded'
        $task.steps[$i].errorMessage = $null
    }
    else {
        $task.steps[$i].status = 'failed'
        $task.steps[$i].errorMessage = Get-OcSingleLinePreview -Text $outputText
    }

    $rawArtifacts = Get-OcPropertyValue -Object $stepDef -Name 'artifacts'
    $artifactTemplates = @()
    if ($null -ne $rawArtifacts) {
        $artifactTemplates = @($rawArtifacts | Where-Object { $null -ne $_ })
    }
    if ($artifactTemplates.Count -gt 0) {
        $existingArtifacts = New-Object System.Collections.ArrayList
        foreach ($artifactPath in @((Get-OcPropertyValue -Object $task -Name 'artifactPaths'))) {
            [void]$existingArtifacts.Add([string]$artifactPath)
        }

        foreach ($artifactTemplate in $artifactTemplates) {
            $resolvedArtifactPath = Resolve-OcTemplateValue -Value $artifactTemplate -TaskObject $task -RuntimeConfig $config
            if (-not [string]::IsNullOrWhiteSpace([string]$resolvedArtifactPath) -and (Test-Path -LiteralPath $resolvedArtifactPath)) {
                if (-not $existingArtifacts.Contains([string]$resolvedArtifactPath)) {
                    [void]$existingArtifacts.Add([string]$resolvedArtifactPath)
                }
            }
        }

        $task.artifactPaths = @($existingArtifacts)
    }

    Save-TaskSnapshot -TaskObject $task
    Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'step_finished' -TaskId $TaskId -Data @{
        stepIndex = $stepIndex
        action = $actionName
        exitCode = $exitCode
    }

    if ($exitCode -ne 0) {
        $task.lastError = ('Step ' + $stepIndex + ' failed: ' + $task.steps[$i].errorMessage)
        Save-TaskSnapshot -TaskObject $task
        Fail-Task -TaskObject $task -ErrorMessage $task.lastError -ExitCode $exitCode -StepIndex $stepIndex
    }
}

$task.currentStepIndex = $defSteps.Count
$task.status = 'succeeded'
$task.finishedUtc = [DateTime]::UtcNow.ToString('o')
$task.lastError = $null
Save-TaskSnapshot -TaskObject $task
Append-OcTaskEvent -EventsPath $taskPaths.EventsPath -EventName 'task_succeeded' -TaskId $TaskId -Data @{
    stepCount = $defSteps.Count
}
Write-OcRuntimeLog -LogName 'worker.log' -Level 'info' -Message ('Task succeeded: ' + $TaskId)
exit 0