# Changelog - Tester102_3

## Version 3.0 - Manual Sampling Integration (2026-10-04)

### 🎯 Major Changes

**FITUR BARU**: Manual sampling setiap 1/4 detik (250ms) dengan SPACE key - integrasi dari Tester102.

### ✨ New Features

1. **Manual Sampling System**
   - User tekan SPACE untuk sampling setiap 0.25 detik
   - SampleData class untuk menyimpan data setiap sample
   - Position tracking (accumulated dari displacement)
   - Sample counter di display panel
   - Detailed sample printout di console

2. **Data Persistence & Analysis**
   - CSV export functionality: `save_samples_to_csv()`
   - Trajectory plotting dengan matplotlib
   - Auto-save plot sebagai PNG file
   - Time-series analysis (speed, force, humans)

3. **Displacement Calculation**
   - Format: X+ = kanan, Y+ = depan
   - Interval: 0.25 detik (bukan 1 detik)
   - Displacement accumulation untuk position tracking
   - Function: `calculate_displacement(vx, vy, dt=SAMPLE_INTERVAL)`

4. **Enhanced Visualization**
   - Trajectory map dengan proxemic zones
   - Camera path visualization
   - Speed, force, dan human detection time-series
   - Sample markers pada trajectory

### 🔄 Changed

- **Sampling interval**: 1.0 detik → Manual 0.25 detik (SPACE key)
- **Movement command**: 1s duration → 0.25s duration
- **Info panel**: Menampilkan sample count dan displacement untuk 0.25s
- **Controls**: Tambahan SPACE (sample) dan S (save CSV)

### ➕ Added Components

**New Data Class**:
```python
class SampleData:
    timestamp, position, velocity
    target_direction, avoidance_direction
    current_speed, target_speed
    num_humans, closest_distance, proxemic_zone
    sfm_force, displacement
```

**New Functions**:
```python
def calculate_displacement(vx, vy, dt=SAMPLE_INTERVAL)
def save_samples_to_csv(samples, filename=None)
def plot_trajectory(samples)
```

**New Constants**:
```python
SAMPLE_INTERVAL = 0.25  # seconds (1/4 detik)
SFM_TAU = 0.5           # Time constant
SFM_MASS = 5.0          # Robot mass (kg)
```

### 🎮 Controls Updated

```
[SPACE] - Take sample (manual sampling setiap 0.25s)
[R]     - Reset statistics dan trajectory
[S]     - Save data to CSV
[Q]     - Quit dan show trajectory graph
```

### 📊 Output Files

1. **CSV Data**: `trajectory_YYYYMMDD_HHMMSS.csv`
   - Columns: sample_id, timestamp, position, velocity, direction, speed, humans, force, displacement

2. **Trajectory Plot**: `trajectory_plot_YYYYMMDD_HHMMSS.png`
   - Left: Camera trajectory map dengan proxemic zones
   - Right: Time-series (speed, force, humans detected)

### 🔧 Sample Output Format

**Console Output per Sample**:
```
──────────────────────────────────────────────────────────────────────
📍 SAMPLE #5 at t=1.25s
──────────────────────────────────────────────────────────────────────
Position: (0.234, 0.678) m
Velocity: (0.158, 0.579) m/s
Speed: 0.600 m/s | Zone: SOCIAL
Humans: 1 | Closest: 2.35m
SFM Force: (2.15, 3.78) N
Command: ↖ FWD-LEFT
Displacement (0.25s): +0.040X  +0.145Y
──────────────────────────────────────────────────────────────────────
▶ Move camera, then press SPACE for next sample
```

### 📝 Technical Details

**Integration dari Tester102**:
- ✅ Manual sampling workflow
- ✅ Position accumulation
- ✅ Data persistence (CSV)
- ✅ Trajectory visualization
- ✅ Sample-based analysis

**Perbedaan dengan Tester102**:
- Tester102: Robot digerak manual (broken robot)
- Tester102_3: Camera digeser manual (testing avoidance)
- Same sampling interval: 0.25 detik
- Same output format: X+right, Y+forward

### 🚀 Workflow

1. **Setup**: Jalankan program, camera initialize
2. **Sampling**: 
   - Geser camera secara fisik
   - Tekan SPACE untuk sample (setiap 0.25s)
   - Lihat displacement command
3. **Analysis**:
   - Tekan S untuk save CSV (optional)
   - Tekan Q untuk quit dan lihat trajectory plot
   - Review data untuk validasi algoritma

### ✅ Testing Checklist

- [x] Manual sampling dengan SPACE key
- [x] Position tracking dari displacement
- [x] CSV export functionality
- [x] Trajectory plotting
- [x] Sample data persistence
- [x] Console output formatting
- [ ] Test dengan real camera movement
- [ ] Validate trajectory accuracy

