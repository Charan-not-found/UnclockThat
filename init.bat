@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   CLOCKIT - Environment & Model Setup
echo ============================================

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating Python virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create Python venv. Ensure Python 3.10+ is on PATH.
        exit /b 1
    )
) else (
    echo [1/4] Using existing .venv
)

echo [2/4] Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python packages.
    exit /b 1
)

echo [3/4] Installing frontend dependencies...
pushd frontend
call npm.cmd install
if errorlevel 1 (
    popd
    echo ERROR: Failed to install frontend npm packages.
    exit /b 1
)
popd

echo [4/4] Downloading base AI models & initializing database...
".venv\Scripts\python.exe" scripts\install_models.py
".venv\Scripts\python.exe" -c "from backend.app.database.connection import init_db; init_db()"

echo.
echo ============================================
echo   Setup complete! Run run.bat to start.
echo ============================================
endlocal
