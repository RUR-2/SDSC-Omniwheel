# Integration Summary: Tester102_3 Manual Camera Movement Tester

## 📋 Overview

Program **Tester102_3** adalah solusi testing untuk robot Roda yang sedang mengalami kerusakan fisik. Program ini memungkinkan testing navigasi dengan **simulasi pergerakan kamera manual** menggunakan keyboard, sambil tetap memvalidasi behavior proxemic zone dan speed adjustment.

## 🎯 Problem Statement

**Situasi:**
- Robot Roda (fisik) sedang dalam perbaikan/kerusakan
- Tidak bisa melakukan testing pergerakan fisik
- Perlu validasi algoritma proxemic navigation
- Perlu output perintah gerakan dalam format 2D (X, Y axis)

**Solusi:**
- Simulasi pergerakan dengan keyboard control
- Kamera depth untuk deteksi manusia dan proxemic zones
- Output movement command untuk 1 detik ke depan
- Tracking posisi 2D dan trajectory

## 🔄 Relationship dengan Program Lain

```
┌─────────────────────────────────────────────────────────────┐
│                   TESTING ECOSYSTEM                         │
└─────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Tester102      │     │  Tester102_3     │     │  Robot Fisik     │
│                  │     │                  │     │                  │
│  Pure SFM        │────▶│  Manual Control  │────▶│  Implementation  │
│  Avoidance       │     │  + Proxemics     │     │  (saat fixed)    │
│                  │     │                  │     │                  │
│  • Force calc    │     │  • Keyboard      │     │  • Real motors   │
│  • No goal       │     │  • Speed adjust  │     │  • Real sensors  │
│  • Reaction test │     │  • 2D tracking   │     │  • Full system   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
       ▲                         ▲                         ▲
       │                         │                         │
       └─────────────────────────┴─────────────────────────┘
                        Validation Chain
```

### Program Comparison

| Aspect | Tester102 | Tester102_3 | Robot Fisik |
|--------|-----------|-------------|-------------|
| **Control** | None (pure observation) | Keyboard (WASD) | Autonomous |
| **Movement** | Simulated (force vectors) | Manual simulation | Real motors |
| **Speed Source** | SFM force calculation | Proxemic zones | Real velocity |
| **Goal/Target** | None | User-defined | Autonomous goal |
| **Output** | Force vectors, velocity | Movement commands, X/Y | Motor commands |
| **Position** | Not tracked | Tracked (X, Y) | Real odometry |
| **Use Case** | Understand reactions | Test navigation | Production use |
| **Robot Status** | Not needed | Not needed | Must be functional |

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                  TESTER102_3 ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────┘

Input Layer:
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │   Keyboard   │   │  RealSense   │   │     YOLO     │
  │    (WASD)    │   │    Depth     │   │   Detection  │
  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
         │                  │                  │
         ▼                  ▼                  ▼
Processing Layer:
  ┌──────────────────────────────────────────────────────┐
  │              Manual Control System                   │
  │  • Direction vector from keyboard                    │
  │  • Base speed: 1.0 m/s                              │
  │  • Target direction calculation                      │
  └──────────────────────┬───────────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────────┐
  │         Proxemic Zone Classification                 │
  │  • Detect humans (YOLO)                             │
  │  • Measure distance (depth camera)                  │
  │  • Classify zone (INTIMATE/PERSONAL/SOCIAL/PUBLIC)  │
  │  • Find closest human                               │
  └──────────────────────┬───────────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────────┐
  │           Speed Adjustment System                    │
  │  • INTIMATE (<0.45m)  → 0.0 m/s (STOP)             │
  │  • PERSONAL (0.45-1.2m) → 0.3 m/s                  │
  │  • SOCIAL (1.2-3.6m)   → 0.6 m/s                   │
  │  • PUBLIC (>3.6m)      → 1.0 m/s                   │
  │  • Smooth transitions (acceleration/deceleration)   │
  └──────────────────────┬───────────────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────────────┐
  │          Velocity Calculation                        │
  │  • vx = direction_x × adjusted_speed                │
  │  • vy = direction_y × adjusted_speed                │
  │  • Integration: position += velocity × dt           │
  └──────────────────────┬───────────────────────────────┘
                         │
