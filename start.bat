@echo off
rem Windows launcher. Usage: start.bat [port]
cd /d "%~dp0"
if "%~1"=="" (
    python server.py 16261
) else (
    python server.py %1
)
