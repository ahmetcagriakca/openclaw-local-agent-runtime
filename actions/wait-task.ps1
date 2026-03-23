param(
    [Parameter(Mandatory = $true)][string]$taskId,
    [int]$timeoutSeconds = 120,
    [int]$pollSeconds = 2
)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'oc-task-wait.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task wait script was not found.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath -TaskId $taskId -TimeoutSeconds $timeoutSeconds -PollSeconds $pollSeconds
exit $LASTEXITCODE