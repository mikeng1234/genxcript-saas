@echo off
:: GenXcript Payroll — Auto-start Streamlit Server
:: Place a shortcut to this file in: shell:startup
:: (Win+R > shell:startup > paste shortcut)

title GenXcript Payroll Server
cd /d "I:\SaaS\PaySys\genxcript-saas"

echo ============================================================
echo  GenXcript Payroll Server
echo  Starting on http://localhost:8501
echo  Cloudflare Tunnel provides HTTPS access
echo ============================================================
echo.

:: Pull latest code
echo [%date% %time%] Pulling latest from GitHub...
git pull origin master

:: Start Streamlit (stays running)
echo [%date% %time%] Starting Streamlit...
streamlit run app/main.py --server.port 8501 --server.headless true --server.address 0.0.0.0