Output Layer:           ▼
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │   Movement   │   │   Position   │   │ Visualization│
  │   Command    │   │   Tracking   │   │   (OpenCV)   │
  │  (1s, X/Y)   │   │   (X, Y)     │   │              │
  └──────────────┘   └──────────────┘   └──────────────┘
```

### Data Flow

```
User Input (Keyboard)
         ↓
  Direction Vector (normalized)
         ↓
  Target Direction ← Current Direction (smooth update)
         ↓
Camera Frame → YOLO → Human Detections
         ↓              ↓
    Depth Map → Distance Measurement
         ↓              ↓
              Proxemic Classification
                       ↓
               Closest Human Distance
                       ↓
             Speed Adjustment (zone-based)
                       ↓
    Target Direction × Adjusted Speed = Velocity (vx, vy)
                       ↓
         ┌─────────────┴─────────────┐
         ▼                           ▼
  Position Update              Movement Command
  (integration)                (1 second output)
         ▼                           ▼
    X, Y coords                 Direction + X/Y axes
         ▼                           ▼
     Display                     Display
```

## 🔧 Technical Specifications

### Input

**Keyboard Control:**
- Keys: W, A, S, D
- Mode: Toggle (press to turn ON/OFF)
- Combinations: Yes (e.g., W+D = diagonal)
- Response: Immediate

**Camera Input:**
- Type: Intel RealSense D435/D455
- Resolution: 640×480 @ 30fps
- Depth range: 0.3m - 10m
- FOV: 69° horizontal

**Detection:**
- Model: YOLO11n
- Class: Person (class 0)
- Confidence threshold: 0.5
- Processing: CPU/GPU

### Processing

**Proxemic Zones:**
```python
R_INTIMATE = 0.45 m   # Emergency stop
R_PERSONAL = 1.20 m   # Slow down
R_SOCIAL = 3.60 m     # Caution
```

**Speed Parameters:**
```python
BASE_SPEED = 1.0 m/s        # 100%
SPEED_PUBLIC = 1.0 m/s      # 100% (no humans or far)
SPEED_SOCIAL = 0.6 m/s      # 60%  (moderate proximity)
SPEED_PERSONAL = 0.3 m/s    # 30%  (close)
SPEED_INTIMATE = 0.0 m/s    # 0%   (STOP!)
```

**Speed Transition:**
- Change rate: 2.0 m/s² (smooth acceleration/deceleration)
- Update rate: Real-time (every frame)

**Position Tracking:**
- Method: Velocity integration
- Formula: `position(t+dt) = position(t) + velocity × dt`
- Origin: (0, 0) at program start
- Coordinate system: 2D (X, Y)

### Output

**Movement Command (1 second interval):**
```
Format:
  Movement Command (1s): [Arrow] [Direction]
    X-axis: [+/-]X.XXX m/s  |  Y-axis: [+/-]X.XXX m/s

Example:
  Movement Command (1s): ↗ FWD-RIGHT
    X-axis: +0.424 m/s  |  Y-axis: +0.424 m/s
```

**Direction Encoding:**
- 8 directions: N, NE, E, SE, S, SW, W, NW
- Arrows: ↑↗→↘↓↙←↖ (unicode) or ASCII fallback
- Stop: ⊙ (when speed ≈ 0)

**Axis Components:**
- X-axis: horizontal (-left to +right)
- Y-axis: vertical (-backward to +forward)
- Range: -1.0 to +1.0 m/s each
- Combined magnitude: √(Vx² + Vy²)

**Visualization:**
- Proxemic zone circles (red/orange/yellow)
- Human bounding boxes (zone-colored)
- Robot position indicator (blue circle)
- Movement trajectory (red trail)
- Info panel (statistics)

## 📊 Algorithm Details

### 1. Direction Vector Calculation

```python
direction = np.array([0.0, 0.0])

