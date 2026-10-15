@echo off
title Shopo Robo - AI Inventory Store Launcher
echo Starting Shopo Robo Server...

:: Start local web server in background if not already running on 8080
netstat -ano | find "8080" >nul 2>&1
if %errorlevel% neq 0 (
    start /min python -m http.server 8080
    timeout /t 2 /nobreak >nul
)

:: Find Chrome Path
set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist %CHROME_PATH% set CHROME_PATH="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist %CHROME_PATH% set CHROME_PATH="%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

echo Launching Shopo Robo in Chrome App Mode...
if exist %CHROME_PATH% (
    start "" %CHROME_PATH% --app="http://localhost:8080/index.html" --window-size=1280,820
) else (
    start http://localhost:8080/index.html
)
exit
