# GeNXcript - Start Cloudflare Tunnel & Post URL to Discord
# Auto-restarts tunnel if it dies
$ErrorActionPreference = "SilentlyContinue"

$webhookUrl = "https://discord.com/api/webhooks/1485822463723175970/0q1bl1T-9f1J0mvsQ3MBZEjdvirvidZS1OTHTnoHrvjeCjnEs2bF0I--dS6npaHw7DMf"
$cloudflared = "$env:USERPROFILE\cloudflared.exe"
$logFile = "$env:TEMP\cloudflared_output.log"

function Post-Discord($message, $title = "GeNXcript Payroll", $color = 3447003) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $body = @{
        embeds = @(
            @{
                title = $title
                description = $message
                color = $color
                footer = @{ text = "GeNXcript Payroll System" }
                timestamp = (Get-Date).ToUniversalTime().ToString("o")
            }
        )
    } | ConvertTo-Json -Depth 5
    try {
        Invoke-RestMethod -Uri $webhookUrl -Method Post -ContentType "application/json" -Body $body
    } catch {}
}

function Start-Tunnel {
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host " GeNXcript - Cloudflare Tunnel" -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""

    # Clear old log
    if (Test-Path $logFile) { Remove-Item $logFile -Force }

    # Start cloudflared as a background process
    $process = Start-Process -FilePath $cloudflared `
        -ArgumentList "tunnel","--url","http://localhost:8501" `
        -RedirectStandardError $logFile `
        -PassThru -WindowStyle Hidden

    Write-Host "Cloudflared started (PID: $($process.Id))" -ForegroundColor Green
    Write-Host "Waiting for tunnel URL..." -ForegroundColor Yellow

    # Poll the log file for the tunnel URL (up to 30 seconds)
    $tunnelUrl = $null
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-Path $logFile) {
            $content = Get-Content $logFile -Raw
            $match = [regex]::Match($content, "https://[a-z0-9-]+\.trycloudflare\.com")
            if ($match.Success) {
                $tunnelUrl = $match.Value
                break
            }
        }
        Write-Host "." -NoNewline
    }
    Write-Host ""

    if ($tunnelUrl) {
        Write-Host ""
        Write-Host "==> TUNNEL URL: $tunnelUrl" -ForegroundColor Green
        Write-Host ""
        Post-Discord "Server is live!`n**$tunnelUrl**`n`nStarted: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`nLocal: http://localhost:8501" "GeNXcript Payroll is Live!" 3447003
    } else {
        Write-Host "Could not detect tunnel URL after 30 seconds." -ForegroundColor Red
        Post-Discord "Tunnel started but could not detect URL. Check the Beelink." "Tunnel Warning" 16776960
    }

    return $process
}

# ── Main loop — restart tunnel if it dies ──────────────────────
$restartCount = 0

while ($true) {
    $process = Start-Tunnel
    $restartCount++

    Write-Host "Tunnel is running (restart #$restartCount). Monitoring..." -ForegroundColor Cyan

    # Wait for the process to exit
    while (-not $process.HasExited) {
        Start-Sleep -Seconds 10

        # Also check if Streamlit is still alive
        $stProc = Get-Process -Name "streamlit" -ErrorAction SilentlyContinue
        $pyProc = Get-Process -Name "python" -ErrorAction SilentlyContinue
        if (-not $stProc -and -not $pyProc) {
            Write-Host "Streamlit appears to have stopped! Restarting..." -ForegroundColor Red
            Post-Discord "Streamlit process died. Auto-restarting..." "Streamlit Restart" 15158332
            Start-Process cmd -ArgumentList "/k", "cd /d `"I:\SaaS\PaySys\genxcript-saas`" && python -m streamlit run app/main.py --server.port 8501" -WindowStyle Normal
            Start-Sleep -Seconds 8
        }
    }

    Write-Host ""
    Write-Host "Tunnel died! Restarting in 5 seconds..." -ForegroundColor Red
    Post-Discord "Tunnel connection lost. Auto-restarting... (restart #$($restartCount + 1))" "Tunnel Reconnecting" 15158332
    Start-Sleep -Seconds 5
}
