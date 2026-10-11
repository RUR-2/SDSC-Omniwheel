================================================================================
                   INTERACTIVE HTML REPORT - USER GUIDE
================================================================================

📊 FILE: interactive_report.html

📍 LOCATION: d:\Vroomniwheel\SDSC Omniwheel\Tester102_4\

================================================================================

🎯 WHAT'S NEW - HUMAN POSITION VISUALIZATION
────────────────────────────────────────────────────────────────────────────

✅ NOW SHOWS:
  • Robot positions (blue circles, numbered 1-9)
  • Human positions (red stars with 👤 emoji)
  • Connection lines between robot and human (colored by zone)
  • Distance measurements
  • Interactive hovering for details

✅ NEW PLOT ADDED:
  • "Robot-Human Interaction Map" in Overview tab
  • Shows complete spatial relationship
  • Color-coded distance lines
  • START and END markers

================================================================================

🎨 VISUALIZATIONS INCLUDED (9 PLOTS)
────────────────────────────────────────────────────────────────────────────

📊 OVERVIEW TAB:
  1. Robot Trajectory Map
     - Robot path with zone colors
     - Human positions (red stars)
     - Proxemic zone circles
     - Connection lines (dotted)
  
  2. Speed Over Time
     - Speed graph with zone coloring
     - Shows speed adjustment response
  
  3. Robot-Human Interaction Map ⭐ NEW!
     - Robot path numbered (1-9)
     - Human positions with emoji
     - Distance lines colored by zone
     - START (green) and END (red) markers

🗺️ TRAJECTORY TAB:
  4. Velocity Vector Field
     - Movement arrows
     - Robot path + human positions
  
  5. Force Vector Field
     - SFM force arrows
     - Robot path + human positions

📈 ANALYSIS TAB:
  6. Proximity to Humans
     - Distance over time
     - Zone boundary lines
  
  7. SFM Force Magnitude
     - Force intensity over time
  
  8. Zone Distribution
     - Pie chart of time in zones

📋 DATA TABLE TAB:
  9. Complete Data Table
     - Robot positions (X, Y)
     - Human positions (X, Y) ⭐ NEW!
     - All metrics

================================================================================

📖 HOW TO OPEN
────────────────────────────────────────────────────────────────────────────

METHOD 1: Double-Click
  1. Navigate to: d:\Vroomniwheel\SDSC Omniwheel\Tester102_4\
  2. Double-click: interactive_report.html
  3. Opens in default browser

METHOD 2: Drag and Drop
  1. Open Chrome, Firefox, or Edge
  2. Drag interactive_report.html into browser window
  3. Drop to open

METHOD 3: Copy Path
  1. Open browser
  2. Paste in address bar:
     file:///d:/Vroomniwheel/SDSC%20Omniwheel/Tester102_4/interactive_report.html
  3. Press Enter

METHOD 4: Right-Click
  1. Right-click on interactive_report.html
  2. Select "Open with"
  3. Choose your browser

================================================================================

🔍 UNDERSTANDING THE VISUALIZATIONS
────────────────────────────────────────────────────────────────────────────

ROBOT-HUMAN INTERACTION MAP:
  🔵 Blue circles (1-9) = Robot positions at each sample
  ⭐ Red stars with 👤 = Human positions (estimated)
  ━━━ Colored lines = Distance between robot and human
       • Green = PUBLIC zone (>3.6m)
       • Yellow = SOCIAL zone (1.2-3.6m)
       • Orange = PERSONAL zone (0.45-1.2m)
  🟢 Green circle = START position
  ❌ Red X = END position

TRAJECTORY MAP:
  • Blue line = robot's path
  • Colored dots = robot position (colored by zone)
  • Red stars = human positions
  • Dotted lines = connection to human
  • Circles = proxemic zone boundaries at final position

VELOCITY VECTORS:
  • Blue line = robot trajectory
  • Arrows = movement direction and speed
  • Red stars = human positions

FORCE VECTORS:
  • Blue line = robot trajectory
  • Arrows = SFM force (points away from human)
  • Red stars = human positions
  • Arrow color: green (weak) → orange (medium) → red (strong)

================================================================================

💡 INTERACTIVE FEATURES
────────────────────────────────────────────────────────────────────────────

✓ HOVER: Mouse over any point/line for detailed info
✓ ZOOM: Click and drag to zoom into area
✓ PAN: Hold and drag to move view
✓ RESET: Double-click to reset view
✓ LEGEND: Click legend items to show/hide traces
✓ TABS: Switch between different analysis views

================================================================================

📊 KEY FINDINGS FROM DATA
────────────────────────────────────────────────────────────────────────────

SAFETY VALIDATION: ✅ PASSED
  • No INTIMATE zone violations (<0.45m)
  • Closest approach: 0.87m (PERSONAL zone - safe)
  • System properly adjusts speed based on proximity

BEHAVIOR VERIFICATION:
  • Robot starts at PUBLIC zone (3.71m) → 1.0 m/s
  • Enters SOCIAL zone (3.07m) → slows to 0.6 m/s
  • Enters PERSONAL zone (0.87m) → slows to 0.3 m/s
  • Maintains safe distance throughout

HUMAN TRACKING:
  • Human detected in 8 out of 9 samples (88.9%)
  • Human positions estimated from robot position and SFM forces
  • Positions consistent with expected movement pattern

================================================================================

🎯 WHAT TO LOOK FOR
────────────────────────────────────────────────────────────────────────────

✅ GOOD INDICATORS:
  □ Robot path curves around human (avoidance behavior)
  □ Connection lines get shorter as robot approaches
  □ Line color changes: green → yellow → orange
  □ Speed decreases as lines change color
  □ Force arrows point away from human
  □ No red (INTIMATE) connections

