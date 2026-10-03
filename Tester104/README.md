# 🎮 Tester104: Manual Control + Social Avoidance

## 📋 Overview

Tester104 adalah sistem kontrol robot yang menggabungkan:
- **Manual Control**: WASD keyboard atau Xbox controller
- **Social Avoidance**: Deteksi manusia real-time menggunakan YOLO
- **Hybrid Mode**: Kombinasi input manual + avoidance otomatis

Robot dapat dikontrol secara manual, tetapi akan **otomatis menghindari manusia** yang terdeteksi oleh kamera.

## ✨ Features

### 🎮 Dual Input Support
- **WASD Keyboard** - Kontrol dasar dengan keyboard
- **Xbox Controller** - Kontrol analog dengan joystick

### 🚧 Social Avoidance
- **YOLO Human Detection** - Deteksi manusia real-time dari kamera
- **Repulsive Forces** - Robot otomatis menjauh dari manusia terdeteksi
- **Configurable** - Dapat diaktifkan/nonaktifkan saat runtime

### 📹 Visual Feedback
- **Live Camera View** - Tampilan kamera dengan bounding boxes
- **Detection Overlay** - Confidence score dan jumlah deteksi
- **Status Display** - Real-time status avoidance

## 🚀 Installation

### Prerequisites

```bash
# ROS 2 packages
sudo apt install ros-humble-cv-bridge python3-opencv

# Python packages
pip3 install ultralytics pygame opencv-python numpy

# Download YOLO model (first run will auto-download)
# yolov8n.pt will be downloaded automatically
```

### Hardware Requirements
- **Camera**: USB camera atau CSI camera (ROS topic `/camera/image_raw`)
- **Xbox Controller** (optional): USB Xbox controller atau compatible gamepad

## 📖 Usage

### Quick Start

```bash
cd ~/Dummy1102/Tester104
python3 social_avoidance_teleop.py
```

### With ROS2 Camera Node

Terminal 1 - Start camera node:
```bash
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:=/dev/video0
```

Terminal 2 - Start Tester104:
```bash
cd ~/Dummy1102/Tester104
python3 social_avoidance_teleop.py
```

## 🎮 Controls

### Keyboard Controls

| Key | Action |
|-----|--------|
| **W** | Maju (Forward) |
| **S** | Mundur (Backward) |
| **A** | Strafe Kiri (Left) |
| **D** | Strafe Kanan (Right) |
| **Q** | Putar Kiri (CCW) |
| **E** | Putar Kanan (CW) |
| **Space** / **X** | Stop |
| **R** | Increase Speed (+0.1 m/s) |
| **F** | Decrease Speed (-0.1 m/s) |
| **V** | Toggle Social Avoidance ON/OFF |
| **C** | Toggle Camera View ON/OFF |
| **Ctrl+C** | Exit |

### Xbox Controller

| Input | Action |
|-------|--------|
| **Left Stick** | Forward/Backward & Strafe |
| **Right Stick** | Rotation (yaw) |
| **A Button** | Enable Social Avoidance |
| **B Button** | Disable Social Avoidance |
| **Y Button** | Toggle Camera View |
| **Start Button** | Reset Speed to Default |

## 🧠 How It Works

### 1. Manual Control
User input (keyboard/controller) generates base velocity commands:
```
manual_vx = forward/backward velocity
manual_vy = strafe left/right velocity
manual_w  = rotation velocity
```

### 2. Human Detection
YOLO detects humans in camera frame:
```python
- Class: 'person' (COCO class 0)
- Confidence threshold: 0.5
- Output: bounding boxes with position and size
```

### 3. Avoidance Force Calculation
Repulsive forces calculated from detected humans:
```
- Horizontal position → Strafe force (left/right)
- Detection size → Force magnitude (closer = stronger)
- Forward blocking → Slow down force
```

### 4. Velocity Fusion
Final velocity = Manual input + Avoidance forces:
```python
final_vx = manual_vx + avoidance_force_x
final_vy = manual_vy + avoidance_force_y
final_w  = manual_w  # Rotation not affected by avoidance
```

## 📊 Architecture

```
┌─────────────────┐
│  User Input     │
│  (WASD/Xbox)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ Manual Control  │      │  Camera Stream   │
│   Velocities    │      │  /camera/image   │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         │                        ▼
         │               ┌──────────────────┐
         │               │  YOLO Detection  │
         │               │  (Human Class)   │
         │               └────────┬─────────┘
         │                        │
         │                        ▼
         │               ┌──────────────────┐
         │               │ Avoidance Force  │
         │               │   Calculation    │
         │               └────────┬─────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────┐
│      Velocity Fusion & Limiter          │
│  final_vel = manual + avoidance_force   │
└──────────────────┬──────────────────────┘
                   │
                   ▼
          ┌────────────────┐
          │   /cmd_vel     │
          │ (Twist message)│
          └────────────────┘
```

