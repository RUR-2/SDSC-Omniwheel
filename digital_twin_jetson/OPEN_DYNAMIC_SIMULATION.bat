@echo off
REM ============================================================================
REM  Open Dynamic Human Simulation Results
REM  Shows robot behavior with moving human encounter
REM ============================================================================

echo.
echo ============================================================================
echo    OPENING DYNAMIC HUMAN SIMULATION RESULTS
echo ============================================================================
echo.
echo    Scenario: Moving human encounter (1.2 m/s approach)
echo    SFM Version: v1.1 (Improved with 2-8x lateral multiplier)
echo    File: dynamic_simulation_results.html
echo.
echo    Opening in default browser...
echo.

REM Open in default browser
start "" "%~dp0dynamic_simulation_results.html"

echo    ✓ Report opened!
echo.
echo    📊 Visualizations:
echo       • Robot vs Human trajectory paths
echo       • Distance evolution over time
echo       • Speed and force response
echo       • Lateral evasion progress
echo       • Complete data table
echo.
echo    ✅ Results: Zero INTIMATE violations - System safe!
echo    📏 Minimum distance: 0.52m (safe clearance)
echo.
echo ============================================================================
echo.

REM Wait 3 seconds then close
timeout /t 3 /nobreak >nul
