# Tester102 - Manual Sampling Tester v2.0

## 📋 Description

Testing tool untuk robot omniwheel yang **rusak** (tidak bisa bergerak sendiri).

## ✨ Features

- ✅ Robot digerakkan manual oleh user
- ✅ User press **SPACE** untuk sampling setiap 1/4 detik
- ✅ Social force calculation dengan **initial velocity 1.0 m/s**
- ✅ RealSense camera + YOLOv11 untuk deteksi manusia
- ✅ Tampilan visual seperti referensi dengan:
  - Proxemic zone circles (Red/Orange/Yellow)
  - Green command arrow
  - Info panel lengkap
- ✅ **Displacement output**: Format `+0.4X +0.5Y` (X+=kanan, Y+=depan)
- ✅ Grafik trajectory + human detection

## 🚀 Quick Start

```bash
# Install
cd Tester102
pip install -r requirements.txt

# Run
python3 manual_sampling_tester.py
```

## 🎮 Controls

| Key | Action |
|-----|--------|
| `SPACE` | Take sample |
| `Q` | Quit and show graph |
| `R` | Reset trajectory |
| `S` | Save to CSV |

## 📊 Output

### Display Panel Shows:
- **Time**: Current time
- **Target Direction**: Goal angle
- **Avoidance Direction**: Angle avoiding humans (orange)
- **Avoidance Force**: SFM force magnitude
- **Current Speed**: m/s and percentage (green)
- **Proxemic Zone**: Closest zone with distance (colored)
- **Movement Command (0.25s)**: Direction (FWD/LEFT/RIGHT)
- **Displacement**: `+0.4X +0.5Y` format (green)
  - X+ = kanan (right)
  - Y+ = depan (forward)

### Files Generated:
1. `trajectory_YYYYMMDD_HHMMSS.csv` - Sample data
2. `trajectory_plot_YYYYMMDD_HHMMSS.png` - Trajectory graph

## 📈 CSV Columns

- `sample_id`, `timestamp`
- `robot_x`, `robot_y` - Position
- `robot_vx`, `robot_vy` - Velocity
- `sfm_fx`, `sfm_fy` - Forces
- `next_vx`, `next_vy` - Next velocity
- `disp_x_right`, `disp_y_forward` - Displacement (X+=right, Y+=forward)
- `num_humans` - Human count

## ⚙️ Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Sample Interval | 0.25s | 1/4 detik |
| Initial Velocity | 1.0 m/s | Starting speed |
| SFM A | 5.0 N | Repulsion force |
| SFM B | 0.8 m | Repulsion range |
| Intimate Zone | 0.45 m | Emergency stop |
| Personal Zone | 1.20 m | Slow down |
| Social Zone | 3.60 m | Avoidance |

## 🔧 Troubleshooting

### Camera not detected
```bash
rs-enumerate-devices
realsense-viewer
```

### YOLO model error
Model akan auto-download pada first run.

## 📝 Notes

- Robot coordinate system (internal): vx=forward, vy=left
- Output displacement: X+=right, Y+=forward
- Dead reckoning untuk position estimation
- Manual timing (user controlled)

## 👥 Author

**SDSC Team**  
Version: 2.0 (Clean rebuild)  
Date: 2026-10-04

---

**Perfect untuk robot yang rusak! 🤖✨**