## ⚙️ Configuration

Edit `social_avoidance_teleop.py` to tune parameters:

### Speed Limits
```python
self.linear_speed = 0.5    # Default linear speed (m/s)
self.angular_speed = 0.8   # Default angular speed (rad/s)
self.max_linear = 1.2      # Maximum linear speed
self.max_angular = 1.5     # Maximum angular speed
```

### Detection Parameters
```python
# In detect_humans()
confidence_threshold = 0.5  # YOLO confidence threshold

# In calculate_avoidance_forces()
force_magnitude = min(size * 10.0, 0.8)  # Max repulsive force
size_threshold = 0.1  # Size threshold for "close" detection
```

### YOLO Model
```python
# Change model size (n=nano, s=small, m=medium, l=large)
self.yolo_model = YOLO('yolov8n.pt')  # Fastest
self.yolo_model = YOLO('yolov8s.pt')  # Balanced
self.yolo_model = YOLO('yolov8m.pt')  # More accurate
```

## 🔧 Troubleshooting

### No Camera Feed
```bash
# Check camera device
ls /dev/video*

# Test camera with ROS
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:=/dev/video0

# Check topic
ros2 topic list | grep camera
ros2 topic echo /camera/image_raw --once
```

### YOLO Not Working
```bash
# Install ultralytics
pip3 install ultralytics

# Test YOLO separately
python3 -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt'); print('OK')"
```

### Xbox Controller Not Detected
```bash
# Check if controller is connected
ls /dev/input/js*

# Test pygame
python3 -c "import pygame; pygame.init(); pygame.joystick.init(); print(f'Joysticks: {pygame.joystick.get_count()}')"

# Grant permissions
sudo chmod a+rw /dev/input/js0
```

### Robot Not Moving
1. Check if jetson_robot_bridge is running
2. Check ROS_DOMAIN_ID matches
3. Test with simple teleop first
4. Check `/cmd_vel` topic: `ros2 topic echo /cmd_vel`

## 📈 Performance Tips

### For Jetson Nano/TX2
```python
# Use smaller YOLO model
self.yolo_model = YOLO('yolov8n.pt')

# Reduce camera resolution in camera node
# Add to launch: -p image_width:=640 -p image_height:=480

# Lower detection rate
self.create_timer(0.1, self.control_loop)  # 10 Hz instead of 20 Hz
```

### For High-End Hardware
```python
# Use larger YOLO model for better accuracy
self.yolo_model = YOLO('yolov8l.pt')

# Higher resolution camera
# Use full HD: 1920x1080
```

## 🧪 Testing Scenarios

### Test 1: Pure Manual Control
1. Disable avoidance (press V)
2. Drive robot with WASD/Xbox
3. Verify all directions work

### Test 2: Static Human Detection
1. Enable avoidance (press V)
2. Enable camera view (press C)
3. Place human in front of camera
4. Verify detection appears with bounding box

### Test 3: Dynamic Avoidance
1. Enable avoidance
2. Drive forward (W)
3. Have person walk into path
4. Robot should automatically strafe away

### Test 4: Xbox Controller
1. Connect Xbox controller
2. Test all stick movements
3. Test button toggles (A/B/Y)

## 📝 Example Output

```
==========================================================
   🎮 TESTER104: MANUAL CONTROL + SOCIAL AVOIDANCE      
==========================================================
   
✅ YOLO model loaded successfully
✅ Xbox controller connected: Xbox 360 Controller
🚀 Social Avoidance Teleop Active
   Avoidance: ENABLED
   YOLO: AVAILABLE
   Xbox Controller: CONNECTED

Status: ⬆️  MAJU      | Avoidance: 2 humans
```

## 📊 ROS2 Topics

### Published Topics
- `/cmd_vel` (geometry_msgs/Twist) - Robot velocity commands
- `/teleop_status` (std_msgs/String) - Teleop status information

### Subscribed Topics
- `/camera/image_raw` (sensor_msgs/Image) - Camera image stream

## 🎯 Future Enhancements

- [ ] Dynamic speed adjustment based on human proximity
- [ ] Multi-human tracking with unique IDs
- [ ] Predictive avoidance (anticipate human movement)
- [ ] 3D obstacle avoidance (depth camera integration)
- [ ] Gesture recognition for interaction
- [ ] Voice commands integration
- [ ] Path planning with social cost maps

## 📚 References

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
- [ROS2 Humble](https://docs.ros.org/en/humble/)
- [Social Force Model](https://en.wikipedia.org/wiki/Social_force_model)

---

**Version:** 1.0  
**Created:** 2026-09-27  
**Author:** Tester104 Team  
**License:** MIT
