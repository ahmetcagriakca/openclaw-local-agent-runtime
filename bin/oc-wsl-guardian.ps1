<#
.SYNOPSIS
    Active guardian for WSL Ubuntu-E and OpenClaw gateway.
    Checks every 30 seconds, auto-restarts if down, sends Telegram alerts on state changes.
    Runs indefinitely (like start-wmcp-server.ps1). Stops with Ctrl+C.

.NOTES
    Location: C:\Users\AKCA\oc\bin\oc-wsl-guardian.ps1
    Replaces the passive WSLKeepAlive (sleep infinity) approach.
#>

param(
    [int]$IntervalSeconds = 30
)

$ErrorActionPreference = 'Continue'
. (Join-Path (Split-Path -Parent $PSCommandPath) 'oc-task-common.ps1')

$config = Get-OcRuntimeConfig
$repoRoot = $config.RuntimeRoot
$logsPath = $config.LogsPath
$guardianLog = 'wsl-guardian.log'
$guardianStatePath = Join-Path $logsPath 'wsl-guardian-state.json'

# --- State variables ---
$wslPreviousStatus = 'unknown'
$openclawPreviousStatus = 'unknown'
$wslRestartCount = 0
$openclawRestartCount = 0
$wslLastDownUtc = $null
$openclawLastDownUtc = $null
$startedUtc = [DateTime]::UtcNow
$cycleCount = 0
$sleepJob = $null

function Write-GuardianLog {
    param(
        [Parameter(Mandatory)][string]$Level,
        [Parameter(Mandatory)][string]$Message
    )
    Write-OcRuntimeLog -LogName $guardianLog -Level $Level -Message ('[wsl-guardian] ' + $Message)
}

# --- Resolve Telegram token (once at startup) ---
$telegramToken = $null
$telegramChatId = if ($env:OC_TELEGRAM_CHAT_ID) { $env:OC_TELEGRAM_CHAT_ID } else { '8654710624' }

if ($env:OC_TELEGRAM_BOT_TOKEN) {
    $telegramToken = $env:OC_TELEGRAM_BOT_TOKEN
} else {
    try {
        $envLine = & wsl -d Ubuntu-E -- bash -c "grep TELEGRAM_BOT_TOKEN /home/akca/.openclaw/.env 2>/dev/null" 2>&1 | Out-String
        if ($envLine -match '=(.+)$') {
            $telegramToken = $Matches[1].Trim().Trim('"', "'")
        }
    } catch { }
}

if ($telegramToken) {
    Write-GuardianLog -Level 'info' -Message 'Telegram token resolved. Notifications enabled.'
} else {
    Write-GuardianLog -Level 'warn' -Message 'No Telegram bot token found. Notifications disabled.'
}

function Send-TelegramMessage {
    param([Parameter(Mandatory)][string]$Text)
    if (-not $telegramToken) { return }
    try {
        $body = @{
            chat_id    = $telegramChatId
            text       = $Text
            parse_mode = 'HTML'
        }
        Invoke-RestMethod -Uri "https://api.telegram.org/bot$telegramToken/sendMessage" `
            -Method POST -Body ($body | ConvertTo-Json -Compress) `
            -ContentType 'application/json; charset=utf-8' -TimeoutSec 10 | Out-Null
        Write-GuardianLog -Level 'info' -Message 'Telegram notification sent.'
    } catch {
        Write-GuardianLog -Level 'warn' -Message ('Telegram send failed: ' + $_.Exception.Message)
    }
}

function Test-WslRunning {
    try {
        $out = & wsl -d Ubuntu-E -- echo WSL_OK 2>&1 | Out-String
        return ($out -match 'WSL_OK')
    } catch { return $false }
}

function Test-OpenClawRunning {
    try {
        $out = & wsl -d Ubuntu-E -- pgrep -fa openclaw 2>&1 | Out-String
        $lines = @(($out -split "`n") | Where-Object { $_.Trim().Length -gt 0 })
        return ($lines.Count -gt 0)
    } catch { return $false }
}

function Test-SleepInfinityRunning {
    try {
        $out = & wsl -d Ubuntu-E -- pgrep -f 'sleep infinity' 2>&1 | Out-String
        $lines = @(($out -split "`n") | Where-Object { $_.Trim().Length -gt 0 })
        return ($lines.Count -gt 0)
    } catch { return $false }
}

