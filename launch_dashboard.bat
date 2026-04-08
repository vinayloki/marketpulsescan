@echo off
title India Swing Scanner - Dashboard Server
echo ==================================================
echo   INDIA SWING SCANNER - LOCAL SERVER
echo ==================================================
echo.
echo Starting local web server so the dashboard can load data files...
echo.
echo Please leave this window open while using the dashboard.
echo The dashboard will automatically open in your default browser.
echo.

start http://localhost:8000
python -m http.server 8000
