@echo off
REM ============================================================
REM  start_ngrok.bat — Launch Streamlit + ngrok HTTPS tunnel
REM  Usage: double-click or run from project root
REM ============================================================

set NGROK_EXE="C:\Users\Jasper Dizon\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

echo.
echo  ============================================================
echo   GeNXcript — HTTPS Dev Server (ngrok)
echo  ============================================================
echo.

REM --- Check authtoken is configured ---
%NGROK_EXE% config check >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] ngrok authtoken not configured!
    echo.
    echo  Steps:
    echo   1. Go to https://dashboard.ngrok.com/signup  ^(free^)
    echo   2. After signing in, go to:
    echo      https://dashboard.ngrok.com/get-started/your-authtoken
    echo   3. Copy your token, then run:
    echo      %NGROK_EXE% config add-authtoken YOUR_TOKEN_HERE
    echo   4. Re-run this script.
    echo.
    pause
    exit /b 1
)

REM --- Start Streamlit in background ---
echo  [1/2] Starting Streamlit on http://localhost:8501 ...
start "Streamlit" cmd /k "cd /d %~dp0 && "C:\Users\Jasper Dizon\AppData\Local\Programs\Python\Python312\Scripts\streamlit.exe" run app/main.py --server.headless true --browser.gatherUsageStats false"

echo  [INFO] Waiting for Streamlit to start...
timeout /t 4 /nobreak >nul

REM --- Start ngrok tunnel ---
echo  [2/2] Starting ngrok tunnel (HTTPS)...
echo.
echo  ============================================================
echo   Your permanent HTTPS URL:
echo   https://malarian-kimberlee-postnuptially.ngrok-free.dev
echo   Open that URL on your phone for GPS + camera support.
echo  ============================================================
echo.
%NGROK_EXE% http 8501 --domain=malarian-kimberlee-postnuptially.ngrok-free.dev

pause
