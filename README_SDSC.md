# Bluetooth SDSC Controller
## Social-Dynamic System Control dengan Proxemic Zones

Sistem kontrol robot omniwheel via Bluetooth dengan integrasi **Social Force Model** untuk human-aware navigation.

---

## 🎯 Fitur Utama

### 1. **Bluetooth Joystick Control**
- Kontrol manual menggunakan joystick via Bluetooth (rfcomm)
- Deadman switch (B4) untuk keamanan
- Left stick: forward/backward + strafe left/right
- B6/B7: rotasi CCW/CW

### 2. **Human Detection & Tracking**
- **YOLOv11 nano** untuk deteksi manusia real-time
- **Intel RealSense** depth camera untuk pengukuran jarak 3D
- Simple tracking dengan ID assignment
- Transformasi koordinat pixel → camera frame → robot frame

### 3. **Social Force Model (Helbing & Molnar 1995)**
- Repulsive force dari setiap manusia terdeteksi
- Formula: `F_rep = A × exp(-d/B) × n̂`
- Parameters:
  - `A = 5.0 N` (magnitude)
  - `B = 0.8 m` (range)
  - `τ = 0.5 s` (relaxation time)

### 4. **Proxemic Zones (Edward T. Hall 1966)**
| Zone | Radius | Behavior | Speed Scale |
|------|--------|----------|-------------|
| **Intimate** | < 0.45m | 🔴 Emergency STOP | 0% |
| **Personal** | < 1.20m | 🟠 Slow down | 30% |
| **Social** | < 3.60m | 🟡 Active avoidance | 70% |
| **Public** | > 3.60m | 🟢 Normal operation | 100% |

### 5. **Real-time Visualization**
- OpenCV window dengan annotated detections
- Bounding boxes + ID + distance
- Proxemic zone indicators (color-coded)
- Repulsive force vector visualization
- Tkinter GUI untuk status monitoring

---

## 📋 Requirements

### Hardware
1. **Robot**: ESP32 + 4x Mecanum wheels (Omniwheel)
2. **Camera**: Intel RealSense D435/D455 (atau model depth camera lainnya)
3. **Controller**: USB Joystick/Gamepad (tested dengan Logitech F310)
4. **Computer**: Linux PC dengan Bluetooth (Ubuntu 20.04/22.04 recommended)

### Software
- Python 3.8+
- CUDA 11.8+ (optional, untuk YOLO acceleration)
- RealSense SDK 2.54+

---

## 🚀 Installation

### 1. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements_sdsc.txt

# Install RealSense SDK (Ubuntu)
sudo apt-key adv --keyserver keys.gnupg.net --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE
sudo add-apt-repository "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -sc) main"
sudo apt update
sudo apt install librealsense2-dkms librealsense2-utils librealsense2-dev

# Test RealSense
realsense-viewer

# Download YOLOv11 model (otomatis saat pertama run)
# Model akan di-download ke: ~/.ultralytics/models/yolo11n.pt
```

### 2. Setup Bluetooth (rfcomm)
```bash
# Scan untuk MAC address ESP32
sudo hcitool scan

# Bind rfcomm (ganti <MAC_ESP32> dengan MAC address dari scan)
sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1

# Contoh:
# sudo rfcomm bind /dev/rfcomm0 24:6F:28:XX:XX:XX 1

# Verify
ls -l /dev/rfcomm0

# Set permissions
sudo chmod 666 /dev/rfcomm0
```

### 3. Test Components

#### Test Joystick
```bash
# List joystick devices
python3 -c "import pygame; pygame.init(); pygame.joystick.init(); print(f'Found {pygame.joystick.get_count()} joystick(s)')"
```

#### Test RealSense
```bash
# Run RealSense viewer
realsense-viewer

