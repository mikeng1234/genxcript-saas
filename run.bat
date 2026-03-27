@echo off
REM ============================================================
REM  run.bat — Start GeNXcript on Python 3.12
REM  Double-click from project root.
REM ============================================================
set PY="C:\Users\Jasper Dizon\AppData\Local\Programs\Python\Python312\python.exe"
set ST="C:\Users\Jasper Dizon\AppData\Local\Programs\Python\Python312\Scripts\streamlit.exe"
cd /d %~dp0

echo.
echo  ============================================================
echo   GeNXcript Payroll  —  Python 3.12
echo  ============================================================
echo.
echo  Starting on http://localhost:8501
echo  Press Ctrl+C to stop.
echo.

%ST% run app/main.py --server.headless false --browser.gatherUsageStats false
pause
