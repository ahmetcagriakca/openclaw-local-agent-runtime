param(
    [Parameter(Mandatory = $true)][string]$taskId,
    [int]$stepIndex = 0
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'bin\oc-task-output.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task output script was not found.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TaskId $taskId -StepIndex $stepIndex
exit $LASTEXITCODE