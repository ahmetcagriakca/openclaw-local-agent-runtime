param(
    [Parameter(Mandatory=$true)]
    [string]$ScriptPath,

    [string]$ArgsBase64 = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')
$ocConfig = Get-OcRuntimeConfig

$actionsRootFull = [System.IO.Path]::GetFullPath($ocConfig.ActionsPath).TrimEnd('\')

$clean = $ScriptPath
$clean = $clean -replace "`r",""
$clean = $clean -replace "`n",""
$clean = $clean.Trim()

if ($clean.StartsWith('"') -and $clean.EndsWith('"')) {
    $clean = $clean.Trim('"')
}
if ($clean.StartsWith("'") -and $clean.EndsWith("'")) {
    $clean = $clean.Trim("'")
}

if ($clean -match '^/mnt/([a-zA-Z])/(.*)$') {
    $drive = $matches[1].ToUpper()
    $rest  = $matches[2] -replace '/', '\'
    $clean = "${drive}:\$rest"
}

if (-not (Test-Path -LiteralPath $clean)) {
    throw "Script not found: $clean"
}

$resolved = (Resolve-Path -LiteralPath $clean).Path
$resolvedFull = [System.IO.Path]::GetFullPath($resolved)

if (-not ($resolvedFull.StartsWith($actionsRootFull + '\', [System.StringComparison]::OrdinalIgnoreCase) -or $resolvedFull.Equals($actionsRootFull, [System.StringComparison]::OrdinalIgnoreCase))) {
    throw "Script is outside oc-actions: $resolvedFull"
}

$argParts = @()

if (-not [string]::IsNullOrWhiteSpace($ArgsBase64)) {
    try {
        $json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($ArgsBase64))
    }
    catch {
        throw "ArgsBase64 is not valid base64."
    }

    try {
        $argsObj = $json | ConvertFrom-Json
    }
    catch {
        throw "Args payload is not valid JSON."
    }

    if ($null -eq $argsObj) {
        throw "Args payload resolved to null."
    }

    foreach ($prop in $argsObj.PSObject.Properties) {
        $name = [string]$prop.Name

        if ($name -notmatch '^[A-Za-z][A-Za-z0-9_]*$') {
            throw "Invalid parameter name: $name"
        }

        if ($null -eq $prop.Value) {
            $value = ''
        }
        elseif ($prop.Value -is [System.Collections.IEnumerable] -and -not ($prop.Value -is [string])) {
            throw "Complex parameter values are not allowed: $name"
        }
        elseif ($prop.Value -is [pscustomobject] -or $prop.Value -is [hashtable]) {
            throw "Complex parameter values are not allowed: $name"
        }
        else {
            $value = [string]$prop.Value
        }

        $escaped = $value.Replace("'", "''")
        $argParts += "-$name '$escaped'"
    }
}

$command = "& '$resolvedFull'"
if ($argParts.Count -gt 0) {
    $command += " " + ($argParts -join " ")
}

& $ocConfig.WmcpCallPath -Command $command