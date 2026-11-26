@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found. Run init.bat first.
    exit /b 1
)

echo Starting CLOCKIT Backend (http://127.0.0.1:8000) ...
start "CLOCKIT Backend" cmd /k "cd /d "%~dp0" && ".venv\Scripts\python.exe" backend\app\main.py %*"

echo Starting CLOCKIT Frontend (http://localhost:5173) ...
start "CLOCKIT Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo CLOCKIT is launching:
echo   Frontend UI : http://localhost:5173
echo   API Docs    : http://127.0.0.1:8000/api/docs
echo.
echo Tip: Pass --resetdb to reset the database and runtime files on startup:
echo   run.bat --resetdb
endlocal
