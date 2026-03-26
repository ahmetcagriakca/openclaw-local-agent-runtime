<#
.SYNOPSIS
    Minimal HTTP server for the Vezir System Monitor dashboard.
    Serves dashboard/index.html and health API endpoints.
    Runs in-process, stops with Ctrl+C.

.NOTES
    Location: C:\Users\AKCA\oc\bin\start-dashboard.ps1
#>

param(
    [int]$Port = 8002
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$dashboardHtml = Join-Path $repoRoot 'dashboard' 'index.html'
$snapshotPath = Join-Path $repoRoot 'logs' 'health-snapshot.json'
$historyPath = Join-Path $repoRoot 'logs' 'health-history.jsonl'

if (-not (Test-Path -LiteralPath $dashboardHtml)) {
    Write-Error "[dashboard] dashboard/index.html not found at $dashboardHtml"
    exit 1
}

$prefix = "http://localhost:$Port/"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($prefix)

try {
    $listener.Start()
    Write-Host "[dashboard] Listening on $prefix (Ctrl+C to stop)"

    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        $resp = $ctx.Response
        $path = $req.Url.AbsolutePath

        try {
            $contentType = 'application/json'
            $body = $null

            switch ($path) {
                '/' {
                    $contentType = 'text/html; charset=utf-8'
                    $body = [System.IO.File]::ReadAllBytes($dashboardHtml)
                }
                '/api/health' {
                    if (Test-Path -LiteralPath $snapshotPath) {
                        $body = [System.IO.File]::ReadAllBytes($snapshotPath)
                    } else {
                        $resp.StatusCode = 404
                        $body = [System.Text.Encoding]::UTF8.GetBytes('{"error":"no snapshot yet"}')
                    }
                }
                '/api/history' {
                    $contentType = 'text/plain; charset=utf-8'
                    if (Test-Path -LiteralPath $historyPath) {
                        $body = [System.IO.File]::ReadAllBytes($historyPath)
                    } else {
                        $body = [System.Text.Encoding]::UTF8.GetBytes('')
                    }
                }
                default {
                    $resp.StatusCode = 404
                    $body = [System.Text.Encoding]::UTF8.GetBytes('{"error":"not found"}')
                }
            }

            $resp.ContentType = $contentType
            $resp.Headers.Add('Access-Control-Allow-Origin', '*')
            if ($null -ne $body) {
                $resp.ContentLength64 = $body.Length
                $resp.OutputStream.Write($body, 0, $body.Length)
            }
        } catch {
            Write-Warning "[dashboard] Request error: $_"
        } finally {
            $resp.Close()
        }
    }
} finally {
    $listener.Stop()
    Write-Host "[dashboard] Stopped."
}