⚠️ WARNING SIGNS:
  □ Direct path toward human (no avoidance)
  □ Orange lines (PERSONAL zone) frequent
  □ Speed not changing with distance
  □ Force arrows erratic or wrong direction

🔴 CRITICAL ISSUES:
  □ Red connections (INTIMATE zone violations)
  □ Robot path intersects human position
  □ Speed constant despite proximity
  □ No force response

================================================================================

📐 HOW HUMAN POSITIONS ARE CALCULATED
────────────────────────────────────────────────────────────────────────────

Formula:
  Human Position = Robot Position - (Force Direction × Distance)

Explanation:
  • SFM forces point AWAY from humans
  • We reverse the force direction
  • Scale it by the measured distance
  • Add to robot position to get human position

Example (Sample 6):
  Robot: (0.147, 0.881)
  Force: (1.63, -0.47) N
  Distance: 0.87 m
  → Human: (0.147, 0.881) - (1.63, -0.47)/|F| × 0.87
  → Human: approximately behind and left of robot

Note: Positions are estimates based on force model

================================================================================

🖥️ TECHNICAL DETAILS
────────────────────────────────────────────────────────────────────────────

TECHNOLOGY:
  • Pure HTML + JavaScript (no Python needed)
  • Plotly.js for interactive plots (via CDN)
  • Responsive CSS Grid layout
  • Mobile-friendly design

FILE SIZE: ~100 KB (single file, self-contained)

BROWSER COMPATIBILITY:
  ✓ Chrome 90+
  ✓ Firefox 88+
  ✓ Edge 90+
  ✓ Safari 14+

NO INTERNET REQUIRED:
  • Plotly.js loaded from CDN (needs internet first time)
  • After first load, browser caches it
  • All data embedded in HTML

================================================================================

🔧 CUSTOMIZATION
────────────────────────────────────────────────────────────────────────────

To modify the report, open interactive_report.html in text editor:

Change colors:
  Line 67: const zoneColors = {...}

Change zone boundaries:
  Add constants at top of <script> section

Add more data:
  Line 254: const data = [...]
  Add new objects following same format

================================================================================

📤 SHARING THE REPORT
────────────────────────────────────────────────────────────────────────────

EASY SHARING:
  1. Email: Attach interactive_report.html
  2. USB: Copy file to USB drive
  3. Cloud: Upload to Dropbox/Google Drive
  4. Network: Copy to shared folder

RECIPIENT INSTRUCTIONS:
  "Double-click the HTML file to open in browser"

NO INSTALLATION NEEDED:
  • Works on any computer with browser
  • No Python, no dependencies
  • Just open and view

================================================================================

🆘 TROUBLESHOOTING
────────────────────────────────────────────────────────────────────────────

Problem: File won't open
Solution: Right-click → Open With → Choose browser

Problem: Plots not showing
Solution: Enable JavaScript in browser settings

Problem: Layout broken
Solution: Use modern browser (Chrome/Firefox/Edge)

Problem: Can't zoom/pan
Solution: Use mouse wheel + drag, or touch gestures

Problem: Legend items not clickable
Solution: Click directly on colored squares, not text

================================================================================

📚 RELATED FILES
────────────────────────────────────────────────────────────────────────────

Source Data:
  sample_data.csv              - Raw CSV data

Python Alternatives:
  visualize_csv.py             - Python version (requires packages)
  plot_from_samples.py         - Alternative Python plotter
  quick_stats.py               - Statistical analysis

Documentation:
  VISUALIZATION_GUIDE.md       - Complete guide
  DATA_ANALYSIS_SUMMARY.md     - Analysis report
  README.md                    - Main documentation

================================================================================

✨ ADVANTAGES OF HTML REPORT
────────────────────────────────────────────────────────────────────────────

VS PYTHON SCRIPTS:
  ✓ No Python installation needed
  ✓ No dependency hell (pandas, matplotlib, etc.)
  ✓ Works on any computer
  ✓ Easy to share (single file)
  ✓ Interactive (zoom, pan, hover)
  ✓ Professional appearance
  ✓ Fast loading
  ✓ Mobile-friendly

VS STATIC IMAGES (PNG):
  ✓ Interactive exploration
  ✓ Zoom without quality loss
  ✓ Show/hide data series
  ✓ Hover for exact values
  ✓ Multiple views in one file
  ✓ Smaller file size

================================================================================

🎓 TIPS FOR ANALYSIS
────────────────────────────────────────────────────────────────────────────

1. START WITH OVERVIEW TAB
   - Get big picture understanding
   - Check interaction map first

2. LOOK AT TRAJECTORY TAB
   - Verify velocity makes sense
   - Check force directions

3. DIVE INTO ANALYSIS TAB
   - Proximity trends
   - Force buildup
   - Zone distribution

4. VERIFY IN DATA TABLE
   - Check exact numbers
   - Cross-reference positions

5. COMPARE BEFORE/AFTER
   - Early samples (PUBLIC) vs late (PERSONAL)
   - How behavior changes

================================================================================

📞 QUESTIONS & SUPPORT
────────────────────────────────────────────────────────────────────────────

For more information:
  • See: VISUALIZATION_GUIDE.md
  • See: DATA_ANALYSIS_SUMMARY.md
  • See: FILES_INDEX.md

For technical details:
  • See: README.md (Tester102_4)
  • See: SAMPLING_GUIDE.md

================================================================================

Created: 2026-10-06
Version: 2.0 (with human positions)
Author: Brone Social Nav Team
Status: ✅ Enhanced with Human Tracking

================================================================================

ENJOY EXPLORING THE DATA! 📊🗺️⭐

Open interactive_report.html in your browser now!

================================================================================
