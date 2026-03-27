# push_and_shutdown.ps1
# Commits all changes, pushes to GitHub, then shuts down.

Set-Location "I:\SaaS\PaySys\genxcript-saas"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  GeNXcript - Push to GitHub and Shutdown" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Show current status
Write-Host "Changed files:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Check if there's anything to commit
$changes = git status --porcelain
if (-not $changes) {
    Write-Host "Nothing to commit. Working tree is clean." -ForegroundColor Green
    Write-Host ""
} else {
    # Ask for commit message
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    $defaultMsg = "[$timestamp] [Beelink] Auto-save changes"
    Write-Host "Commit message (press Enter for default):" -ForegroundColor Yellow
    Write-Host "  Default: $defaultMsg" -ForegroundColor Gray
    $msg = Read-Host "Message"
    if ([string]::IsNullOrWhiteSpace($msg)) { $msg = $defaultMsg }

    Write-Host ""
    Write-Host "Staging all changes..." -ForegroundColor Yellow
    git add .

    Write-Host "Committing..." -ForegroundColor Yellow
    git commit -m $msg
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Commit failed. Aborting." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
    git push
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed. Aborting shutdown." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }

    # Update ACTIVITY.md
    $activityLine = "$timestamp [Beelink] Pushed to GitHub: $msg"
    Add-Content -Path "I:\SaaS\PaySys\genxcript-saas\ACTIVITY.md" -Value $activityLine

    Write-Host ""
    Write-Host "Push successful!" -ForegroundColor Green
}

# Countdown shutdown
Write-Host ""
Write-Host "Shutting down in 15 seconds... Press Ctrl+C to cancel." -ForegroundColor Magenta
for ($i = 15; $i -gt 0; $i--) {
    Write-Host "`r  $i seconds remaining..." -NoNewline -ForegroundColor Magenta
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "Shutting down now." -ForegroundColor Red
shutdown /s /t 0
