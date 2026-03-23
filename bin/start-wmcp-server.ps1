<#
.SYNOPSIS
    Start windows-mcp server via mcpo on localhost:8001.
    Runs in-process (no child PowerShell window).
    Idempotent: if already healthy, exits cleanly.

.NOTES
    Location: C:\Users\AKCA\oc\bin\start-wmcp-server.ps1
#>

param(
    [string]$UvPath     = "E:\ai\windows-agent\.venv\Scripts\uv.exe",
    [int]$Port          = 8001,
    [string]$ApiKey     = "local-mcp-12345"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $UvPath)) {
    Write-Error "[wmcp] uv not found: $UvPath"
    exit 2
}

function Test-WmcpHealth {
    try {
        $r = Invoke-RestMethod "http://localhost:$Port/openapi.json" -TimeoutSec 5 -ErrorAction Stop
        return ($r.info.title -eq "windows-mcp")
    } catch { return $false }
}

# --- Already running? ---
if (Test-WmcpHealth) {
    Write-Host "[wmcp] Already healthy on port $Port"
    exit 0
}

# --- Kill stale ---
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        $_.CommandLine -like "*mcpo*--port*$Port*" -or
        $_.CommandLine -like "*windows-mcp*"
    )
} | ForEach-Object {
    Write-Host "[wmcp] Stopping stale PID $($_.ProcessId)"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

# --- Run in-process (blocks until server exits) ---
Write-Host "[wmcp] Starting server on port $Port (in-process)..."
& $UvPath tool run mcpo --port $Port --api-key $ApiKey -- $UvPath tool run windows-mcp
