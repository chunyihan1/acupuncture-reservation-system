@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Acupuncture Reservation System

echo ==========================================================
echo   Acupuncture Reservation ^& Treatment Record System
echo ==========================================================
echo.

set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "!PYTHON!" (
    echo [1/4] Virtual environment not found, creating it...
    where python >nul 2>nul
    if errorlevel 1 (
        where py >nul 2>nul
        if errorlevel 1 (
            echo.
            echo [ERROR] Python not found. Please install Python 3.10+ and
            echo         check "Add Python to PATH", then run this script again.
            echo.
            pause
            exit /b 1
        )
        py -3 -m venv ".venv"
    ) else (
        python -m venv ".venv"
    )
    if not exist "!PYTHON!" (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

"!PYTHON!" -c "import django" >nul 2>nul
if errorlevel 1 (
    echo [2/4] Installing dependencies...
    "!PYTHON!" -m pip install --upgrade pip --quiet
    "!PYTHON!" -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed. Check your network and retry.
        pause
        exit /b 1
    )
)

echo [3/4] Applying database migrations...
"!PYTHON!" manage.py migrate --noinput
if errorlevel 1 goto :failed

"!PYTHON!" manage.py shell -c "from clinic.models import User; raise SystemExit(0 if User.objects.exists() else 1)" >nul 2>nul
if errorlevel 1 (
    echo [4/4] First run, loading demo data...
    "!PYTHON!" manage.py seed_demo
    if errorlevel 1 goto :failed
) else (
    echo [4/4] Database already initialized, skipping demo data.
)

echo.
echo ----------------------------------------------------------
echo   URL      : http://127.0.0.1:8000
echo   Accounts : patient1 / doctor1 / admin / sysadmin
echo   Password : demo12345
echo   Close this window to stop the server.
echo ----------------------------------------------------------
echo.

start "" /min cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000/"
"!PYTHON!" manage.py runserver 127.0.0.1:8000
goto :end

:failed
echo.
echo [ERROR] Startup failed. Please check the log above.
pause

:end
endlocal
