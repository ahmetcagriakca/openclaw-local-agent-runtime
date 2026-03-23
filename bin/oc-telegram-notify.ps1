<#
.SYNOPSIS
    Reusable Telegram message sender. Best-effort — never crashes the caller.

.NOTES
    Location: C:\Users\AKCA\oc\bin\oc-telegram-notify.ps1
    Exit code: always 0
#>

param(
    [Parameter(Mandatory)][string]$Message,
    [string]$ParseMode = 'HTML'
)

try {
    $token = $env:OC_TELEGRAM_BOT_TOKEN
    if ([string]::IsNullOrWhiteSpace($token)) {
        try {
            $envLine = & wsl -d Ubuntu-E -- bash -c "grep '^TELEGRAM_BOT_TOKEN=' /home/akca/.openclaw/.env 2>/dev/null" 2>&1 | Out-String
            if ($envLine -match 'TELEGRAM_BOT_TOKEN=(.+)') {
                $token = $Matches[1].Trim().Trim('"', "'")
            }
        } catch { }
    }

    if ([string]::IsNullOrWhiteSpace($token)) {
        Write-Warning "[telegram-notify] No bot token available. Skipping notification."
        exit 0
    }

    $chatId = $env:OC_TELEGRAM_CHAT_ID
    if ([string]::IsNullOrWhiteSpace($chatId)) { $chatId = '8654710624' }

    $body = @{
        chat_id    = $chatId
        text       = $Message
        parse_mode = $ParseMode
    } | ConvertTo-Json -Compress

    $url = "https://api.telegram.org/bot$token/sendMessage"
    Invoke-RestMethod -Uri $url -Method Post -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 10 | Out-Null
    Write-Host "[telegram-notify] Message sent."
} catch {
    Write-Warning "[telegram-notify] Failed: $($_.Exception.Message)"
}

exit 0
