@echo off
setlocal
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
  "venv\Scripts\python.exe" web_main.py %*
) else (
  python web_main.py %*
)
pause
