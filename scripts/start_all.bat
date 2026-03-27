@echo off
title GeNXcript - Start All
echo ============================================================
echo  GeNXcript Payroll - Starting Server + Tunnel
echo ============================================================
echo.

:: Start Streamlit in a new window
start "GeNXcript Streamlit" cmd /k "cd /d "I:\SaaS\PaySys\genxcript-saas" && python -m streamlit run app/main.py --server.port 8501"

:: Wait 5 seconds for Streamlit to start
echo Waiting 5 seconds for Streamlit to start...
timeout /t 5 /nobreak >nul

:: Start tunnel + post URL to Discord via PowerShell script
echo Starting Cloudflare Tunnel + Discord notification...
start "GeNXcript Tunnel" powershell -ExecutionPolicy Bypass -File "%~dp0start_tunnel_discord.ps1"

echo.
echo Both windows started!
echo - Streamlit: http://localhost:8501
echo - Check Discord for the public tunnel URL
echo.
pause
