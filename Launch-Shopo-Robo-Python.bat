@echo off
title Shopo Robo - AI Inventory Store
cd /d "c:\Users\dell\Downloads\antigravity"

echo ===================================================
echo       Launching Shopo Robo AI Assistant...
echo ===================================================
echo Starting Native Python App with Voice AI...

python "c:\Users\dell\Downloads\antigravity\python_app\main.py"

if %errorlevel% neq 0 (
    echo.
    echo Application stopped. Press any key to close...
    pause
)
