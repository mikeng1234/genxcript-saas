@echo off
title GeNXcript - Cloudflare Tunnel
echo ============================================================
echo  GeNXcript Payroll - Cloudflare Tunnel
echo ============================================================
echo.
echo Starting tunnel to localhost:8501...
echo The public URL will appear below.
echo.
"%USERPROFILE%\cloudflared.exe" tunnel --url http://localhost:8501
pause
