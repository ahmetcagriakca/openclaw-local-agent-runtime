param(
    [Parameter(Mandatory = $true)][string]$taskId
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'bin\oc-task-cancel.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task cancel script was not found.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TaskId $taskId
exit $LASTEXITCODE