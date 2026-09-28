@echo off
setlocal

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

if not exist "logs" mkdir "logs"

chcp 65001 >nul
title Match Hub - Basketball Update
set "PYTHONIOENCODING=utf-8"
set "MATCH_HUB_DAILY_CONSOLE=1"
if defined NO_PROXY (
    set "NO_PROXY=%NO_PROXY%,titan007.com,.titan007.com"
) else (
    set "NO_PROXY=titan007.com,.titan007.com"
)

"%PROJECT_ROOT%\venv\Scripts\python.exe" -u "%PROJECT_ROOT%\scripts\windows\tee_daily_maintenance.py"
exit /b %ERRORLEVEL%
