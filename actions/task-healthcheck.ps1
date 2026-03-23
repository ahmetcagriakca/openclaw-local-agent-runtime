$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$scriptPath = Join-Path $base 'bin\oc-task-health.ps1'
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw 'Task health script was not found.'
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath
exit $LASTEXITCODE