@echo off
title India Swing Scanner - Daily Update
echo ==================================================
echo   INDIA SWING SCANNER - DAILY AUTOMATED UPDATE
echo ==================================================
echo.

set VIRTUAL_ENV=
set PYTHONIOENCODING=utf-8

echo [1/2] Running Complete Market Scan (this takes ~3.5 mins)...
python scanner.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Scanner failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Fetching Daily Market News...
python news_fetcher.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] News Fetcher failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ==================================================
echo   ALL TASKS COMPLETED SUCCESSFULLY!
echo ==================================================
echo You can now refresh the dashboard.
pause
