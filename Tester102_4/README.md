# Manual Camera Movement Tester dengan Proxemic Speed Control

## 📋 Deskripsi

Program ini dibuat khusus untuk menguji pergerakan robot fisik yang sedang mengalami kerusakan dengan menggunakan **simulasi pergerakan kamera secara manual**. Kamera digerakkan dengan keyboard (arah WASD) dengan **kecepatan awal 1 m/s** menuju target tujuan. Sistem secara otomatis menyesuaikan kecepatan berdasarkan **proxemic zone** yang terdeteksi menggunakan:

- **Intel RealSense Depth Camera** (D435/D455)
- **YOLO11** untuk deteksi manusia
- **Proxemic theory** untuk zone classification

## 🎯 Tujuan Program

Karena robot fisik (Roda) sedang dalam perbaikan, program ini memungkinkan:

1. **Testing navigasi** tanpa robot fisik
2. **Validasi proxemic zone behavior** secara real-time
3. **Analisis speed adjustment** berdasarkan jarak manusia
4. **Output perintah gerakan** untuk 1 detik ke depan
5. **Visualisasi 2D trajectory** dan movement commands

## 🔧 Fitur Utama

### 1. Manual Movement Control
- **Keyboard WASD** untuk kontrol arah
- **Toggle mode**: tekan sekali untuk ON/OFF
- **8 arah pergerakan**: N, NE, E, SE, S, SW, W, NW
- **Base speed**: 1.0 m/s (dapat disesuaikan)

### 2. Proxemic Zone Speed Adjustment

| Zone | Distance | Speed | % Base | Color |
|------|----------|-------|--------|-------|
| INTIMATE | < 0.45m | 0.0 m/s | 0% | 🔴 Red |
| PERSONAL | 0.45-1.2m | 0.3 m/s | 30% | 🟠 Orange |
| SOCIAL | 1.2-3.6m | 0.6 m/s | 60% | 🟡 Yellow |
| PUBLIC | > 3.6m | 1.0 m/s | 100% | 🟢 Green |

### 3. Output Display (1 Second Interval)

Program menampilkan perintah pergerakan robot untuk **1 detik ke depan**:

```
Movement Command (1s): ↗ FWD-RIGHT
  X-axis: +0.424 m/s  |  Y-axis: +0.424 m/s
```

**Komponen output:**
- **Direction arrow**: ↑↗→↘↓↙←↖ (8 arah) atau ⊙ (stop)
- **Direction name**: FORWARD, FWD-RIGHT, RIGHT, dll.
- **X-axis component**: kecepatan horizontal (-left, +right)
- **Y-axis component**: kecepatan vertikal (-backward, +forward)
- **Speed magnitude**: √(Vx² + Vy²)

### 4. Real-time Visualization

- **Proxemic zone circles** (red/orange/yellow)
- **Human detection boxes** dengan zone color
- **Robot position indicator** (blue circle)
- **Movement trajectory trail** (red line)
- **Info panel** dengan statistik lengkap

## 🚀 Installation

### Requirements

**Hardware:**
- Intel RealSense D435 atau D455
- USB 3.0 port
- Pencahayaan yang baik

**Software:**
- Python 3.6+
- PyRealSense2
- Ultralytics YOLO
- OpenCV
- NumPy

### Install Dependencies

```bash
pip3 install pyrealsense2 ultralytics opencv-python numpy
```

### Download YOLO Model

```bash
cd d:\Dummy1102\Tester102_3

# Download YOLO11n model
# From: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11n.pt
```

### Test Camera

```bash
realsense-viewer
```

## 📖 Cara Penggunaan

### 1. Jalankan Program

```bash
python3 manual_camera_movement_tester.py
```

### 2. Keyboard Controls

| Key | Fungsi |
|-----|--------|
| `W` | Move forward (Y+) |
| `S` | Move backward (Y-) |
| `A` | Move left (X-) |
| `D` | Move right (X+) |
| `SPACE` | Stop & Reset position |
| `Q` | Quit program |

**Catatan:** Keys adalah toggle (tekan sekali ON, tekan lagi OFF)

### 3. Membaca Output

**Info Panel Display:**

```
MANUAL CAMERA MOVEMENT TESTER
Time: 15.3s
Robot Position: X=2.45m, Y=3.12m
Target Direction: 45.0°
Current Speed: 0.600 m/s (60%)
Proxemic Zone: SOCIAL (closest: 2.35m)
Movement Command (1s): ↗ FWD-RIGHT
  X-axis: +0.424 m/s  |  Y-axis: +0.424 m/s
────────────────────────────────────────
Detected Humans: 2
  Human 1: 2.35m | SOCIAL
  Human 2: 4.12m | PUBLIC
```

