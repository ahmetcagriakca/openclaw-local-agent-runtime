Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')
$ocConfig = Get-OcRuntimeConfig

Write-Host "STEP=manifest_validate"
$validatePath = Join-Path $ocConfig.BinPath 'oc-validate-manifest.ps1'
pwsh.exe -NoLogo -NoProfile -File $validatePath

Write-Host "STEP=list_actions_json"
$listJsonPath = Join-Path $ocConfig.BinPath 'oc-list-actions-json.ps1'
$null = pwsh.exe -NoLogo -NoProfile -File $listJsonPath | Out-String

Write-Host "STEP=check_required_files"
$required = @(
    $ocConfig.RunFilePath,
    $ocConfig.ActionRunnerPath,
    $ocConfig.WmcpCallPath,
    $ocConfig.ManifestPath,
    (Join-Path $ocConfig.ActionsPath 'notepad-test.ps1'),
    (Join-Path $ocConfig.ActionsPath 'open-app.ps1'),
    (Join-Path $ocConfig.ActionsPath 'write-file.ps1')
)

foreach ($p in $required) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Missing required file: $p"
    }
    Write-Host "OK FILE=$p"
}

Write-Host "STEP=write_file_smoke"
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('{"filename":"healthcheck.txt","content":"OC_HEALTHCHECK_OK"}'))
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $ocConfig.ActionRunnerPath write_file $payload -Approved

$healthFile = Join-Path $ocConfig.ResultsPath 'healthcheck.txt'
if (-not (Test-Path -LiteralPath $healthFile)) {
    throw "Healthcheck output file missing: $healthFile"
}

$content = Get-Content -LiteralPath $healthFile -Raw
if ($content.Trim() -ne 'OC_HEALTHCHECK_OK') {
    throw "Healthcheck output content mismatch."
}

Write-Host "HEALTHCHECK OK"