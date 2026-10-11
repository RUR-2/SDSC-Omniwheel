# 🚀 Quick Start Guide - Bluetooth SDSC

Panduan cepat untuk menjalankan Bluetooth SDSC Controller dalam 5 menit.

---

## ⚡ Prerequisites Check

Pastikan Anda memiliki:
- ✅ Linux PC (Ubuntu 20.04/22.04)
- ✅ Intel RealSense camera (D435/D455)
- ✅ USB Joystick/Gamepad
- ✅ ESP32 robot dengan Bluetooth paired

---

## 📦 Installation (5 menit)

### Option 1: Automatic (Recommended)
```bash
# Run installation script
bash install_sdsc.sh

# Logout/login untuk apply group changes
```

### Option 2: Manual
```bash
# Install dependencies
pip3 install -r requirements_sdsc.txt

# Install RealSense (Ubuntu)
sudo apt install librealsense2-dkms librealsense2-utils python3-pyrealsense2

# Download YOLO model
python3 -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

---

## 🔧 Setup (2 menit)

### 1. Setup Bluetooth
```bash
# Scan untuk MAC address ESP32
sudo hcitool scan

# Output example:
# Scanning ...
#   24:6F:28:XX:XX:XX	ESP32-Robot

# Bind rfcomm (ganti XX:XX:XX dengan MAC address Anda)
sudo rfcomm bind /dev/rfcomm0 24:6F:28:XX:XX:XX 1

# Set permissions
sudo chmod 666 /dev/rfcomm0

# Verify
ls -l /dev/rfcomm0
```

### 2. Connect Hardware
- Plug RealSense camera (USB 3.0 - **biru**)
- Plug joystick (USB)
- Power on ESP32 robot

### 3. Test Components (optional)
```bash
python3 test_components.py
```

---

## ▶️ Run (30 detik)

### Start Controller
```bash
python3 bluetooth_sdsc.py
```

### GUI Steps:
1. **Refresh** button → Pilih `/dev/rfcomm0`
2. **Connect** button → Status berubah "Connected"
3. **Joystick** akan terdeteksi otomatis
4. **OpenCV window** akan muncul menampilkan deteksi

### Control:
- **Hold B4** (deadman switch)
- **Move left stick** untuk forward/back + strafe left/right
- **Press B6/B7** untuk rotate
- Robot akan **otomatis menghindari manusia**

---

## 🎯 Expected Behavior

### Normal Operation:
```
[12:34:56] ✅ All systems initialized
[12:34:57] 📷 Camera: 640x480 @ 30fps
[12:34:58] 🧠 YOLO: yolo11n.pt
[12:34:59] Ready for operation!
[12:35:00] Detected 2 humans | ID1:(1.2,0.5)@1.5m, ID2:(2.0,-0.3)@2.1m
[12:35:01] 🟡 SOCIAL ZONE (1.52m) - AVOIDING (70%)
```

### GUI Status Display:
```
Humans: 2
Closest: 1.52m
Zone: SOCIAL
Repulsion: 3.45N
```

### OpenCV Window:
- Bounding boxes pada manusia (hijau)
- ID tracking (ID0, ID1, ...)
- Distance dalam meter
- Position (x, y) dalam robot frame
- Zone indicator (colored circle):
  - 🔴 Red = INTIMATE (< 0.45m)
  - 🟠 Orange = PERSONAL (< 1.2m)
  - 🟡 Yellow = SOCIAL (< 3.6m)
  - 🟢 Green = PUBLIC (> 3.6m)
- Force vector (magenta arrow)

---

## ⚙️ Quick Tuning

Edit `bluetooth_sdsc.py` bagian `CONFIGURATION`:

### Make robot MORE conservative (safer):
```python
SFM_A = 8.0              # Increase repulsion
R_INTIMATE = 0.60        # Larger stop zone
SPEED_SCALE = 0.3        # Slower overall
```

### Make robot MORE aggressive (faster):
```python
SFM_A = 3.0              # Decrease repulsion
R_INTIMATE = 0.30        # Smaller stop zone
SPEED_SCALE = 0.7        # Faster overall
```

### Reduce false detections:
```python
YOLO_CONFIDENCE = 0.6    # Higher threshold
```

---

## 🐛 Common Issues

### ❌ "No such file or directory: /dev/rfcomm0"
```bash
sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1
sudo chmod 666 /dev/rfcomm0
```

### ❌ "Permission denied: /dev/rfcomm0"
```bash
sudo chmod 666 /dev/rfcomm0
# Or add to dialout group:
sudo usermod -a -G dialout $USER
# Logout/login
```

### ❌ "No RealSense device connected"
- Check USB 3.0 connection (blue port)
- Try different USB port
- Replug camera
- Run: `realsense-viewer`

### ❌ "No joystick connected"
- Check USB connection
- Run: `ls /dev/input/js*`
- Test: `jstest /dev/input/js0`

### ❌ Robot jerky/oscillating
```python
SFM_A = 3.0           # Reduce repulsion
SFM_TAU = 0.8         # Increase relaxation
```

### ❌ Robot gets too close
```python
SFM_A = 8.0           # Increase repulsion
R_INTIMATE = 0.60     # Larger stop zone
```

### ❌ Slow inference
- Check CUDA: `python3 -c "import torch; print(torch.cuda.is_available())"`
- Reduce resolution: `CAMERA_WIDTH = 424, CAMERA_HEIGHT = 240`
- Reduce detection rate: `DETECTION_RATE_HZ = 5`

---

## 📊 Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Detection FPS | 10 Hz | 8-12 Hz |
| YOLO inference | < 50ms | 30-40ms (GPU) |
| Control rate | 20 Hz | 20 Hz |
| Latency (joystick→robot) | < 100ms | 60-80ms |

---

## 🎓 Next Steps

### Learn More:
- Read `README_SDSC.md` untuk dokumentasi lengkap
- Study Social Force Model theory
- Experiment dengan parameter tuning

### Extend:
- Integrate dengan ROS 2
- Add path planning (A* + SFM)
- Implement velocity prediction
- Multi-robot coordination

### Debug:
- Check log window untuk errors
- Use `test_components.py` untuk isolate issues
- Review packet format di serial monitor

---

## 📝 Cheat Sheet

### Bluetooth Commands
```bash
# Scan devices
sudo hcitool scan