**Interpretasi:**
- Robot telah bergerak `2.45m` ke kanan, `3.12m` ke depan dari origin
- Target arah: `45°` (diagonal kanan-depan)
- Kecepatan saat ini: `0.6 m/s` (60% dari base speed karena SOCIAL zone)
- Ada 2 manusia terdeteksi
- Manusia terdekat: `2.35m` di SOCIAL zone
- **Perintah untuk 1 detik ke depan**: gerak `FWD-RIGHT` (diagonal)
- **Komponen velocity**: X = `+0.424 m/s`, Y = `+0.424 m/s`

### 4. Coordinate System (2D)

```
        Y+ (Forward)
         ↑
         │
         │
   X- ←──●──→ X+
  (Left) │ (Right)
         │
         ↓
       Y- (Backward)
```

- **Origin (0,0)**: starting position saat program dimulai
- **X-axis**: horizontal movement (-left, +right)
- **Y-axis**: vertical movement (-backward, +forward)

**Contoh:**
- `[W]` → X=0.0, Y=+1.0 (pure forward)
- `[D]` → X=+1.0, Y=0.0 (pure right)
- `[W]+[D]` → X=+0.707, Y=+0.707 (diagonal 45°)

## 🧪 Test Scenarios

### Test 1: Straight Line Approach

**Setup:**
- Letakkan 1 manusia di depan kamera (3-4 meter)

**Procedure:**
1. Tekan `[W]` untuk move forward
2. Observe speed transitions

**Expected Results:**
- Start (>3.6m): speed = 1.0 m/s (PUBLIC zone - green)
- At 3.6m: speed drops to 0.6 m/s (SOCIAL zone - yellow)
- At 1.2m: speed drops to 0.3 m/s (PERSONAL zone - orange)
- At 0.45m: speed = 0.0 m/s (INTIMATE zone - red, STOP!)

**Validation:**
✓ Robot berhenti sebelum menabrak manusia

---

### Test 2: Side Movement

**Setup:**
- Manusia di sisi kiri kamera

**Procedure:**
1. Tekan `[D]` untuk move right (menjauhi manusia)

**Expected Results:**
- Speed tetap 1.0 m/s (tidak ada obstacle di depan)
- X-axis: positive (+1.0)
- Y-axis: zero (0.0)
- Trajectory bergerak horizontal ke kanan

**Validation:**
✓ Robot menghindari manusia dengan lateral movement

---

### Test 3: Diagonal Approach

**Setup:**
- Manusia di posisi diagonal kanan-depan (2-3m)

**Procedure:**
1. Tekan `[W]` + `[D]` untuk move diagonal

**Expected Results:**
- Direction: 45° (FWD-RIGHT)
- X-axis ≈ Y-axis ≈ +0.707 (normalized)
- Speed adjusts as distance decreases
- Display shows ↗ arrow

**Validation:**
✓ Robot bergerak diagonal, speed menurun saat mendekati

---

### Test 4: Multiple Humans

**Setup:**
- 2 manusia: satu di 2m (SOCIAL), satu di 5m (PUBLIC)

**Procedure:**
1. Tekan `[W]` untuk move forward

**Expected Results:**
- Speed determined by CLOSEST human (2m)
- Zone: SOCIAL
- Speed: 0.6 m/s (60%)
- Display shows both humans

**Validation:**
✓ Robot responds to closest threat

---

### Test 5: Emergency Stop

**Setup:**
- Robot moving forward ([W] pressed)

**Procedure:**
1. Manusia tiba-tiba masuk ke zona <0.45m

**Expected Results:**
- Speed immediately drops to 0.0 m/s
- Zone changes to RED (INTIMATE)
- Command display: "⊙ STOP"
- Bounding box merah di manusia

**Validation:**
✓ Emergency brake activated successfully

## 📊 Understanding the Output

### Movement Command Format

```
Movement Command (1s): [Arrow] [Direction]
  X-axis: [+/-]X.XXX m/s  |  Y-axis: [+/-]X.XXX m/s
```

**Direction Arrows:**

| Arrow | Direction | Angle |
|-------|-----------|-------|
| ↑ | FORWARD | 90° |
| ↗ | FWD-RIGHT | 45° |
| → | RIGHT | 0° |
| ↘ | BACK-RIGHT | -45° |
| ↓ | BACKWARD | -90° |
| ↙ | BACK-LEFT | -135° |
| ← | LEFT | 180° |
| ↖ | FWD-LEFT | 135° |
| ⊙ | STOP | - |

