param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ActionName,

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$PayloadB64 = "",

    [Parameter(Mandatory = $false)]
    [switch]$Approved
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')
$ocConfig = Get-OcRuntimeConfig

$ActionName = $ActionName.Trim()
$PayloadB64 = $PayloadB64.Trim()

$manifestPath = $ocConfig.ManifestPath
$runFilePath  = $ocConfig.RunFilePath
$logDir       = $ocConfig.LogsPath
$logPath      = Join-Path $logDir 'action-execution.log'

$status = 'unknown'
$errorMessage = ''
$exitCode = 1
$riskLevel = ''
$approvalRequired = $false
$scriptPathFull = ''
$payloadKeys = @()

function Write-ExecutionLog {
    param(
        [string]$ActionNameValue,
        [bool]$ApprovedValue,
        [bool]$ApprovalRequiredValue,
        [string]$RiskLevelValue,
        [string]$ScriptPathValue,
        [string[]]$PayloadKeysValue,
        [string]$StatusValue,
        [int]$ExitCodeValue,
        [string]$ErrorMessageValue
    )

    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    }

    $entry = [ordered]@{
        timestampUtc      = [DateTime]::UtcNow.ToString('o')
        actionName        = $ActionNameValue
        approved          = $ApprovedValue
        approvalRequired  = $ApprovalRequiredValue
        riskLevel         = $RiskLevelValue
        scriptPath        = $ScriptPathValue
        payloadKeys       = @($PayloadKeysValue)
        status            = $StatusValue
        exitCode          = $ExitCodeValue
        errorMessage      = $ErrorMessageValue
    }

    $line = $entry | ConvertTo-Json -Compress
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

try {
    if (-not (Test-Path $manifestPath)) {
        throw "Manifest not found: $manifestPath"
    }

    if (-not (Test-Path $runFilePath)) {
        throw "Runner not found: $runFilePath"
    }

    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

    if (-not $manifest.actionsRoot) {
        throw "Manifest actionsRoot is missing."
    }

    $actionsRootFull = [System.IO.Path]::GetFullPath($manifest.actionsRoot).TrimEnd('\')

    $action = $manifest.actions | Where-Object { $_.name -eq $ActionName } | Select-Object -First 1

    if (-not $action) {
        throw "Action not found: $ActionName"
    }

    if ($action.enabled -ne $true) {
        throw "Action disabled: $ActionName"
    }

    $approvalRequired = ($action.approvalRequired -eq $true)
    $riskLevel = [string]$action.riskLevel

    if ([string]::IsNullOrWhiteSpace($riskLevel)) {
        $riskLevel = 'unknown'
    }

    if ($approvalRequired -and -not $Approved) {
        throw "Approval required: $ActionName"
    }

    if (-not $action.scriptPath) {
        throw "Action scriptPath is missing: $ActionName"
    }

    $scriptPathFull = [System.IO.Path]::GetFullPath([string]$action.scriptPath)

    if (-not ($scriptPathFull.StartsWith($actionsRootFull + '\', [System.StringComparison]::OrdinalIgnoreCase) -or $scriptPathFull.Equals($actionsRootFull, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Action script is outside actionsRoot: $scriptPathFull"
    }

    if (-not (Test-Path $scriptPathFull)) {
        throw "Action script not found: $scriptPathFull"
    }

    $declaredParams = @()
    if ($null -ne $action.parameters) {
        $declaredParams = @($action.parameters)
    }

    $payloadObject = $null

    if (-not [string]::IsNullOrWhiteSpace($PayloadB64)) {
        try {
            $payloadJson = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PayloadB64))
        }
        catch {
            throw "PayloadB64 is not valid base64."
        }

        try {
            $payloadObject = $payloadJson | ConvertFrom-Json
        }
        catch {
            throw "Payload is not valid JSON."
        }

        if ($null -ne $payloadObject) {
            $payloadKeys = @($payloadObject.PSObject.Properties.Name)
        }
    }

    $requiredParams = @($declaredParams | Where-Object { $_.required -eq $true } | ForEach-Object { [string]$_.name })
    $allowedParams  = @($declaredParams | ForEach-Object { [string]$_.name })

    if ($requiredParams.Count -gt 0 -and [string]::IsNullOrWhiteSpace($PayloadB64)) {
        throw "Payload required but missing: $ActionName"
    }

    foreach ($required in $requiredParams) {
        if ($payloadKeys -notcontains $required) {
            throw "Missing required param: $required"
        }
    }

    foreach ($key in $payloadKeys) {
        if ($allowedParams -notcontains $key) {
            throw "Unexpected param: $key"
        }
    }

    Write-Host "ACTION=$ActionName"
    Write-Host "RISK=$riskLevel"
    Write-Host "APPROVAL_REQUIRED=$approvalRequired"
    Write-Host "APPROVED=$Approved"
    Write-Host "SCRIPT=$scriptPathFull"
    Write-Host "PAYLOAD_KEYS=$([string]::Join(',', $payloadKeys))"

    & $runFilePath $scriptPathFull $PayloadB64

    if (Get-Variable LASTEXITCODE -ErrorAction SilentlyContinue) {
        $exitCode = [int]$LASTEXITCODE
    }
    else {
        $exitCode = 0
    }

    if ($exitCode -eq 0) {
        $status = 'success'
    }
    else {
        $status = 'error'
    }
}
catch {
    $status = 'error'
    $exitCode = 1
    $errorMessage = $_.Exception.Message
    throw
}
finally {
    Write-ExecutionLog `
        -ActionNameValue $ActionName `
        -ApprovedValue ([bool]$Approved) `
        -ApprovalRequiredValue ([bool]$approvalRequired) `
        -RiskLevelValue $riskLevel `
        -ScriptPathValue $scriptPathFull `
        -PayloadKeysValue @($payloadKeys) `
        -StatusValue $status `
        -ExitCodeValue $exitCode `
        -ErrorMessageValue $errorMessage
}

if ($exitCode -ne 0) {
    exit $exitCode
}
else {
    exit 0
}