@echo off
REM ============================================================================
REM  Open Before vs After Improvement Comparison
REM  Double-click to view interactive comparison charts
REM ============================================================================

echo.
echo ============================================================================
echo    OPENING IMPROVEMENT COMPARISON REPORT
echo ============================================================================
echo.
echo    File: improvement_comparison.html
echo    Type: Interactive Comparison Charts
echo    Location: %~dp0
echo.
echo    Opening in default browser...
echo.

REM Open in default browser
start "" "%~dp0improvement_comparison.html"

echo    ✓ Report opened!
echo.
echo    📊 5 Interactive Charts Available:
echo       1. Trajectory Comparison (Before vs After)
echo       2. Lateral Deviation Analysis
echo       3. Speed Reduction Comparison
echo       4. Key Metrics Dashboard
echo       5. Response Timeline
echo.
echo ============================================================================
echo.

REM Wait 3 seconds then close
timeout /t 3 /nobreak >nul
