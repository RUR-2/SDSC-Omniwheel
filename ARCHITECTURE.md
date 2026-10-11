# 🏗️ Bluetooth SDSC - System Architecture

Visual architecture dan data flow untuk Bluetooth SDSC Controller.

---

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BLUETOOTH SDSC CONTROLLER                     │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   SENSING    │ →  │  PROCESSING  │ →  │    CONTROL   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         ↓                    ↓                     ↓            │
│    Joystick              Detection            Bluetooth         │
│    RealSense             Tracking             Serial Tx         │
│       YOLO               SFM Force                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow Diagram

```
                      ┌────────────────────────┐
                      │   HARDWARE INPUTS      │
                      └────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
            ┌───────────┐  ┌──────────┐  ┌──────────┐
            │ Joystick  │  │ RealSense│  │  YOLO    │
            │  (USB)    │  │  Camera  │  │  Model   │
            └───────────┘  └──────────┘  └──────────┘
                    │             │             │
                    │      ┌──────┴──────┐      │
                    │      │  Detection  │◄─────┘
                    │      │   Thread    │
                    │      └──────┬──────┘
                    │             │
                    │             ▼
                    │      ┌─────────────┐
                    │      │  Detections │
                    │      │   Buffer    │
                    │      └─────────────┘
                    │             │
                    └─────┬───────┘
                          ▼
                  ┌───────────────┐
                  │  Main Control │
                  │     Loop      │
                  │   (20 Hz)     │
                  └───────┬───────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
        ┌──────────────┐    ┌─────────────┐
        │   Social     │    │  Velocity   │
        │   Force      │    │  Modulator  │
        │   Model      │    └──────┬──────┘
        └──────┬───────┘           │
               │                   │
               └─────────┬─────────┘
                         ▼
                  ┌─────────────┐
                  │   Packet    │
                  │   Builder   │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  Bluetooth  │
                  │   Serial    │
                  │   (rfcomm)  │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   ESP32     │
                  │   Robot     │
                  └─────────────┘
```

---

## 🧵 Thread Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        MAIN THREAD                             │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Tkinter GUI (Event Loop)                            │    │
│  │    ├─ Bluetooth controls                             │    │
│  │    ├─ Status display                                 │    │
│  │    └─ Log window                                     │    │
│  └──────────────────────────────────────────────────────┘    │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Control Loop (Tkinter.after)                        │    │
│  │    • Read joystick (pygame)                          │    │
│  │    • Get detections (from thread)                    │    │
│  │    • Compute SFM                                     │    │
│  │    • Build packet                                    │    │
│  │    • Send via Bluetooth                              │    │
│  │    • Update UI                                       │    │
│  │    Rate: 20 Hz (50ms)                                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                      DETECTION THREAD (daemon)                 │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Detection Loop                                       │    │
│  │    1. Capture frames (RealSense)                     │    │
│  │    2. Align depth to color                           │    │
│  │    3. Run YOLO inference                             │    │
│  │    4. Extract bounding boxes                         │    │
│  │    5. Get depth at centers                           │    │
│  │    6. Match to tracks                                │    │
│  │    7. Transform coordinates                          │    │
│  │    8. Update buffer (thread-safe)                    │    │
│  │    Rate: 10 Hz (100ms)                               │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                   VISUALIZATION THREAD (daemon)                │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  OpenCV Window Loop                                   │    │
│  │    1. Get latest frame + detections                  │    │
│  │    2. Draw bounding boxes                            │    │
│  │    3. Draw IDs, distances                            │    │
│  │    4. Draw zone indicators                           │    │
│  │    5. Draw force vectors                             │    │
│  │    6. Show info overlay                              │    │
│  │    7. Display with cv2.imshow()                      │    │
│  │    Rate: ~30 Hz (limited by waitKey)                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

**Thread Safety:**
- Detection buffer protected with `threading.Lock()`
- Main thread reads via `get_detections()` (copies data)
- No shared mutable state between threads

---

