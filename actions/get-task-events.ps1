param(
    [Parameter(Mandatory = $true)][string]$taskId,
    [int]$limit = 100
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'oc-task-events.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task events script was not found.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TaskId $taskId -Limit $limit
exit $LASTEXITCODE