# Atau test dengan Python
python3 -c "import pyrealsense2 as rs; pipe = rs.pipeline(); pipe.start(); print('RealSense OK'); pipe.stop()"
```

#### Test YOLO
```bash
# Download model dan test inference
python3 -c "from ultralytics import YOLO; model = YOLO('yolo11n.pt'); print('YOLO OK')"
```

---

## 🎮 Usage

### Basic Operation
```bash
# Run the controller
python3 bluetooth_sdsc.py
```

### Step-by-step:
1. **Refresh Ports** → Pilih `/dev/rfcomm0`
2. **Connect** → Establish Bluetooth connection
3. **Connect Joystick** → Plug in USB joystick (auto-detected)
4. **Hold B4** (deadman switch) + Move left stick
5. Robot akan **otomatis menghindari manusia** yang terdeteksi

### GUI Controls:
- **Refresh**: Scan ulang port serial
- **Connect/Disconnect**: Toggle Bluetooth connection
- **Status Panel**: Menampilkan jumlah manusia, jarak terdekat, zone, dan gaya repulsif
- **Log Window**: Event logging real-time

### OpenCV Window:
- Menampilkan deteksi manusia dengan:
  - Bounding box (hijau)
  - ID tracking (ID0, ID1, ...)
  - Distance (meter)
  - Position (x, y) dalam robot frame
  - Zone indicator (colored circle)
  - Repulsive force vector (magenta arrow)
- **Press 'q'** untuk close window

---

## ⚙️ Configuration

Edit parameter di bagian `CONFIGURATION` dalam `bluetooth_sdsc.py`:

### Joystick Mapping
```python
AXIS_X = 0              # Left stick horizontal
AXIS_Y = 1              # Left stick vertical
BTN_ROT_LEFT = 6        # Button untuk CCW rotation
BTN_ROT_RIGHT = 7       # Button untuk CW rotation
BTN_DEADMAN = 4         # Hold untuk enable motion
```

### Social Force Model Tuning
```python
SFM_A = 5.0             # ⬆️ Increase = stronger repulsion
SFM_B = 0.8             # ⬆️ Increase = wider repulsion range
SFM_MASS = 5.0          # Robot mass (kg)
SFM_TAU = 0.5           # Relaxation time (seconds)
```

### Proxemic Zones
```python
R_INTIMATE = 0.45       # ⬆️ Increase = safer (more conservative)
R_PERSONAL = 1.20       
R_SOCIAL = 3.60         

INTIMATE_SPEED_SCALE = 0.0   # 0.0 = full stop
PERSONAL_SPEED_SCALE = 0.3   # 0.3 = 30% speed
SOCIAL_SPEED_SCALE = 0.7     # 0.7 = 70% speed
```

### Detection Parameters
```python
YOLO_CONFIDENCE = 0.5        # ⬆️ Increase = fewer false positives
DETECTION_RATE_HZ = 10       # Detection frequency (Hz)
MIN_DISTANCE = 0.1           # Ignore closer than (m)
MAX_DISTANCE = 10.0          # Ignore farther than (m)
```

---

## 🧪 Tuning Guide

### Problem: Robot terlalu dekat dengan manusia
**Solution:**
- ⬆️ Increase `SFM_A` (e.g., 8.0)
- ⬆️ Increase `R_INTIMATE` (e.g., 0.60m)
- ⬆️ Increase `SFM_B` (e.g., 1.0)

### Problem: Robot terlalu takut / menghindari terlalu jauh
**Solution:**
- ⬇️ Decrease `SFM_A` (e.g., 3.0)
- ⬇️ Decrease `SFM_B` (e.g., 0.5)
- ⬇️ Decrease `R_SOCIAL` (e.g., 2.5m)

### Problem: Gerakan jerky / oscillations
**Solution:**
- ⬇️ Decrease `SFM_A` (e.g., 3.0)
- ⬆️ Increase `SFM_TAU` (e.g., 0.8)
- ⬇️ Decrease `SPEED_SCALE` (e.g., 0.3)

### Problem: False detections
**Solution:**
- ⬆️ Increase `YOLO_CONFIDENCE` (e.g., 0.6 atau 0.7)
- Ensure good lighting
- Clean camera lens

### Problem: Detection lag
**Solution:**
- ⬆️ Increase `DETECTION_RATE_HZ` (e.g., 15)
- Use smaller YOLO model (already using nano)
- Consider CUDA acceleration

---

## 📊 Packet Format

Data dikirim ke ESP32 via Bluetooth dalam format:
```
<x,y,w>\n
```

- `x` = lateral velocity (0-255, center=127, left is positive)
- `y` = forward velocity (0-255, center=127, forward is positive)
- `w` = angular velocity (0-255, center=127, CCW is positive)
- `\n` = newline terminator

**Example:**
- `<127,127,127>` = STOP
- `<127,200,127>` = Forward
- `<200,127,127>` = Strafe left
- `<127,127,180>` = Rotate CCW

---

## 🔧 Troubleshooting

### Bluetooth Issues

**Problem: `/dev/rfcomm0` not found**
```bash
# Re-bind rfcomm
sudo rfcomm release /dev/rfcomm0
sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1
```

**Problem: Permission denied**
```bash
sudo chmod 666 /dev/rfcomm0
# Or add user to dialout group:
sudo usermod -a -G dialout $USER
# Then logout/login
```

**Problem: Connection failed**
```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# Restart if needed
sudo systemctl restart bluetooth

