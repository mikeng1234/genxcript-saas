@echo off
title GenXcript - Cloudflare Tunnel
echo ============================================================
echo  GenXcript Payroll - Cloudflare Tunnel
echo ============================================================
echo.
echo Starting tunnel to localhost:8501...
echo The public URL will appear below.
echo.
"%USERPROFILE%\cloudflared.exe" tunnel --url http://localhost:8501
pause
