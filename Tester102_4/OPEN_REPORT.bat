@echo off
REM ============================================================================
REM  Open Interactive HTML Report
REM  Double-click this file to open the report in your default browser
REM ============================================================================

echo.
echo ============================================================================
echo    OPENING INTERACTIVE REPORT
echo ============================================================================
echo.
echo    File: interactive_report.html
echo    Location: %~dp0
echo.
echo    Opening in default browser...
echo.

REM Open in default browser
start "" "%~dp0interactive_report.html"

echo    ✓ Report opened!
echo.
echo    If the browser didn't open, try:
echo      1. Double-click 'interactive_report.html' directly
echo      2. Right-click → Open With → Choose browser
echo.
echo ============================================================================
echo.

REM Wait 3 seconds then close
timeout /t 3 /nobreak >nul
