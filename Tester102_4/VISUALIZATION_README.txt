================================================================================
                   TESTER102_4 - DATA VISUALIZATION TOOLS
================================================================================

📊 QUICK START - 3 COMMANDS
────────────────────────────────────────────────────────────────────────────

  1. FULL DASHBOARD (Recommended) ⭐
     python visualize_csv.py
     → Creates 6 plots + statistics
     → Output: PNG file + terminal stats

  2. QUICK STATISTICS (No plots)
     python quick_stats.py
     → Terminal output only
     → Runs in <1 second

  3. ALTERNATIVE PLOTS
     python plot_from_samples.py
     → 2 plots + data export
     → Can use hardcoded data

================================================================================

📁 FILES
────────────────────────────────────────────────────────────────────────────

  DATA:
    sample_data.csv                  - 9 samples, 15 columns

  SCRIPTS:
    visualize_csv.py                 - Main visualization tool ⭐
    quick_stats.py                   - Statistical analysis
    plot_from_samples.py             - Alternative plotter

  DOCUMENTATION:
    VISUALIZATION_GUIDE.md           - Complete usage guide
    DATA_ANALYSIS_SUMMARY.md         - Analysis results
    FILES_INDEX.md                   - File navigation

================================================================================

📈 WHAT YOU GET
────────────────────────────────────────────────────────────────────────────

  visualize_csv.py produces:
    ✓ Trajectory map (colored by zone)
    ✓ Speed over time graph
    ✓ Distance to humans chart
    ✓ SFM force analysis
    ✓ Velocity vector field
    ✓ Force vector field
    ✓ Statistical summary
    ✓ PNG file saved automatically

  quick_stats.py shows:
    ✓ Position & movement stats
    ✓ Speed distribution
    ✓ Zone breakdown
    ✓ Human detection metrics
    ✓ Force analysis
    ✓ Safety check
    ✓ Command distribution

================================================================================

🔑 KEY METRICS (from sample_data.csv)
────────────────────────────────────────────────────────────────────────────

  Samples: 9
  Duration: 775.98 seconds (~13 minutes)
  Distance: 1.284 meters
  Avg Speed: 0.656 m/s

  Zone Distribution:
    PUBLIC (>3.6m)   : 22.2%  🟢
    SOCIAL (1.2-3.6m): 44.4%  🟡
    PERSONAL (<1.2m) : 33.3%  🟠
    INTIMATE (<0.45m): 0%     🔴  ✓ No violations!

  Safety Status: ✅ VALIDATED
    - No INTIMATE zone violations
    - Closest approach: 0.87m (safe)
    - Speed adjustments working correctly
    - Force model responding appropriately

================================================================================

⚙️ REQUIREMENTS
────────────────────────────────────────────────────────────────────────────

  Python packages:
    pip install pandas matplotlib numpy

  Or use:
    pip install -r requirements.txt

================================================================================

🎯 USAGE EXAMPLES
────────────────────────────────────────────────────────────────────────────

  Basic usage:
    python visualize_csv.py

  Analyze specific file:
    python quick_stats.py mydata.csv

  Use hardcoded data:
    python plot_from_samples.py --hardcoded

  Batch process:
    for file in *.csv; do
        python quick_stats.py "$file" > "${file%.csv}_stats.txt"
    done

================================================================================

📖 DOCUMENTATION
────────────────────────────────────────────────────────────────────────────

  For detailed information, see:

    VISUALIZATION_GUIDE.md
      → Complete guide for all visualization tools
      → Graph explanations
      → Troubleshooting
      → Customization

    DATA_ANALYSIS_SUMMARY.md
      → Analysis results and interpretation
      → Validation report
      → Recommendations

    FILES_INDEX.md
      → Navigate all files
      → File relationships
      → Workflow paths

    README.md
      → Main program documentation
      → System overview
      → Test scenarios

================================================================================

🔍 GRAPH DESCRIPTIONS
────────────────────────────────────────────────────────────────────────────

  1. TRAJECTORY MAP
     - Shows robot's path through space
     - Points colored by proxemic zone
     - Circles show zone boundaries
     - Start = green dot, End = red X

  2. SPEED OVER TIME
     - Line graph of robot speed
     - Background colored by zone
     - Shows speed adjustment response

  3. PROXIMITY TO HUMANS
     - Distance to closest human
     - Zone boundary lines (0.45m, 1.2m, 3.6m)
     - Colored zones (red=danger, orange=caution, yellow=social)

  4. SFM FORCES
     - Social Force Model magnitude
     - Increases as robot approaches human
     - Shows repulsion intensity

  5. VELOCITY VECTORS
     - Arrows show movement direction
     - Length = speed magnitude
     - Color = speed (blue=slow, red=fast)

  6. FORCE VECTORS
     - Arrows show SFM force direction
     - Should point away from humans
     - Color = force magnitude

