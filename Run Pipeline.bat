@echo off
title Heat-Risk Data Pipeline Runner
color 0B

echo.
echo  ============================================================
echo   Neighbourhood Heat-Risk Communication and Outreach Planner
echo   End-to-End Pipeline Execution (Phases 2-4)
echo  ============================================================
echo.

cd /d "%~dp0"
call venv\Scripts\activate.bat

echo [1/3] Running Phase 2: Data Generation...
python -m src.data.generator
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Data Generation failed!
    pause
    exit /b %ERRORLEVEL%
)
echo.

echo [2/3] Running Phase 3: Data Preprocessing...
python -m src.data.preprocessing
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Data Preprocessing failed!
    pause
    exit /b %ERRORLEVEL%
)
echo.

echo [3/3] Running Phase 4: Baseline Prioritisation Model...
python -m src.risk.baseline
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Baseline Model failed!
    pause
    exit /b %ERRORLEVEL%
)
echo.

echo ============================================================
echo   Pipeline Execution Complete!
echo ============================================================
echo.
pause
