@echo off
REM ============================================================================
REM  Open Detailed Critical Scenario Report
REM  Double-click this file to open the detailed analysis
REM ============================================================================

echo.
echo ============================================================================
echo    OPENING DETAILED CRITICAL SCENARIO ANALYSIS
echo ============================================================================
echo.
echo    File: detailed_report.html
echo    Scenario: INTIMATE Zone Violations
echo    Location: %~dp0
echo.
echo    Opening in default browser...
echo.

REM Open in default browser
start "" "%~dp0detailed_report.html"

echo    ✓ Report opened!
echo.
echo    ⚠ WARNING: This report shows INTIMATE zone violations
echo    Review findings carefully for safety analysis
echo.
echo ============================================================================
echo.

REM Wait 3 seconds then close
timeout /t 3 /nobreak >nul