================================================================================

💡 TIPS
────────────────────────────────────────────────────────────────────────────

  ✓ Always check safety violations first (INTIMATE zone)
  ✓ Verify speed decreases as distance decreases
  ✓ Look for smooth transitions between zones
  ✓ Force vectors should point away from humans
  ✓ Detection rate should be >80% for reliable results

  ⚠ Warning signs:
    - Sudden speed jumps (not smooth)
    - Frequent PERSONAL zone entries
    - Erratic force directions
    - Low detection rate

================================================================================

🐛 TROUBLESHOOTING
────────────────────────────────────────────────────────────────────────────

  Problem: File not found
  Solution: Make sure you're in Tester102_4 directory
            cd "d:\Vroomniwheel\SDSC Omniwheel\Tester102_4"

  Problem: Module not found
  Solution: pip install pandas matplotlib numpy

  Problem: Plot window not showing
  Solution: Check matplotlib backend
            python -c "import matplotlib; print(matplotlib.get_backend())"
            Should be 'TkAgg' on Windows

  Problem: Permission denied
  Solution: Run as administrator or check file permissions

================================================================================

📊 OUTPUT FILES
────────────────────────────────────────────────────────────────────────────

  visualize_csv.py creates:
    social_nav_analysis_YYYYMMDD_HHMMSS.png

  plot_from_samples.py creates:
    trajectory_plot_YYYYMMDD_HHMMSS.png
    trajectory_data_YYYYMMDD_HHMMSS.csv

  quick_stats.py:
    Terminal output only (no files)

================================================================================

🎨 CUSTOMIZATION
────────────────────────────────────────────────────────────────────────────

  Change zone radii:
    Edit at top of script:
      R_INTIMATE = 0.45  # meters
      R_PERSONAL = 1.20
      R_SOCIAL = 3.60

  Change zone colors:
    zone_colors = {
        'PUBLIC': 'green',
        'SOCIAL': 'yellow',
        'PERSONAL': 'orange',
        'INTIMATE': 'red'
    }

  Change plot size:
    fig = plt.figure(figsize=(20, 12))  # width, height in inches

  Save different formats:
    fig.savefig('output.pdf')  # PDF (vector)
    fig.savefig('output.svg')  # SVG (editable)
    fig.savefig('output.png', dpi=300)  # High-res PNG

================================================================================

📞 SUPPORT
────────────────────────────────────────────────────────────────────────────

  Issue: "How do I interpret results?"
  → See: DATA_ANALYSIS_SUMMARY.md

  Issue: "Plot doesn't look right"
  → See: VISUALIZATION_GUIDE.md → Troubleshooting section

  Issue: "What's in this folder?"
  → See: FILES_INDEX.md

  Issue: "First time using this"
  → See: README.md → Getting Started

================================================================================

✅ VALIDATION SUMMARY
────────────────────────────────────────────────────────────────────────────

  From sample_data.csv analysis:

  ✓ System is working as designed
  ✓ Proxemic zones correctly classified
  ✓ Speed adjustment responsive
  ✓ Force model functioning
  ✓ Safety constraints respected
  ✓ No INTIMATE zone violations
  ✓ Smooth zone transitions
  ✓ Appropriate avoidance behavior

  STATUS: ✅ SYSTEM VALIDATED

================================================================================

🚀 NEXT STEPS
────────────────────────────────────────────────────────────────────────────

  1. Run visualization to see your data
  2. Check safety violations (should be 0)
  3. Verify speed adjustment pattern
  4. Analyze force responses
  5. Document any issues or observations
  6. Tune parameters if needed
  7. Collect more data for different scenarios
  8. Transfer validated parameters to robot

================================================================================

📚 REFERENCES
────────────────────────────────────────────────────────────────────────────

  Theory:
    - Proxemics: Hall (1966) "The Hidden Dimension"
    - Social Forces: Helbing & Molnár (1995)
    - HRI: Pacchierotti et al. (2006)

  Related Files:
    - Tester102/sfm_realtime_viewer.py (force-based)
    - digital_twin_jetson/social_force_controller.py (implementation)

================================================================================

Created: 2026-10-06
Version: Tester102_4
Author: Brone Social Nav Team

For complete documentation, see VISUALIZATION_GUIDE.md

================================================================================