### Axis Components

**X-axis Component:**
- **Range**: -1.0 to +1.0 m/s
- **Negative value**: robot bergerak ke KIRI
- **Positive value**: robot bergerak ke KANAN
- **Zero**: tidak ada gerakan horizontal

**Y-axis Component:**
- **Range**: -1.0 to +1.0 m/s
- **Negative value**: robot bergerak MUNDUR
- **Positive value**: robot bergerak MAJU
- **Zero**: tidak ada gerakan vertikal

**Speed Magnitude:**
- **Formula**: `speed = √(Vx² + Vy²)`
- **Range**: 0.0 to 1.0 m/s
- **Adjusted by**: proxemic zone of closest human

### Example Output Analysis

```
Movement Command (1s): → RIGHT
  X-axis: +1.000 m/s  |  Y-axis: +0.000 m/s
```

**Analysis:**
- Pure horizontal movement (right)
- No vertical component
- Full speed (1.0 m/s - PUBLIC zone)
- Robot will move 1.0m to the right in 1 second

---

```
Movement Command (1s): ↗ FWD-RIGHT
  X-axis: +0.424 m/s  |  Y-axis: +0.424 m/s
```

**Analysis:**
- Diagonal movement (45°)
- Equal X and Y components
- Speed magnitude: √(0.424² + 0.424²) = 0.6 m/s
- SOCIAL zone (60% speed)
- Robot will move 0.6m diagonally in 1 second

---

```
Movement Command (1s): ⊙ STOP
  X-axis: +0.000 m/s  |  Y-axis: +0.000 m/s
```

**Analysis:**
- No movement
- INTIMATE zone (<0.45m)
- Emergency stop activated
- Robot stays in current position

## ⚙️ Parameter Tuning

Edit bagian Configuration di `manual_camera_movement_tester.py`:

```python
# Proxemic zones (meters)
R_INTIMATE = 0.45      # Emergency stop zone
R_PERSONAL = 1.20      # Slow down zone  
R_SOCIAL = 3.60        # Caution zone

# Speed parameters (m/s)
BASE_SPEED = 1.0       # Initial speed
SPEED_INTIMATE = 0.0   # Stop
SPEED_PERSONAL = 0.3   # 30% speed
SPEED_SOCIAL = 0.6     # 60% speed
SPEED_PUBLIC = 1.0     # 100% speed

# Update interval (seconds)
UPDATE_INTERVAL = 1.0  # Command update rate
```

**Contoh penyesuaian untuk robot lebih konservatif:**

```python
R_PERSONAL = 1.5       # Slow down lebih awal
SPEED_SOCIAL = 0.4     # Lebih pelan di social zone
SPEED_PERSONAL = 0.2   # Lebih pelan di personal zone
```

## 🔍 Troubleshooting

### Camera not detected
```bash
# Check devices
rs-enumerate-devices

# Check permissions (Linux)
sudo usermod -a -G video $USER

# Try different USB 3.0 port
```

### No humans detected
- Improve lighting
- Stand 1-5 meters from camera
- Check YOLO confidence threshold (default: 0.5)
- Verify camera is not blocked

### Speed not adjusting
- Pastikan manusia terdeteksi (check bounding box)
- Verify depth reading (should be 0.1-10m)
- Check proxemic zone thresholds
- Ensure closest human calculation is correct

### Position drift
- Normal behavior (velocity integration over time)
- Press `[SPACE]` to reset position
- Adjust `dt` calculation if drift is excessive

### Low FPS / Lag
- Close other applications
- Reduce camera resolution
- Use GPU for YOLO inference (requires CUDA)
- Lower YOLO confidence threshold

## 📈 Data Collection & Analysis

### Visualization Tools 📊

Program ini dilengkapi dengan tool visualisasi untuk analisis data:

#### 1. **visualize_csv.py** ⭐ RECOMMENDED
Membuat dashboard visualisasi lengkap dengan 6 grafik:
- Trajectory map dengan zona proksemik
- Speed over time (colored by zone)
- Distance to closest human
- SFM force magnitude
- Velocity vector field
- Force vector field

```bash
python visualize_csv.py
```

#### 2. **quick_stats.py**
Analisis statistik cepat tanpa grafik:
```bash
python quick_stats.py sample_data.csv
```

Output:
- Position & movement statistics
- Speed distribution
- Zone distribution
- Human detection metrics
- Force analysis
- Safety violation check

#### 3. **plot_from_samples.py**
Plotter alternatif dengan data hardcoded atau CSV:
```bash
# Gunakan CSV
python plot_from_samples.py

# Gunakan data hardcoded
python plot_from_samples.py --hardcoded
```

