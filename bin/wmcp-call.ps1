# wmcp-call.ps1
# INTERNAL RUNTIME TRANSPORT ONLY.
# This script is an internal MCP HTTP transport layer used by oc-run-file.ps1.
# It is NOT part of the external task-centric integration surface.
# External callers (Bridge, Vezir, Telegram) must use canonical task APIs
# (enqueue_task, get_task, etc.) — never this script directly.
#
# Phase 1.5-A frozen decision: external integration surface is task-centric.
# Raw action invocation is forbidden as an external integration path.
param(
    [Parameter(Mandatory=$true)]
    [string]$Command,

    [int]$Timeout = 30,

    [string]$BaseUrl = "http://localhost:8001",

    [string]$ApiKey
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve API key: parameter > environment variable > hardcoded localhost fallback.
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = $env:OC_MCP_API_KEY
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $ApiKey = 'local-mcp-12345'
}

$headers = @{
    Authorization = "Bearer $ApiKey"
}

$body = @{
    command = $Command
    timeout = $Timeout
} | ConvertTo-Json

try {
    $resp = Invoke-RestMethod `
        -Uri "$BaseUrl/PowerShell" `
        -Method Post `
        -Headers $headers `
        -ContentType "application/json" `
        -Body $body
}
catch {
    Write-Error "MCP HTTP request failed: $($_.Exception.Message)"
    exit 1
}

if ($resp -is [string]) {
    Write-Output $resp

    $m = [regex]::Match($resp, '(?mi)^\s*Status Code:\s*(-?\d+)\s*$')
    if (-not $m.Success) {
        Write-Error "MCP text response does not include a parsable status code."
        exit 1
    }

    exit ([int]$m.Groups[1].Value)
}

$resp | Write-Output

$statusCode = $null

if ($null -ne $resp.PSObject.Properties['Status Code']) {
    $statusCode = [int]$resp.'Status Code'
}
elseif ($null -ne $resp.PSObject.Properties['StatusCode']) {
    $statusCode = [int]$resp.StatusCode
}
elseif ($null -ne $resp.PSObject.Properties['statusCode']) {
    $statusCode = [int]$resp.statusCode
}
else {
    Write-Error "MCP response does not include a status code."
    exit 1
}

exit $statusCode
