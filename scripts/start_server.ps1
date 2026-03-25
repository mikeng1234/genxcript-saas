# GenXcript Payroll — Auto-start Streamlit Server (PowerShell version)
# To auto-start on boot, create a scheduled task:
#   schtasks /create /tn "GenXcript Server" /tr "powershell -File I:\SaaS\PaySys\genxcript-saas\scripts\start_server.ps1" /sc onlogon /rl highest

$ErrorActionPreference = "Continue"
Set-Location "I:\SaaS\PaySys\genxcript-saas"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " GenXcript Payroll Server" -ForegroundColor Cyan
Write-Host " $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan

# Pull latest
Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Pulling latest from GitHub..." -ForegroundColor Yellow
git pull origin master 2>&1

# Start Streamlit
Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Starting Streamlit on port 8501..." -ForegroundColor Green
streamlit run app/main.py --server.port 8501 --server.headless true --server.address 0.0.0.0
