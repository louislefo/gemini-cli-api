@echo off
setlocal

echo ============================================================
echo   Launching Google Chrome with Remote Debugging (Port 9222)
echo ============================================================

set "CHROME_PATH="

if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)

if "%CHROME_PATH%"=="" (
    echo [ERROR] Could not find chrome.exe.
    echo Please specify the Chrome path manually in this script.
    pause
    exit /b 1
)

set "USER_DATA_DIR=%USERPROFILE%\.chrome_gemini_profile"

echo Chrome Path : %CHROME_PATH%
echo Profile Dir : %USER_DATA_DIR%
echo CDP Port    : 9222
echo Target URL  : https://gemini.google.com/app
echo.
echo Opening Chrome...

start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%USER_DATA_DIR%" https://gemini.google.com/app

echo.
echo Chrome started successfully.
echo Please log in to Gemini if prompted, then start the FastAPI API / CLI.
pause