Write-GuardianLog -Level 'info' -Message ('Guardian started. Interval: ' + $IntervalSeconds + 's')
Write-Host "[wsl-guardian] Started. Checking every ${IntervalSeconds}s. Ctrl+C to stop."

try {
    while ($true) {
        $cycleCount++
        $now = [DateTime]::UtcNow
        $wslStatus = 'ok'
        $openclawStatus = 'ok'
        $sleepInfinity = $false

        # ── 1. CHECK WSL ──────────────────────────────────────────────────────
        try {
            $wslUp = Test-WslRunning
            if ($wslUp) {
                $wslStatus = 'ok'
            } else {
                $wslStatus = 'error'
                Write-GuardianLog -Level 'warn' -Message 'WSL Ubuntu-E is down. Restarting...'

                # Attempt restart (wsl -d Ubuntu-E -- echo boots the distro)
                try {
                    $restartOut = & wsl -d Ubuntu-E -- echo WSL_RESTART_OK 2>&1 | Out-String
                } catch { }
                Start-Sleep -Seconds 5

                $wslRecovered = Test-WslRunning
                if ($wslRecovered) {
                    $wslStatus = 'ok'
                    $wslRestartCount++
                    Write-GuardianLog -Level 'info' -Message 'WSL Ubuntu-E recovered after restart.'
                } else {
                    Write-GuardianLog -Level 'error' -Message 'WSL Ubuntu-E failed to recover.'
                }

                if (-not $wslLastDownUtc) { $wslLastDownUtc = $now.ToString('o') }

                # Telegram notification
                if ($wslPreviousStatus -ne 'error') {
                    $resultText = if ($wslRecovered) { [char]0x2705 + ' Recovered' } else { [char]0x274C + ' Failed to recover' }
                    Send-TelegramMessage -Text (@(
                        [char]0x1F534 + " ALERT: WSL Ubuntu-E is DOWN"
                        ""
                        "Time: $($now.ToString('yyyy-MM-dd HH:mm:ss')) UTC"
                        "Component: WSL Ubuntu-E"
                        "Status: Auto-restart attempted"
                        "Result: $resultText"
                    ) -join "`n")
                }
            }

            # Notify recovery if was down, now ok
            if ($wslPreviousStatus -eq 'error' -and $wslStatus -eq 'ok' -and $wslPreviousStatus -ne 'unknown') {
                $downtime = if ($wslLastDownUtc) {
                    [math]::Round(($now - [DateTime]::Parse($wslLastDownUtc)).TotalSeconds)
                } else { '?' }
                Send-TelegramMessage -Text (@(
                    [char]0x1F7E2 + " RECOVERED: WSL Ubuntu-E is back up"
                    ""
                    "Time: $($now.ToString('yyyy-MM-dd HH:mm:ss')) UTC"
                    "Component: WSL Ubuntu-E"
                    "Downtime: ~${downtime} seconds"
                ) -join "`n")
                $wslLastDownUtc = $null
            }
        } catch {
            $wslStatus = 'error'
            Write-GuardianLog -Level 'error' -Message ('WSL check exception: ' + $_.Exception.Message)
        }

        # ── 2. CHECK OPENCLAW (only if WSL is running) ────────────────────────
        if ($wslStatus -eq 'ok') {
            try {
                $ocUp = Test-OpenClawRunning
                if ($ocUp) {
                    $openclawStatus = 'ok'
                } else {
                    $openclawStatus = 'error'
                    Write-GuardianLog -Level 'warn' -Message 'OpenClaw is down. Restarting...'

                    try {
                        & wsl -d Ubuntu-E -- bash -c 'cd /home/akca/.openclaw && nohup openclaw start > /dev/null 2>&1 &' 2>&1 | Out-Null
                    } catch { }
                    Start-Sleep -Seconds 10

                    $ocRecovered = Test-OpenClawRunning
                    if ($ocRecovered) {
                        $openclawStatus = 'ok'
                        $openclawRestartCount++
                        Write-GuardianLog -Level 'info' -Message 'OpenClaw recovered after restart.'
                    } else {
                        Write-GuardianLog -Level 'error' -Message 'OpenClaw failed to recover.'
                    }

                    if (-not $openclawLastDownUtc) { $openclawLastDownUtc = $now.ToString('o') }

                    # Telegram notification
                    if ($openclawPreviousStatus -ne 'error') {
                        $resultText = if ($ocRecovered) { [char]0x2705 + ' Recovered' } else { [char]0x274C + ' Failed to recover' }
                        Send-TelegramMessage -Text (@(
                            [char]0x1F534 + " ALERT: OpenClaw Gateway is DOWN"
                            ""
                            "Time: $($now.ToString('yyyy-MM-dd HH:mm:ss')) UTC"
                            "Component: OpenClaw Gateway"
                            "Status: Auto-restart attempted"
                            "Result: $resultText"
                        ) -join "`n")
                    }
                }

                # Notify recovery if was down, now ok
                if ($openclawPreviousStatus -eq 'error' -and $openclawStatus -eq 'ok' -and $openclawPreviousStatus -ne 'unknown') {
                    $downtime = if ($openclawLastDownUtc) {
                        [math]::Round(($now - [DateTime]::Parse($openclawLastDownUtc)).TotalSeconds)
                    } else { '?' }
                    Send-TelegramMessage -Text (@(
                        [char]0x1F7E2 + " RECOVERED: OpenClaw Gateway is back up"
                        ""
                        "Time: $($now.ToString('yyyy-MM-dd HH:mm:ss')) UTC"
                        "Component: OpenClaw Gateway"
                        "Downtime: ~${downtime} seconds"
                    ) -join "`n")
                    $openclawLastDownUtc = $null
                }
            } catch {
                $openclawStatus = 'error'
                Write-GuardianLog -Level 'error' -Message ('OpenClaw check exception: ' + $_.Exception.Message)
            }
        } else {
            $openclawStatus = 'unknown'
        }

        # ── 3. KEEP WSL ALIVE (sleep infinity) ───────────────────────────────
        if ($wslStatus -eq 'ok') {
            try {
                $sleepInfinity = Test-SleepInfinityRunning
                if (-not $sleepInfinity) {
                    # Start sleep infinity as a background job to keep WSL alive
                    if ($null -eq $sleepJob -or $sleepJob.State -ne 'Running') {
                        $sleepJob = Start-Job -ScriptBlock { wsl -d Ubuntu-E -- sleep infinity } -Name 'WslSleepInfinity'
                        Write-GuardianLog -Level 'info' -Message 'Started sleep infinity background job.'
                    }
                    $sleepInfinity = $true
                }
            } catch {
                Write-GuardianLog -Level 'warn' -Message ('Sleep infinity check failed: ' + $_.Exception.Message)
            }
        }

        # ── 4. UPDATE STATE ──────────────────────────────────────────────────
        $wslPreviousStatus = $wslStatus
        $openclawPreviousStatus = $openclawStatus

        $uptimeSeconds = [math]::Round(($now - $startedUtc).TotalSeconds)
        $state = [ordered]@{
            timestamp      = $now.ToString('o')
            wsl            = [ordered]@{ status = $wslStatus; lastDownUtc = $wslLastDownUtc; restartCount = $wslRestartCount }
            openclaw       = [ordered]@{ status = $openclawStatus; lastDownUtc = $openclawLastDownUtc; restartCount = $openclawRestartCount }
            sleepInfinity  = $sleepInfinity
            uptimeSeconds  = $uptimeSeconds
            cycleCount     = $cycleCount
        }

        try {
            $stateJson = $state | ConvertTo-Json -Depth 10 -Compress
            [System.IO.File]::WriteAllText($guardianStatePath, $stateJson, [System.Text.UTF8Encoding]::new($false))
        } catch { }

        # ── 5. LOG ROTATION ──────────────────────────────────────────────────
        if ($cycleCount % 120 -eq 0) {
            try {
                Invoke-OcLogRotate -LogPath (Join-Path $logsPath $guardianLog) -MaxSizeBytes 5242880 -KeepCount 3
            } catch { }
        }

        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    Write-GuardianLog -Level 'info' -Message 'Guardian stopped.'
    Write-Host "[wsl-guardian] Stopped."
    if ($sleepJob) {
        Stop-Job -Job $sleepJob -ErrorAction SilentlyContinue
        Remove-Job -Job $sleepJob -Force -ErrorAction SilentlyContinue
    }
}