# Bind rfcomm
sudo rfcomm bind /dev/rfcomm0 <MAC> 1

# Release rfcomm
sudo rfcomm release /dev/rfcomm0

# Check status
rfcomm -a
```

### Camera Commands
```bash
# Launch viewer
realsense-viewer

# List devices
rs-enumerate-devices

# Check USB
lsusb | grep Intel
```

### Python Quick Tests
```bash
# Test imports
python3 -c "import pygame, serial, cv2, torch, pyrealsense2; print('OK')"

# Test CUDA
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"

# Test joystick
python3 -c "import pygame; pygame.init(); pygame.joystick.init(); print(pygame.joystick.get_count())"
```

---

## 🆘 Getting Help

1. Check troubleshooting di `README_SDSC.md`
2. Run `python3 test_components.py all`
3. Check log window untuk specific errors
4. Review hardware connections
5. Test individual components separately

---

## 🎉 Success Criteria

Anda berhasil jika:
- ✅ GUI shows "Connected" untuk Bluetooth
- ✅ Joystick terdeteksi dan input responsive
- ✅ OpenCV window menampilkan camera feed
- ✅ Manusia terdeteksi dengan bounding box dan distance
- ✅ Robot bisa bergerak dengan deadman switch
- ✅ Robot melambat/berhenti saat mendekati manusia
- ✅ Force vector terlihat di visualization
- ✅ Zone indicators berubah warna sesuai jarak

**Happy Social Navigation! 🤖🚀**

---

*Last updated: 2024-12-31*
*Version: 2.0*