### 📚 Dependencies Added

```python
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from datetime import datetime
```

---

## Version 2.0 - Automatic Avoidance (2024-12-31)

### 🎯 Major Changes

**KONSEP BARU**: Kamera digeser MANUAL (fisik) oleh user, robot menghitung perintah menghindar OTOMATIS.

### ✨ New Features

1. **Automatic Avoidance Direction Calculation**
   - Robot menghitung arah menghindar secara otomatis
   - Menggunakan Social Force Model (SFM)
   - Kombinasi: target direction + avoidance forces
   - Output: movement command dengan X/Y components

2. **Removed Keyboard Control**
   - TIDAK ada lagi kontrol WASD
   - User hanya menggeser kamera secara FISIK
   - Program hanya menampilkan OUTPUT perintah
   - User TIDAK perlu mengikuti perintah

3. **Enhanced Visualization**
   - Cyan arrow: Target direction (goal/forward)
   - Green arrow: Command direction (avoidance output)
   - Magenta arrow: Force vectors dari humans
   - Clear distinction antara target vs command

4. **Improved Output Display**
   - Terminal output setiap 1 detik
   - Menampilkan:
     - Target direction vs Avoidance direction
     - Avoidance force magnitude
     - Movement command (direction + X/Y axis)
     - Proxemic zone dan speed

### 🔄 Changed

- **Title**: "Manual Camera Movement Tester" → "Camera-Based Avoidance Command Tester"
- **Controls**: Removed W/A/S/D, SPACE → Only R (reset) and Q (quit)
- **Position tracking**: Removed (tidak relevan untuk manual camera)
- **Trajectory trail**: Removed (tidak relevan)

### ➕ Added Functions

```python
def sfm_repulsive_force(distance, direction_x, direction_y):
    """Calculate SFM repulsive force from human"""
    
def calculate_avoidance_direction(detections, target_direction, ...):
    """Calculate avoidance direction combining target + obstacles"""
```

### 🎨 Visual Changes

**Before (v1.0)**:
- Single direction arrow (user controlled)
- Position tracking display
- Trajectory trail

**After (v2.0)**:
- Three arrows: Target (cyan) + Command (green) + Force (magenta)
- No position tracking
- Focus on avoidance behavior

### 📊 Output Format

**Terminal Output Example**:
```
────────────────────────────────────────────────────────────
⏱️  Time: 5.2s
🎯 Target: Forward | Avoidance: -15.3°
📊 Zone: SOCIAL | Speed: 0.600 m/s
🤖 MOVEMENT COMMAND (1s): ↖ FWD-LEFT
   ├─ X-axis: -0.158 m/s  (← left / right →)
   └─ Y-axis: +0.579 m/s  (↓ back / forward ↑)
👥 Humans detected: 1
⚠️  Closest: 2.35m
💨 Avoidance force: 4.23 N
────────────────────────────────────────────────────────────
```

### 🔧 Parameters

**New Parameters**:
```python
SFM_A = 5.0            # Repulsive force magnitude
SFM_B = 0.8            # Repulsive force range
SFM_WEIGHT = 0.3       # Weight for avoidance vs goal
DEFAULT_TARGET = [0.0, 1.0]  # Forward direction
```

**Removed Parameters**:
- SHOW_TRAJECTORY (not applicable)
- Position tracking variables
- Keyboard state variables

### 🎯 Use Case Change

**Before (v1.0)**:
- Testing navigasi dengan keyboard control
- Position tracking
- Trajectory visualization
- User mengontrol pergerakan

**After (v2.0)**:
- Validasi algoritma avoidance
- Perintah gerak otomatis
- User hanya membaca output
- Focus pada avoidance behavior

### 📝 Documentation Updates

- **QUICK_START.txt**: Updated untuk v2.0 concept
- **README.md**: Perlu update (coming soon)
- **INTEGRATION_SUMMARY.md**: Perlu update (coming soon)

### ✅ Testing

**Test Scenarios**:
1. No humans → Command = Target (straight)
2. Human on right → Command deviates left
3. Human on left → Command deviates right  
4. Human ahead → Strong lateral avoidance
5. Close approach (<0.45m) → STOP

### 🚀 Next Steps

- [ ] Update README.md dengan v2.0 changes
- [ ] Update INTEGRATION_SUMMARY.md
- [ ] Test dengan real camera
- [ ] Validate avoidance behavior
- [ ] Compare dengan Tester102 output

---

## Version 1.0 - Manual Control (2024-12-31)

### Initial Release

- Manual keyboard control (WASD)
- Proxemic zone speed adjustment
- Position tracking (X, Y)
- Trajectory visualization
- Movement commands dengan X/Y components

---

**Current Version**: 2.0 (Automatic Avoidance)  
**Status**: Ready for Testing  
**Author**: Brone Social Nav Team