## 🧩 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     bluetooth_sdsc.py                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  HumanDetector (Class)                             │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ • pipeline: rs.pipeline                      │  │    │
│  │  │ • model: YOLO                                │  │    │
│  │  │ • detections: list (thread-safe)             │  │    │
│  │  │ • tracked_humans: dict                       │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ Methods:                                     │  │    │
│  │  │ • detect_once()                              │  │    │
│  │  │ • pixel_to_camera_frame()                    │  │    │
│  │  │ • camera_to_robot_frame()                    │  │    │
│  │  │ • match_detection_to_track()                 │  │    │
│  │  │ • run_detection_loop() [thread]              │  │    │
│  │  │ • get_detections() [thread-safe]             │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  SocialForceModulator (Class)                      │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ • detections: list                           │  │    │
│  │  │ • closest_human_dist: float                  │  │    │
│  │  │ • closest_human_zone: str                    │  │    │
│  │  │ • fx_rep, fy_rep: float (force vectors)      │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  │  ┌──────────────────────────────────────────────┐  │    │
│  │  │ Methods:                                     │  │    │
│  │  │ • compute_repulsive_force()                  │  │    │
│  │  │ • get_proxemic_zone()                        │  │    │
│  │  │ • modulate_velocity()                        │  │    │
│  │  │ • get_status()                               │  │    │
│  │  └──────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Global Functions                                  │    │
│  │  • read_input() - Main control loop                │    │
│  │  • build_packet_with_sfm() - Velocity modulation   │    │
│  │  • connect_serial() - Bluetooth connection          │    │
│  │  • send() - Packet transmission                     │    │
│  │  • update_ui() - GUI updates                        │    │
│  │  • run_visualization() - OpenCV thread              │    │
│  │  • log_message() - Event logging                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  GUI (Tkinter)                                      │    │
│  │  • root: Tk window                                  │    │
│  │  • top_frame: Bluetooth controls                    │    │
│  │  • middle_frame: Status display                     │    │
│  │  • log_frame: ScrolledText log                      │    │
│  │  • Labels: status, zone, humans, distance, force    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔢 Data Structures

### Detection Format
```python
detection = {
    'id': int,              # Tracking ID (1, 2, 3, ...)
    'pixel_x': int,         # Center X in image
    'pixel_y': int,         # Center Y in image
    'distance': float,      # Depth (meters)
    'bbox': [x1,y1,x2,y2],  # Bounding box
    'confidence': float,    # YOLO confidence (0-1)
    'position': {
        'x': float,         # Robot frame X (forward, m)
        'y': float,         # Robot frame Y (left, m)
        'z': float          # Robot frame Z (up, m)
    }
}
```

### SFM Status
```python
status = {
    'closest_dist': float,     # Distance to nearest human (m)
    'zone': str,               # "INTIMATE"|"PERSONAL"|"SOCIAL"|"PUBLIC"
    'num_humans': int,         # Count of detections
    'fx_rep': float,           # Repulsive force X (N)
    'fy_rep': float            # Repulsive force Y (N)
}
```

### Packet Format
```python
packet = "<x,y,w>\n"
# x: lateral (0-255, center=127)
# y: forward (0-255, center=127)
# w: angular (0-255, center=127)
```

---

## 🔁 Control Flow

### Main Control Loop (20 Hz)
```
START
  │
  ▼
pygame.event.pump()  ← Update pygame events
  │
  ▼
Get detections ← From detection thread (thread-safe)
  │
  ▼
Joystick connected? ─NO─→ packet = neutral
  │                        │
 YES                       │
  │                        │
  ▼                        │
Read axes & buttons        │
  │                        │
  ▼                        │
Window focused? ─NO────────┤
  │                        │
 YES                       │
  │                        │
  ▼                        │
Deadman pressed? ─NO───────┤
  │                        │
 YES                       │
  │                        │
  ▼                        │
Apply deadzone to sticks   │
  │                        │
  ▼                        │
Convert to robot frame     │
  │                        │
  ▼                        │
SFM modulation ← detections│
  │                        │
  ├─ Compute repulsive forces
  │  from all humans       │
  ├─ Determine closest zone│
  ├─ Apply velocity adj.   │
  └─ Apply zone scaling    │
  │                        │
  ▼                        │
Build packet               │
  │                        │
  ▼◄───────────────────────┘
Packet changed?
  │
 YES
  │
  ▼
send(packet) ← Bluetooth serial
  │
  ▼
Connection OK? ─NO─→ close_serial()
  │
 YES
  │
  ▼
update_ui() ← Update status labels
  │
  ▼
Schedule next ← root.after(50ms)
  │
  ▼
REPEAT
```

