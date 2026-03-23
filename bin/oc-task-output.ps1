param(
    [Parameter(Mandatory = $true)][string]$TaskId,
    [int]$StepIndex = 0
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

Assert-OcTaskId -TaskId $TaskId
$config = Initialize-OcRuntimeLayout
$taskPaths = Get-OcTaskPaths -TaskId $TaskId -RuntimeConfig $config
$task = Read-OcJson -Path $taskPaths.TaskJsonPath
$steps = @((Get-OcPropertyValue -Object $task -Name 'steps'))
if ($steps.Count -eq 0) {
    throw 'Task has no steps.'
}

if ($StepIndex -gt 0) {
    if ($StepIndex -gt $steps.Count) {
        throw 'StepIndex is out of range.'
    }

    $step = $steps[$StepIndex - 1]
    $logPath = [string](Get-OcPropertyValue -Object $step -Name 'logPath')
    if (-not (Test-Path -LiteralPath $logPath)) {
        throw 'Step output log was not found.'
    }

    Get-Content -Raw -LiteralPath $logPath
    exit 0
}

$sections = New-Object System.Collections.ArrayList
foreach ($step in $steps) {
    $logPath = [string](Get-OcPropertyValue -Object $step -Name 'logPath')
    $title = ('===== STEP ' + [string](Get-OcPropertyValue -Object $step -Name 'index') + ' / ' + [string](Get-OcPropertyValue -Object $step -Name 'action') + ' =====')
    $body = ''
    if (Test-Path -LiteralPath $logPath) {
        $body = Get-Content -Raw -LiteralPath $logPath
    }
    [void]$sections.Add($title)
    [void]$sections.Add($body)
}

[string]::Join([Environment]::NewLine, [string[]]$sections.ToArray())
exit 0