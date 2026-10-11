# Tester102 - Summary

## ✅ Complete Package Created!

Tester102 v2.0 (Clean rebuild) - Manual sampling tester untuk robot omniwheel yang **rusak**.

---

## 📦 Package Contents

```
Tester102/
├── manual_sampling_tester.py  # Main program (complete)
├── requirements.txt           # Dependencies
├── README.md                  # Documentation
├── launch.sh                  # Launcher script
└── SUMMARY.md                 # This file
```

---

## 🎯 Key Features

### ✅ Sesuai Requirement
- ✅ Robot digerakkan **manual** (diangkat/dipindahkan)
- ✅ User input dengan **SPACE** untuk sampling
- ✅ Sample interval: **1/4 detik (0.25s)**
- ✅ Social Force Model calculation
- ✅ Kecepatan awal: **1.0 m/s**
- ✅ Input: **RealSense + YOLO** untuk deteksi manusia
- ✅ Output: **Grafik** trajectory + human detection

### ✅ Display Features (Sesuai Gambar Referensi)
- ✅ **Proxemic zone circles**: Red (intimate), Orange (personal), Yellow (social)
- ✅ **Green arrow**: Movement command direction
- ✅ **Info panel** with:
  - Time
  - Target Direction (goal)
  - **Avoidance Direction** (orange) - avoiding humans
  - **Avoidance Force** - SFM force magnitude
  - **Current Speed** (green) - m/s dan %
  - **Proxemic Zone** (colored) - dengan jarak terdekat
  - **Movement Command (0.25s)** - FWD/LEFT/RIGHT/etc
  - **Displacement**: `+0.4X +0.5Y` format
    - **X+ = kanan (right)**
    - **Y+ = depan (forward)**

### ✅ Displacement Calculation
Format output seperti requirement:
```
+0.239X +0.550Y  (X+=right, Y+=forward)
```
- Konversi dari internal coordinate (vx=forward, vy=left)
- Ke robot frame: X+=right, Y+=forward
- Display di panel bawah dengan warna hijau

---

## 🚀 Usage

```bash
# 1. Install dependencies
cd Tester102
pip install -r requirements.txt

# 2. Run
bash launch.sh
# atau
python3 manual_sampling_tester.py

# 3. Controls
# SPACE - Ambil sample
# Q - Quit dan tampilkan grafik
# R - Reset trajectory
# S - Save ke CSV
```

---

## 📊 Output Example

### Terminal
```
======================================================================
Sample #1 at t=0.00s
======================================================================
Position: (0.000, 0.000) m
Velocity: (1.000, 0.000) m/s
Humans detected: 2

Humans:
  ID1: (1.50, -0.30)m, dist=1.53m, zone=PERSONAL
  ID2: (2.80, 0.50)m, dist=2.84m, zone=SOCIAL

SFM Forces:
  Goal: (5.00, 0.00) N
  Repulsive: (8.23, 2.15) N
  Total: (13.23, 2.15) N

Next velocity: (0.882, 0.107) m/s
Displacement (0.25s): -0.027X +0.221Y
======================================================================
```

### Display Panel (Like Reference Image)
```
CAMERA-BASED AVOIDANCE COMMAND TESTER
Time: 742.1s
Target Direction: 90.0?? (Forward/Goal)
Avoidance Direction: 65.5?? (avoiding humans)    [ORANGE]
Avoidance Force: 0.52 N
Current Speed: 0.600 m/s (60%)                   [GREEN]
Proxemic Zone: SOCIAL (closest: 1.82m)           [YELLOW]
Movement Command (0.25s): FWD-RIGHT              [GREEN]
  +0.249X  +0.546Y  (X+=right, Y+=forward)       [GREEN]
```

### CSV Output
```csv
sample_id,timestamp,robot_x,robot_y,robot_vx,robot_vy,sfm_fx,sfm_fy,next_vx,next_vy,disp_x_right,disp_y_forward,num_humans
1,0.00,0.000,0.000,1.000,0.000,13.23,2.15,0.882,0.107,-0.027,0.221,2
2,0.25,0.220,0.027,0.882,0.107,14.63,2.39,0.809,0.142,-0.035,0.202,2
...
```

### Graph Output
- **Plot 1**: Trajectory map dengan robot path, human detection, dan proxemic zones
- **Plot 2**: Time series - velocity, force, dan human count

---

## ⚙️ Technical Specs

| Parameter | Value |
|-----------|-------|
| Sample Interval | 0.25 seconds |
| Initial Velocity | 1.0 m/s |
| SFM V0 | 1.0 m/s |
| SFM Tau | 0.5 s |
| SFM A (Repulsion) | 5.0 N |
| SFM B (Range) | 0.8 m |
| SFM Mass | 5.0 kg |
| Max Speed | 0.6 m/s |
| Intimate Zone | 0.45 m |
| Personal Zone | 1.20 m |
| Social Zone | 3.60 m |
| Camera Resolution | 640x480 @ 30 FPS |
| YOLO Model | yolo11n.pt |
| YOLO Confidence | 0.5 |

---

## 🔄 Coordinate Systems

### Internal (Calculation)
- **vx** = forward
- **vy** = left

### Display Output (Displacement)
- **X+** = right (kanan)
- **Y+** = forward (depan)

### Conversion
```python
dx_right = -vy * dt
dy_forward = vx * dt
```

---

## 📋 Workflow

```
1. User positions robot manually
   ↓
2. User presses SPACE
   ↓
3. System:
   - Detects humans (YOLO + RealSense)
   - Calculates SFM forces
   - Computes next velocity
   - Calculates displacement
   - Updates display
   ↓
4. User moves robot to new position
   ↓
5. Repeat from step 2
   ↓
6. User presses Q
   ↓
7. System generates:
   - CSV file
   - Trajectory plot
   - Shows graph
```

---

## 🎨 Visual Design

Tampilan mirip gambar referensi:
- ✅ Top bar: Sample count + controls
- ✅ Main view: Camera feed + YOLO boxes + proxemic circles + arrow
- ✅ Bottom panel: Complete info dengan displacement format

---

## 🆚 Comparison with Original Request

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Robot rusak/manual | ✅ | Manual movement by user |
| Sample setiap 1/4 detik | ✅ | SAMPLE_INTERVAL = 0.25 |
| User input SPACE | ✅ | Manual trigger, not automatic |
| Social force calculation | ✅ | Complete SFM implementation |
| Initial velocity 1 m/s | ✅ | INITIAL_VELOCITY = 1.0 |
| RealSense + YOLO | ✅ | Full integration |
| Grafik output | ✅ | Matplotlib trajectory plot |
| Displacement X+/Y+ | ✅ | Format: +0.4X +0.5Y |
| Visual like reference | ✅ | Matching layout and info |

---

## 💡 Usage Tips

1. **Lighting**: Ensure good lighting untuk YOLO detection
2. **Camera angle**: Mount camera facing forward
3. **Sampling rate**: Press SPACE setiap ~0.5-1 meter movement
4. **Data collection**: Aim for 10-20 samples per session
5. **Multiple scenarios**: Test dengan berbagai posisi manusia

---

## ✨ Highlights

- **Clean code**: Single file, well-documented
- **Visual rich**: Semua info ditampilkan real-time
- **Data complete**: CSV contains all needed data
- **Easy to use**: Simple controls
- **Production ready**: Error handling included

---

**Tester102 v2.0 - Ready to use! 🚀**

SDSC Team | 2026-10-04