# Test connection manually
sudo rfcomm connect /dev/rfcomm0 <MAC_ESP32> 1
```

### Camera Issues

**Problem: RealSense not detected**
```bash
# Check USB connection
lsusb | grep Intel

# Check permissions
sudo udevadm control --reload-rules
sudo udevadm trigger

# Replug camera
```

**Problem: "No device connected" error**
```bash
# Update firmware
realsense-viewer
# Tools → Firmware Update

# Or reinstall driver
sudo apt remove librealsense2*
sudo apt install librealsense2-dkms librealsense2-utils
```

### YOLO Issues

**Problem: Model download stuck**
```bash
# Download manually
mkdir -p ~/.ultralytics/models
cd ~/.ultralytics/models
wget https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.pt
```

**Problem: CUDA out of memory**
- YOLOv11 nano sudah sangat kecil, seharusnya tidak issue
- Atau gunakan CPU inference (otomatis fallback)

### Performance Issues

**Problem: Slow inference**
```bash
# Check CUDA availability
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Reduce resolution (dalam code)
CAMERA_WIDTH = 424
CAMERA_HEIGHT = 240
```

**Problem: High CPU usage**
```bash
# Reduce detection rate
DETECTION_RATE_HZ = 5

# Disable visualization
SHOW_DETECTION_WINDOW = False
```

---

## 📚 Technical Details

### Coordinate Frames

#### Camera Frame (RealSense)
- **X**: Right (+)
- **Y**: Down (+)
- **Z**: Forward (+)

#### Robot Frame
- **X**: Forward (+)
- **Y**: Left (+)
- **Z**: Up (+)

**Transformation:**
```python
robot_x = camera_z
robot_y = -camera_x
robot_z = -camera_y
```

### Social Force Model

**Goal Force** (driving force):
```
F_goal = (m/τ) × (v_desired - v_current)
```

**Repulsive Force** (human avoidance):
```
F_rep = A × exp(-d/B) × n̂
where:
  d = distance to human
  n̂ = unit vector (robot → away from human)
```

**Total Force:**
```
F_total = F_goal + Σ F_rep_i
```

**Velocity Update** (Euler integration):
```
a = F_total / m
v_new = v_old + a × dt
```

### Tracking Algorithm

Simple centroid-based tracking:
1. For each new detection, compute centroid (cx, cy)
2. Find closest existing track within `TRACKING_THRESHOLD_PX`
3. If match found: update track with new position
4. If no match: create new ID
5. Remove tracks not seen for > `TRACKING_TIMEOUT` seconds

This is **NOT** a robust multi-object tracker (like SORT/DeepSORT), but sufficient untuk demo.

---

## 🎓 References

1. **Social Force Model**:
   - Helbing, D., & Molnár, P. (1995). "Social force model for pedestrian dynamics." Physical Review E, 51(5), 4282.

2. **Proxemic Zones**:
   - Hall, E. T. (1966). "The Hidden Dimension." Doubleday.

3. **YOLOv11**:
   - Ultralytics. (2024). "YOLOv11: State-of-the-art object detection."

4. **Intel RealSense**:
   - Intel. "Intel RealSense SDK 2.0 Documentation."

---

## 📝 TODO / Future Work

- [ ] Implement proper multi-object tracking (SORT/DeepSORT)
- [ ] Add velocity prediction untuk humans (predictive SFM)
- [ ] Integrate dengan ROS 2 (untuk autonomy stack)
- [ ] Add trajectory recording & replay
- [ ] Implement formation control (multiple robots)
- [ ] Add RViz visualization markers
- [ ] Support multiple camera viewpoints
- [ ] Machine learning-based force tuning
- [ ] Add telemetry logging (CSV export)
- [ ] Implement path planning dengan A* + SFM

---

## 👥 Authors

**Brone Social Nav Team**
- Social-Dynamic System Control (SDSC)
- Version 2.0 - December 2024

---

## 📄 License

MIT License - Free to use and modify

---

## 🆘 Support

Jika ada pertanyaan atau issue:
1. Check troubleshooting section di atas
2. Review log output di GUI window
3. Test individual components (joystick, camera, YOLO) separately
4. Check hardware connections (USB, Bluetooth)

**Happy Social Navigation! 🤖🚀**
