@echo off
REM ============================================================
REM  archive_snapshots.bat — Quarterly DTR Snapshot Archiver
REM  Double-click to run. Keeps last 30 days in Supabase;
REM  downloads older files to archives\dtr-snapshots\YYYY-QN\
REM  then deletes them from Supabase.
REM ============================================================

cd /d %~dp0

echo.
echo  ============================================================
echo   GenXcript — DTR Snapshot Archiver
echo  ============================================================
echo.
echo  This will:
echo    1. Download all DTR snapshots older than 30 days
echo    2. Save them to archives\dtr-snapshots\YYYY-QN\
echo    3. Delete them from Supabase Storage
echo.
echo  Press Ctrl+C NOW to cancel, or...
pause

echo.
echo  Running archiver...
echo.
python scripts/archive_snapshots.py --days 30

echo.
echo  Done! Press any key to close.
pause
