@echo off
title Shopo Robo - Auth Server
echo.
echo ============================================
echo   Shopo Robo - Starting Auth Server...
echo ============================================
echo.

cd /d "c:\Users\dell\Downloads\antigravity"

REM Check if Flask is installed
python -c "import flask" 2>nul
if %errorlevel% neq 0 (
    echo [SETUP] Installing Flask...
    pip install flask werkzeug
    echo.
)

REM Check if server is already running on port 5000
netstat -ano | findstr ":5000" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Shopo Robo Auth Server is already running on port 5000.
    echo Opening browser at http://127.0.0.1:5000/auth/ ...
    start http://127.0.0.1:5000/auth/
    exit /b 0
)

REM Launch browser in 2 seconds in the background
start /min cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5000/auth/"

REM Start the Flask auth server
echo [START] Server starting at http://127.0.0.1:5000/auth/
echo Press CTRL+C to stop the server.
echo.
python "c:\Users\dell\Downloads\antigravity\server\app.py"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Server stopped with an error.
    pause
)