📖 **Panduan lengkap**: Lihat `VISUALIZATION_GUIDE.md`

### Data Format

Data sample dapat di-export ke CSV dengan format:

```csv
Sample,Time_s,Position_X_m,Position_Y_m,Velocity_X_ms,Velocity_Y_ms,Speed_ms,Zone,Humans_Count,Closest_Distance_m,SFM_Force_X_N,SFM_Force_Y_N,Command,Displacement_X_m,Displacement_Y_m
1,228.57,-0.054,0.244,-0.217,0.976,1.000,PUBLIC,1,3.71,-0.01,-0.05,FORWARD,-0.054,0.244
```

### Metrics to Record

1. **Response Time**: waktu dari zone change sampai speed change
2. **Transition Smoothness**: apakah speed berubah smooth atau jerky
3. **Position Accuracy**: bandingkan dengan ground truth measurement
4. **Detection Reliability**: % frame dengan human terdeteksi correctly
5. **Zone Classification**: validasi distance thresholds

### Sample Data Table

| Time(s) | Pos_X | Pos_Y | Speed | Zone | Human_Dist | Vx | Vy |
|---------|-------|-------|-------|------|------------|-------|-------|
| 0.0 | 0.00 | 0.00 | 1.00 | PUBLIC | inf | 0.000 | +1.000 |
| 1.0 | 0.00 | 1.00 | 1.00 | PUBLIC | 4.50 | 0.000 | +1.000 |
| 2.0 | 0.00 | 2.00 | 1.00 | PUBLIC | 3.50 | 0.000 | +1.000 |
| 3.0 | 0.00 | 2.90 | 0.60 | SOCIAL | 2.60 | 0.000 | +0.600 |
| 4.0 | 0.00 | 3.50 | 0.60 | SOCIAL | 2.00 | 0.000 | +0.600 |
| 5.0 | 0.00 | 4.08 | 0.30 | PERSONAL | 1.15 | 0.000 | +0.300 |

## 📚 Perbandingan dengan Tester102

| Feature | Tester102 | Tester102_3 |
|---------|-----------|-------------|
| **Movement Control** | Automatic (SFM) | Manual (keyboard) |
| **Speed Source** | Force calculation | Proxemic zones |
| **Target/Goal** | None (pure avoidance) | User-defined direction |
| **Position Tracking** | No | Yes (X, Y in meters) |
| **Trajectory Display** | No | Yes (red trail) |
| **Output Format** | Terminal text | Panel + visualization |
| **Use Case** | View robot reaction | Navigation testing |
| **Robot Involvement** | None (camera only) | Simulated movement |

**Kapan menggunakan:**
- **Tester102**: untuk melihat REAKSI robot terhadap manusia (force-based)
- **Tester102_3**: untuk TEST NAVIGASI dengan speed adjustment (proxemic-based)

## 🎓 Next Steps

Setelah testing dengan program ini:

1. ✅ **Validasi behavior**: pastikan speed adjustment sesuai ekspektasi
2. ✅ **Parameter tuning**: adjust proxemic zones dan speeds
3. ✅ **Collect data**: record metrics untuk analisis
4. ✅ **Document findings**: catat edge cases dan anomalies
5. ✅ **Robot integration**: transfer parameters ke robot fisik saat sudah diperbaiki

## 📞 References

### Related Files

- `Tester102/sfm_realtime_viewer.py` - Pure SFM avoidance (force-based)
- `digital_twin_jetson/social_force_controller.py` - Robot implementation
- `digital_twin_jetson/SOCIAL_NAVIGATION_INTEGRATION.md` - Theory & documentation

### Theory

- **Proxemics**: Hall, E.T. (1966) "The Hidden Dimension"
- **Social Force Model**: Helbing & Molnár (1995)
- **Human-Robot Interaction**: Pacchierotti et al. (2006)
- **Social Navigation**: Kruse et al. (2013)

## 📝 Version History

- **v1.0** (2024-12-31)
  - Initial release
  - Manual keyboard control (WASD)
  - Proxemic zone speed adjustment
  - Real-time visualization
  - 2D position tracking
  - Movement command output (1s interval)
  - X and Y axis components

## ✨ Author

**Brone Social Nav Team**  
Created for testing robot navigation during physical robot maintenance.

---

**Status**: ✅ Ready for Testing  
**Hardware**: Intel RealSense D435/D455  
**Base Speed**: 1.0 m/s  
**Update Rate**: 1.0 second

Happy Testing! 🎥🤖🚀
