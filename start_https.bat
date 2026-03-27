@echo off
REM ============================================================
REM  start_https.bat — Launch Streamlit + Cloudflare HTTPS tunnel
REM  Usage: double-click or run from project root
REM  Requires: cloudflared installed (winget install Cloudflare.cloudflared)
REM ============================================================

echo.
echo  ============================================================
echo   GeNXcript — HTTPS Dev Server
echo  ============================================================
echo.

REM --- Locate cloudflared (default install path or PATH) ---
set CF_EXE=cloudflared
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    set CF_EXE="C:\Program Files (x86)\cloudflared\cloudflared.exe"
)
%CF_EXE% --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] cloudflared not found. Installing via winget...
    winget install Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements
    set CF_EXE="C:\Program Files (x86)\cloudflared\cloudflared.exe"
)

REM --- Start Streamlit in the background ---
echo  [1/2] Starting Streamlit on http://localhost:8501 ...
start "Streamlit" cmd /k "cd /d %~dp0 && streamlit run app/main.py --server.headless true --browser.gatherUsageStats false"

REM --- Wait a few seconds for Streamlit to start ---
echo  [INFO] Waiting for Streamlit to start...
timeout /t 4 /nobreak >nul

REM --- Start Cloudflare quick tunnel ---
echo  [2/2] Starting Cloudflare tunnel (HTTPS)...
echo.
echo  ============================================================
echo   Copy the https://xxx.trycloudflare.com URL below
echo   and open it on your phone for full GPS + camera support.
echo  ============================================================
echo.
%CF_EXE% tunnel --url http://localhost:8501

pause