### Detection Loop (10 Hz)
```
START
  │
  ▼
Wait for frames ← RealSense pipeline
  │
  ▼
Align depth to color
  │
  ▼
Convert to numpy
  │
  ▼
YOLO inference ← Classes=[0] (person)
  │
  ▼
For each detection:
  │
  ├─ Get bbox center
  ├─ Get depth at center
  ├─ Filter by distance
  ├─ Match to track (or create new ID)
  ├─ pixel_to_camera_frame()
  ├─ camera_to_robot_frame()
  └─ Build detection dict
  │
  ▼
Lock buffer ← threading.Lock()
  │
  ▼
Update detections ← Atomic write
  │
  ▼
Unlock buffer
  │
  ▼
Sleep to maintain 10 Hz
  │
  ▼
REPEAT
```

---

## 📐 Coordinate Transformations

### 1. Pixel → Camera Frame
```
Input: (pixel_x, pixel_y, depth_m)
       + camera intrinsics (fx, fy, cx, cy)

cam_x = (pixel_x - cx) / fx * depth_m
cam_y = (pixel_y - cy) / fy * depth_m
cam_z = depth_m

Output: (cam_x, cam_y, cam_z)
        Camera frame: X=right, Y=down, Z=forward
```

### 2. Camera Frame → Robot Frame
```
Input: (cam_x, cam_y, cam_z)

robot_x = cam_z     (forward)
robot_y = -cam_x    (left)
robot_z = -cam_y    (up)

Output: (robot_x, robot_y, robot_z)
        Robot frame: X=forward, Y=left, Z=up
```

### 3. Robot Frame → Distance
```
Input: (robot_x, robot_y, robot_z)

dist_2d = sqrt(robot_x² + robot_y²)
dist_3d = sqrt(robot_x² + robot_y² + robot_z²)

Output: distance (for zone determination)
```

---

## 🧮 Social Force Model Computation

### Repulsive Force Calculation
```
For each human:
  │
  ├─ dx = robot_x - human_x
  ├─ dy = robot_y - human_y
  ├─ dist = sqrt(dx² + dy²)
  │
  ├─ mag = A × exp(-dist / B)
  │        ▲       ▲     ▲
  │        │       │     └─ Range parameter (0.8m)
  │        │       └─────── Distance
  │        └───────────────── Magnitude (5.0 N)
  │
  ├─ fx = mag × (dx / dist)  ← Unit vector × magnitude
  ├─ fy = mag × (dy / dist)
  │
  └─ Sum all forces: fx_total, fy_total

Velocity adjustment:
  │
  ├─ vx_adj = fx_total / (mass × gain)
  ├─ vy_adj = fy_total / (mass × gain)
  │
  └─ Apply to joystick input:
       vx_mod = vx_joystick + vx_adj
       vy_mod = vy_joystick + vy_adj
```

### Zone-Based Scaling
```
Determine closest human distance
  │
  ▼
Get zone:
  ├─ dist < 0.45m → INTIMATE
  ├─ dist < 1.20m → PERSONAL
  ├─ dist < 3.60m → SOCIAL
  └─ else         → PUBLIC
  │
  ▼
Apply scaling:
  ├─ INTIMATE: scale = 0.0  (STOP)
  ├─ PERSONAL: scale = 0.3  (30%)
  ├─ SOCIAL:   scale = 0.7  (70%)
  └─ PUBLIC:   scale = 1.0  (100%)
  │
  ▼
vx_final = vx_mod × scale
vy_final = vy_mod × scale
vw_final = vw_mod × scale
```

---

## 🎨 Visualization Pipeline

```
Detection Thread → Latest frame + detections
  │
  ▼
Visualization Thread:
  │
  ├─ results.plot() ← YOLO annotated frame
  │
  ├─ For each detection:
  │   ├─ Draw ID text
  │   ├─ Draw distance text
  │   ├─ Draw position text
  │   └─ Draw zone circle (colored)
  │
  ├─ Draw force vector:
  │   ├─ Scale: fx, fy × 20
  │   ├─ Center: image center
  │   └─ Arrow: magenta
  │
  ├─ Draw info overlay:
  │   ├─ Detection count
  │   └─ Zone status
  │
  └─ cv2.imshow()
```

