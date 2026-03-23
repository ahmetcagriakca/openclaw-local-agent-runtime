param(
    [Parameter(Mandatory=$true)]
    [string]$Filename,

    [Parameter(Mandatory=$true)]
    [string]$Content
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$actionsDir = Split-Path -Parent $PSCommandPath
$runtimeRoot = Split-Path -Parent $actionsDir
$resultsRoot = Join-Path $runtimeRoot 'results'

if ([string]::IsNullOrWhiteSpace($Filename)) {
    throw "Filename cannot be empty."
}

if (
    $Filename -match '[\\/]' -or
    [System.IO.Path]::IsPathRooted($Filename) -or
    [System.IO.Path]::GetFileName($Filename) -ne $Filename
) {
    throw "Invalid filename. Only a file name is allowed."
}

if (-not (Test-Path -LiteralPath $resultsRoot)) {
    New-Item -ItemType Directory -Force -Path $resultsRoot | Out-Null
}

$fullPath = Join-Path $resultsRoot $Filename

Set-Content -LiteralPath $fullPath -Value $Content -Encoding UTF8

Write-Output "OK:$fullPath"
exit 0