@echo off
setlocal enabledelayedexpansion
title Heat-Risk Outreach Planner — Phase 11 Ready
color 0A

echo(
echo  ============================================================
echo   Neighbourhood Heat-Risk Communication and Outreach Planner
echo   Phase 1 through Phase 11 — Production Readiness Build
echo  ============================================================
echo(

:: Ensure we are in the script's directory
cd /d "%~dp0"

:: ── STEP 1: Python ────────────────────────────────────────────────────────
echo [1/7] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo(
    echo [ERROR] Python is not installed or not in your PATH.
    echo         Please install Python 3.10+ and ensure "Add to PATH" is checked.
    echo         Download from: https://www.python.org/downloads/
    echo(
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  - Python %PYVER% found.

:: ── STEP 2: Virtual environment ───────────────────────────────────────────
echo [2/7] Checking virtual environment...
if not exist "venv\Scripts\activate.bat" (
    echo  - Virtual environment not found. Creating 'venv'...
    python -m venv venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)
echo  - Virtual environment found.

:: ── STEP 3: Activate environment ──────────────────────────────────────────
echo [3/7] Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)
echo  - Activated.

:: ── STEP 4: Dependencies ──────────────────────────────────────────────────
echo [4/7] Installing / verifying dependencies...
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found. Cannot install dependencies.
    pause
    exit /b 1
)
python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install one or more dependencies.
    echo         Check your internet connection and requirements.txt.
    pause
    exit /b 1
)
echo  - Dependencies verified.

:: ── STEP 5: Phase 11 Startup Validation ───────────────────────────────────
echo [5/7] Running Phase 11 startup validation...
set PYTHONPATH=%~dp0
python run_diagnostics.py
if %errorlevel% neq 0 (
    echo(
    echo ============================================================
    echo [ERROR] APPLICATION FAILED TO START
    echo         Critical environment issues detected - see above.
    echo         Resolve the issues listed before starting the application.
    echo ============================================================
    echo(
    pause
    exit /b 1
)
echo  - Startup validation passed.

:: ── STEP 6: Streamlit ─────────────────────────────────────────────────────
echo [6/7] Verifying Streamlit...
python -m streamlit --version >nul 2>&1
if %errorlevel% neq 0 (
    echo(
    echo ============================================================
    echo [ERROR] APPLICATION FAILED TO START
    echo         Streamlit is not installed properly.
    echo         Run: pip install streamlit
    echo ============================================================
    echo(
    pause
    exit /b 1
)
echo  - Streamlit verified.

:: ── STEP 7: Launch ────────────────────────────────────────────────────────
echo [7/7] Starting application...
echo  - Cleaning up port 8501 if occupied...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501') do (
    if not "%%a" == "0" (
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo(
echo ============================================================
echo   Application is starting in your browser.
echo   URL: http://localhost:8501
echo   Keep this window open. Press Ctrl+C to stop the server.
echo ============================================================
echo(

set PYTHONPATH=%~dp0
python -m streamlit run app\main.py

:: Keep window open if Streamlit exits unexpectedly
echo(
echo ============================================================
echo [NOTICE] Application stopped.
echo          If this was unexpected, review the output above.
echo          Press any key to close this window.
echo ============================================================
pause
