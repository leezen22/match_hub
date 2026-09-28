@echo off
setlocal

set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

if not exist "logs" mkdir "logs"

"%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\scripts\daily_maintenance.py" >> "%PROJECT_ROOT%\logs\daily_maintenance.out.log" 2>> "%PROJECT_ROOT%\logs\daily_maintenance.err.log"
exit /b %ERRORLEVEL%