if keys_pressed['w']:  direction[1] += 1.0  # Forward
if keys_pressed['s']:  direction[1] -= 1.0  # Backward
if keys_pressed['d']:  direction[0] += 1.0  # Right
if keys_pressed['a']:  direction[0] -= 1.0  # Left

# Normalize
if magnitude(direction) > 0:
    direction = direction / magnitude(direction)
```

### 2. Proxemic Zone Classification

```python
def get_proxemic_zone_and_speed(distance):
    if distance < 0.45:
        return "INTIMATE", RED, 0.0
    elif distance < 1.20:
        return "PERSONAL", ORANGE, 0.3
    elif distance < 3.60:
        return "SOCIAL", YELLOW, 0.6
    else:
        return "PUBLIC", GREEN, 1.0
```

### 3. Speed Adjustment

```python
# Find closest human
closest_human = min(detections, key=lambda d: d['distance'])
distance = closest_human['distance']

# Get target speed from zone
zone, color, target_speed = get_zone_and_speed(distance)

# Smooth transition
speed_change_rate = 2.0  # m/s²
if current_speed < target_speed:
    current_speed += speed_change_rate * dt
elif current_speed > target_speed:
    current_speed -= speed_change_rate * dt
```

### 4. Velocity Calculation

```python
# Calculate velocity components
vx = direction[0] * current_speed
vy = direction[1] * current_speed

# Update position (integration)
robot_pos[0] += vx * dt
robot_pos[1] += vy * dt
```

### 5. Movement Command Generation

```python
# Calculate angle
angle = atan2(vy, vx)

# Map to 8 directions
if -22.5° ≤ angle < 22.5°:     direction = "RIGHT"
elif 22.5° ≤ angle < 67.5°:    direction = "FWD-RIGHT"
elif 67.5° ≤ angle < 112.5°:   direction = "FORWARD"
# ... etc

# Format output
command = f"{arrow} {direction}"
axis_info = f"X-axis: {vx:+.3f} m/s  |  Y-axis: {vy:+.3f} m/s"
```

## 🧪 Testing Workflow

### Pre-Test Setup
1. ✅ Connect RealSense camera (USB 3.0)
2. ✅ Test camera with `realsense-viewer`
3. ✅ Download YOLO model (`yolo11n.pt`)
4. ✅ Install dependencies (`pip3 install ...`)
5. ✅ Clear test space (3-5m radius)
6. ✅ Ensure good lighting

### Basic Test (No Humans)
1. Run program
2. Press `[W]` for forward movement
3. **Expected**: speed = 1.0 m/s, Y-axis = +1.0, X-axis = 0.0
4. **Validation**: Position increases steadily in Y direction

### Proxemic Zone Test
1. Human stands 4m ahead
2. Press `[W]`
3. **Expected transitions**:
   - At 4.0m: 1.0 m/s (PUBLIC - green)
   - At 3.5m: 0.6 m/s (SOCIAL - yellow)
   - At 1.0m: 0.3 m/s (PERSONAL - orange)
   - At 0.4m: 0.0 m/s (INTIMATE - red, STOP)
4. **Validation**: Smooth speed transitions, correct zone colors

### Directional Test
1. Test all 8 directions (W, W+D, D, S+D, S, S+A, A, W+A)
2. **Expected**: Correct arrow symbols and axis components
3. **Validation**: Trajectory follows commanded direction

### Multiple Human Test
1. Place 2+ humans at different distances
2. Press `[W]`
3. **Expected**: Speed based on CLOSEST human
4. **Validation**: Display shows all humans, correct closest detection

### Emergency Stop Test
1. Moving forward (`[W]` pressed)
2. Human suddenly enters <0.45m
3. **Expected**: Immediate stop, RED zone, "⊙ STOP"
4. **Validation**: Quick response, no collision

## 📈 Expected Performance

### Frame Rate
- Target: 30 FPS
- Typical: 25-30 FPS (with YOLO on CPU)
- With GPU: 30 FPS stable

### Detection
- Range: 1-5 meters optimal
- Confidence: >0.5
- False positives: <5%
- Miss rate: <10% (with good lighting)

### Speed Transition
- Response time: <100ms
- Transition smoothness: 2.0 m/s² max
- Overshoot: None (clamped)

### Position Accuracy
- Integration error: <5% over 10 seconds
- Reset: Press `[SPACE]` to recalibrate

## 🔍 Debugging & Validation

### Check Detection
```python
# In code, add debug print:
print(f"Detections: {len(detections)}")
for det in detections:
    print(f"  - Distance: {det['distance']:.2f}m")
