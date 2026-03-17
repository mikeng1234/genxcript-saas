# ============================================================
#  start_https.ps1 — Launch Streamlit + Cloudflare HTTPS tunnel
#  Usage:  .\start_https.ps1
#  Requires: cloudflared  (winget install Cloudflare.cloudflared)
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host "   GenXcript — HTTPS Dev Server" -ForegroundColor Cyan
Write-Host "  ============================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Locate cloudflared (handles PATH not refreshed yet) ───
$cfExe = "cloudflared"
$cfDefault = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (Test-Path $cfDefault) { $cfExe = $cfDefault }
elseif (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "  [ERROR] cloudflared not found. Installing via winget..." -ForegroundColor Yellow
    winget install Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
    $cfExe = $cfDefault
}

# ── 2. Start Streamlit in a new window ───────────────────────
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "  [1/2] Starting Streamlit on http://localhost:8501 ..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$root'; streamlit run app/main.py --server.headless true --browser.gatherUsageStats false"

# ── 3. Wait for Streamlit to be ready ────────────────────────
Write-Host "  [INFO] Waiting for Streamlit..." -ForegroundColor Gray
Start-Sleep -Seconds 4

# ── 4. Start Cloudflare quick tunnel, capture the HTTPS URL ──
Write-Host "  [2/2] Starting Cloudflare tunnel..." -ForegroundColor Green
Write-Host ""
Write-Host "  ============================================================" -ForegroundColor Yellow
Write-Host "   Watch for a line like:" -ForegroundColor Yellow
Write-Host "   https://xxxx-xxxx.trycloudflare.com" -ForegroundColor White
Write-Host "   Open that URL on your phone for GPS + camera support." -ForegroundColor Yellow
Write-Host "  ============================================================" -ForegroundColor Yellow
Write-Host ""

# Run tunnel (blocks until Ctrl+C)
& $cfExe tunnel --url http://localhost:8501
