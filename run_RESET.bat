@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: .venv not found. Run init.bat first.
    exit /b 1
)

echo Starting PROMETHEUS-X Backend (http://127.0.0.1:8000) ...
start "PROMETHEUS-X Backend" cmd /k "cd /d "%~dp0" && ".venv\Scripts\python.exe" backend\app\main.py --resetdb%*"

echo Starting PROMETHEUS-X Frontend (http://localhost:5173) ...
start "PROMETHEUS-X Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo Starting PROMETHEUS-X Simulator UI (http://127.0.0.1:5180) ...
start "PROMETHEUS-X Simulator" cmd /k "cd /d "%~dp0" && ".venv\Scripts\python.exe" simulator\web_simulator.py --port 5180"

echo.
echo PROMETHEUS-X is launching:
echo   Frontend UI  : http://localhost:5173
echo   Simulator UI : http://127.0.0.1:5180
echo   API Docs     : http://127.0.0.1:8000/api/docs
echo.
echo Tip: Pass --resetdb to reset the database and runtime files on startup:
echo   run.bat --resetdb
endlocal
