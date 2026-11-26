```bat
@echo off
setlocal EnableExtensions

title CLOCKIT - Environment Setup

cd /d "%~dp0"

echo.
echo ============================================
echo       CLOCKIT - Environment Setup
echo ============================================
echo.

:: ============================================
:: 1. CHECK PROJECT FILES
:: ============================================

echo [1/6] Checking project structure...

if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found.
    goto :error
)

if not exist "frontend\package.json" (
    echo ERROR: frontend\package.json not found.
    goto :error
)

if not exist "scripts\install_models.py" (
    echo ERROR: scripts\install_models.py not found.
    goto :error
)

if not exist "backend\app\database\connection.py" (
    echo ERROR: Database initialization module not found.
    goto :error
)

:: ============================================
:: 2. CHECK PYTHON
:: ============================================

echo.
echo [2/6] Checking Python installation...

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    goto :error
)

python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    goto :error
)

python --version

:: ============================================
:: 3. CREATE VIRTUAL ENVIRONMENT
:: ============================================

echo.
echo [3/6] Preparing Python environment...

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        goto :error
    )
) else (
    echo Existing virtual environment detected.
)

set "PYTHON=.venv\Scripts\python.exe"

"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    goto :error
)

"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Python dependency installation failed.
    goto :error
)

:: ============================================
:: 4. INSTALL FRONTEND
:: ============================================

echo.
echo [4/6] Preparing frontend...

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found. Install Node.js first.
    goto :error
)

pushd frontend

call npm.cmd install
if errorlevel 1 (
    popd
    echo ERROR: Frontend dependency installation failed.
    goto :error
)

popd

:: ============================================
:: 5. INSTALL AI MODELS
:: ============================================

echo.
echo [5/6] Installing AI models...

"%PYTHON%" scripts\install_models.py
if errorlevel 1 (
    echo ERROR: AI model installation failed.
    goto :error
)

:: ============================================
:: 6. INITIALIZE DATABASE
:: ============================================

echo.
echo [6/6] Initializing database...

"%PYTHON%" -c "from backend.app.database.connection import init_db; init_db()"
if errorlevel 1 (
    echo ERROR: Database initialization failed.
    goto :error
)

:: ============================================
:: SUCCESS
:: ============================================

echo.
echo ============================================
echo       CLOCKIT SETUP COMPLETE!
echo ============================================
echo.
echo Python environment : .venv
echo Frontend           : Installed
echo AI models          : Installed
echo Database           : Initialized
echo.
echo Run run.bat to start CLOCKIT.
echo.

pause
endlocal
exit /b 0

:: ============================================
:: ERROR HANDLER
:: ============================================

:error
echo.
echo ============================================
echo       CLOCKIT SETUP FAILED
echo ============================================
echo.
echo Review the error above before continuing.
echo Your existing files have not been deleted.
echo.
pause
endlocal
exit /b 1
```