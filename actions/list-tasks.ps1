param(
    [string]$status = '',
    [int]$limit = 20
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'bin\oc-task-list.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task list script was not found.'
}

$invokeArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $scriptPath,
    '-Limit', $limit
)
if (-not [string]::IsNullOrWhiteSpace($status)) {
    $invokeArgs += @('-Status', $status)
}

& powershell.exe @invokeArgs
exit $LASTEXITCODE