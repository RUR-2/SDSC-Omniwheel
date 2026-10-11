# Manual Sampling Guide - Tester102_3

## Overview

Tester102_3 versi 3.0 menambahkan fitur **manual sampling setiap 1/4 detik (250ms)** yang diintegrasikan dari Tester102. User dapat mengambil sample data secara manual dengan menekan SPACE key.

## Konsep Sampling

### Perbedaan dengan Auto Mode (v2.0)
- **v2.0**: Output command setiap 1 detik otomatis
- **v3.0**: Sampling manual dengan SPACE key setiap 0.25 detik

### Workflow
```
1. User geser camera secara fisik
2. User tekan SPACE → Ambil sample
3. Robot hitung avoidance command untuk 0.25s
4. Robot tampilkan displacement (X, Y)
5. User geser camera lagi
6. Ulangi dari step 2
```

## Controls

| Key | Function | Description |
|-----|----------|-------------|
| `SPACE` | Take Sample | Ambil sample data setiap 0.25s |
| `R` | Reset | Reset trajectory dan statistics |
| `S` | Save CSV | Simpan data ke CSV file |
| `Q` | Quit | Keluar dan tampilkan trajectory plot |

## Sample Data Structure

Setiap sample menyimpan:
- **Timestamp**: Waktu sample (detik)
- **Position**: Posisi camera accumulated (X, Y) meter
- **Velocity**: Kecepatan (Vx, Vy) m/s
- **Direction**: Target dan Avoidance direction
- **Speed**: Current dan target speed
- **Humans**: Jumlah dan jarak terdekat
- **Proxemic Zone**: INTIMATE / PERSONAL / SOCIAL / PUBLIC
- **SFM Force**: Force dari Social Force Model
- **Displacement**: Perpindahan untuk 0.25s (X, Y) meter

## Output Format

### Console Output per Sample
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
```

### Displacement Coordinate System
- **X+ = Kanan** (right)
- **Y+ = Depan** (forward)
- **X- = Kiri** (left)
- **Y- = Belakang** (backward)

Contoh:
- `+0.040X +0.145Y` → Gerak ke kanan-depan
- `-0.030X +0.100Y` → Gerak ke kiri-depan
- `+0.000X -0.050Y` → Gerak mundur

## Data Export

### CSV File
Filename: `trajectory_YYYYMMDD_HHMMSS.csv`

Columns:
```
sample_id, timestamp, 
position_x, position_y, 
velocity_x, velocity_y,
target_dir_x, target_dir_y,
avoid_dir_x, avoid_dir_y,
current_speed, target_speed,
num_humans, closest_distance, proxemic_zone,
sfm_force_x, sfm_force_y,
displacement_x, displacement_y
```

### Trajectory Plot
Filename: `trajectory_plot_YYYYMMDD_HHMMSS.png`

**Left Panel**: Trajectory Map
- Blue line: Camera path
- Circles: Proxemic zones (Intimate, Personal, Social)
- Green marker: Start position
- Red marker: End position

**Right Panel**: Time Series
- Blue line: Speed (m/s)
- Red line: SFM Force (N)
- Green line: Number of humans detected

## Usage Example

### Basic Workflow
```bash
# 1. Run program
python3 manual_camera_movement_tester.py

# 2. Wait for initialization
# 3. Geser camera secara fisik
# 4. Tekan SPACE untuk sample pertama
# 5. Geser camera lagi
# 6. Tekan SPACE untuk sample kedua
# ... repeat ...

# 7. Optional: Tekan S untuk save CSV
# 8. Tekan Q untuk quit dan lihat plot
```

### Testing Scenarios

#### Scenario 1: Straight Movement (No Humans)
```
Sample #1: Position (0, 0) → Displacement +0.000X +0.250Y
Sample #2: Position (0, 0.25) → Displacement +0.000X +0.250Y
Sample #3: Position (0, 0.50) → Displacement +0.000X +0.250Y
Result: Straight forward movement
```

#### Scenario 2: Avoidance Right
```
Sample #1: 1 human detected at 2.5m left
Sample #2: Avoidance direction: +15° (right deviation)
Sample #3: Displacement +0.065X +0.240Y (kanan-depan)
Result: Robot menghindar ke kanan
```

#### Scenario 3: Slow Down (Personal Zone)
```
Sample #1: Human at 3.0m → Speed 1.0 m/s
Sample #2: Human at 2.0m → Speed 0.6 m/s (SOCIAL)
Sample #3: Human at 1.0m → Speed 0.3 m/s (PERSONAL)
Result: Speed reduction based on proxemic zone
```

## Integration dengan Tester102

### Similarities
- ✅ Sample interval: 0.25 detik
- ✅ Displacement format: X+right, Y+forward
- ✅ CSV export structure
- ✅ Trajectory plotting

### Differences
| Aspect | Tester102 | Tester102_3 |
|--------|-----------|-------------|
| **Movement** | Robot digerak manual | Camera digeser manual |
| **Purpose** | Test broken robot | Validate avoidance algorithm |
| **Initial velocity** | 1.0 m/s (robot) | Variable (based on zone) |
| **Output** | Robot displacement | Camera avoidance command |

## Tips & Best Practices

### Sampling Timing
- ⏱️ **Consistent timing**: Usahakan sampling setiap ~0.25s
- 🎯 **Smooth movement**: Geser camera dengan smooth, tidak jerky
- 📊 **Sufficient samples**: Minimal 10 samples untuk analisis

### Data Quality
- ✅ Pastikan human detection stabil
- ✅ Tunggu camera stabilize sebelum sample
- ✅ Hindari motion blur saat sampling

### Analysis
- 📈 Review CSV untuk pola avoidance
- 🗺️ Check trajectory plot untuk consistency
- 🔍 Compare dengan expected behavior

## Troubleshooting

### No Samples Collected
**Problem**: Pressed Q but no plot shown
**Solution**: Tekan SPACE minimal 1x untuk sampling

### Position Not Accumulating
**Problem**: Position tetap (0, 0)
**Solution**: Pastikan velocity tidak 0, ada human detection atau target direction

### CSV File Not Found
**Problem**: File tidak tersimpan
**Solution**: Pastikan folder Tester102_3 exist dan writable

## Version History

- **v3.0** (2026-10-04): Manual sampling integration
- **v2.0** (2024-12-31): Automatic avoidance
- **v1.0** (2024-12-31): Manual keyboard control

---

**Author**: Brone Social Nav Team  
**Last Updated**: 2026-10-04  
**Status**: Active Development