---

## 🔒 Thread Safety Mechanisms

### Detection Buffer
```python
class HumanDetector:
    def __init__(self):
        self.detections = []      # Shared state
        self.lock = threading.Lock()  # Protection
    
    def detect_once(self):        # Detection thread
        # ... compute detections ...
        with self.lock:           # Atomic write
            self.detections = new_detections
    
    def get_detections(self):     # Main thread
        with self.lock:           # Atomic read
            return self.detections.copy()  # Return copy!
```

**Key Points:**
- Lock ensures atomic read/write
- `copy()` prevents shared mutable state
- Short critical sections (just assignment)
- No deadlock risk (simple single lock)

---

## 📊 Performance Characteristics

### Latency Breakdown
```
Joystick input                  →  ~5ms
Detection (async, 10 Hz)        →  ~100ms (not in main loop)
SFM computation                 →  <1ms
Packet building                 →  <1ms
Serial transmission (115200)    →  ~1ms
ESP32 processing                →  ~10ms
Motor response                  →  ~20ms
─────────────────────────────────────────
Total: ~40ms (without detection in loop)

Detection adds: 30-50ms inference (GPU)
                80-120ms inference (CPU)
```

### CPU Usage
```
Main thread (20 Hz):           ~5% (1 core)
Detection thread (10 Hz):      ~30% (with GPU)
                               ~80% (with CPU)
Visualization thread:          ~10% (1 core)
─────────────────────────────────────────
Total: ~45% (GPU) or ~95% (CPU)
```

### Memory Usage
```
Base Python + libraries:       ~500 MB
YOLO model loaded:            ~100 MB
RealSense buffers:            ~50 MB
OpenCV display:               ~100 MB
CUDA context (if GPU):        ~1.5 GB
─────────────────────────────────────────
Total: ~750 MB (CPU) or ~2.2 GB (GPU)
```

---

## 🔍 Key Design Decisions

### 1. Multi-threading
**Why:** Keep control loop responsive (20 Hz) while detection runs slower (10 Hz)
**Trade-off:** Thread synchronization complexity vs. performance

### 2. Simple Tracking
**Why:** Fast, low overhead, good enough for demo
**Trade-off:** Can lose IDs during occlusion vs. SORT/DeepSORT complexity

### 3. SFM in Main Thread
**Why:** Needs latest joystick + detection data, fast computation
**Trade-off:** Could be in separate thread, but adds latency

### 4. OpenCV Separate Thread
**Why:** cv2.imshow() blocks, don't want to block control loop
**Trade-off:** Extra thread vs. potential GUI freeze

### 5. Lock-protected Buffer
**Why:** Simple, correct, no race conditions
**Trade-off:** Could use queue, but overkill for 1 producer + 1 consumer

---

## 🎓 Extension Points

### Add ROS 2 Integration
```python
class HumanDetectionPublisher(Node):
    def __init__(self):
        self.pub = self.create_publisher(HumanArray, '/humans', 10)
    
    def publish_detections(self, detections):
        msg = HumanArray()
        # Convert detections to ROS msg
        self.pub.publish(msg)
```

### Add Path Planning
```python
class PathPlanner:
    def plan(self, start, goal, detections):
        # A* with SFM cost
        return path
    
    def sfm_cost(self, pos, detections):
        # Compute SFM repulsion at pos
        return cost
```

### Add Multi-Camera
```python
class MultiCameraDetector:
    def __init__(self, camera_ids):
        self.cameras = [RealSenseCamera(id) for id in camera_ids]
    
    def detect_all(self):
        # Parallel detection
        # Merge results with coordinate transforms
        return merged_detections
```

---

**Document Version:** 2.0
**Last Updated:** 2024-12-31
**Author:** Brone Social Nav Team

---

*For implementation details, see the source code comments in `bluetooth_sdsc.py`*
*For usage instructions, see `QUICKSTART.md` and `README_SDSC.md`*
