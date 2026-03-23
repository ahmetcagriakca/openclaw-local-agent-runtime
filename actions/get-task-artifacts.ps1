param(
    [Parameter(Mandatory = $true)][string]$taskId
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'oc-task-artifacts.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task artifacts script was not found.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TaskId $taskId
exit $LASTEXITCODE