```

### Check Speed Adjustment
```python
# Monitor speed transitions:
print(f"Target: {target_speed:.2f}, Current: {current_speed:.2f}")
```

### Check Velocity Components
```python
# Verify calculations:
print(f"Direction: ({direction[0]:.2f}, {direction[1]:.2f})")
print(f"Velocity: ({vx:.3f}, {vy:.3f})")
print(f"Magnitude: {math.hypot(vx, vy):.3f}")
```

### Visualization Checks
- Proxemic circles: should be concentric, centered on robot
- Bounding boxes: should be zone-colored
- Trajectory: should follow movement history
- Info panel: should update in real-time

## 📝 Data Collection

### Metrics to Record

```
Time | X | Y | Vx | Vy | Speed | Zone | Dist | Dir
-----|---|---|----|-------|-------|------|------|-----
0.0  | 0 | 0 | 0  | +1.0  | 1.00  | PUB  | inf  | FWD
1.0  | 0 | 1 | 0  | +1.0  | 1.00  | PUB  | 4.5  | FWD
2.0  | 0 | 2 | 0  | +0.6  | 0.60  | SOC  | 2.8  | FWD
```

### Analysis Questions
1. Is speed adjustment smooth?
2. Do zone transitions occur at correct distances?
3. Is emergency stop reliable?
4. Are axis components correct?
5. Does position tracking drift?

## 🚀 Next Steps (Robot Integration)

When robot is fixed:

1. **Transfer Parameters**
   ```python
   # From Tester102_3 to robot code:
   ROBOT_BASE_SPEED = 1.0  # m/s
   ROBOT_PROXEMIC_ZONES = {
       'INTIMATE': (0.45, 0.0),
       'PERSONAL': (1.20, 0.3),
       'SOCIAL': (3.60, 0.6),
       'PUBLIC': (float('inf'), 1.0)
   }
   ```

2. **Command Mapping**
   ```python
   # Convert movement command to motor commands:
   vx, vy = movement_command.get_velocity()
   motor_commands = inverse_kinematics(vx, vy)
   ```

3. **Validation**
   - Run same test scenarios on real robot
   - Compare behavior with Tester102_3 simulation
   - Adjust parameters if needed

## ✅ Summary

**Tester102_3** menyediakan:
- ✅ Manual control untuk testing tanpa robot fisik
- ✅ Proxemic zone validation
- ✅ Movement command output (1s, X/Y)
- ✅ Position tracking (2D)
- ✅ Real-time visualization
- ✅ Parameter tuning capability
- ✅ Data collection for analysis

**Use Cases:**
- Testing algoritma navigasi saat robot rusak
- Validasi proxemic zone behavior
- Parameter tuning sebelum deploy ke robot
- Training operator dengan simulasi
- Development dan debugging tanpa hardware

**Integration Path:**
```
Tester102_3 (Sim) → Parameters → Robot Code → Real Robot
```

---

**Status**: ✅ Ready for Testing  
**Version**: 1.0  
**Date**: 2024-12-31  
**Author**: Brone Social Nav Team
