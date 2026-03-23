param(
    [Parameter(Mandatory = $true)][string]$taskId,
    [int]$priority = 0,
    [int]$maxRetries = 3,
    [switch]$allowCancelled
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'bin\oc-task-retry.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task retry script was not found.'
}

$invokeArgs = @(
    '-NoProfile',
    '-ExecutionPolicy', 'Bypass',
    '-File', $scriptPath,
    '-TaskId', $taskId,
    '-Priority', $priority,
    '-MaxRetries', $maxRetries
)
if ($allowCancelled) { $invokeArgs += '-AllowCancelled' }

& powershell.exe @invokeArgs
exit $LASTEXITCODE