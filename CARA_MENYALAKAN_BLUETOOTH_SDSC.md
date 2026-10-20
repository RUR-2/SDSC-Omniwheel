# 🚀 Cara Menyalakan Bluetooth SDSC (bluetooth_sdsc.py)

## 📋 Panduan Lengkap Step-by-Step

---

## 🔧 PERSIAPAN AWAL

### 1. **Cek Hardware yang Dibutuhkan**

**Checklist:**
- [ ] Laptop/PC Windows dengan Python 3
- [ ] Intel RealSense Camera (terhubung via USB)
- [ ] Gamepad/Joystick (Bluetooth atau USB)
- [ ] Robot dengan ESP32 + Bluetooth module
- [ ] Model YOLO (`yolo11n.pt` ada di folder project)

---

## 📦 INSTALASI DEPENDENCIES (Sekali Saja)

### Step 1: Install Python Dependencies

Buka Command Prompt di folder project, lalu:

```cmd
cd "d:\Vroomniwheel\SDSC Omniwheel"
pip install -r requirements_sdsc.txt
```

**Isi requirements_sdsc.txt:**
```
pygame
pyserial
opencv-python
numpy
pyrealsense2
ultralytics
```

Atau install manual satu per satu:
```cmd
pip install pygame
pip install pyserial
pip install opencv-python
pip install numpy
pip install pyrealsense2
pip install ultralytics
```

### Step 2: Download YOLO Model (Jika Belum Ada)

```cmd
cd "d:\Vroomniwheel\SDSC Omniwheel"

REM Check apakah sudah ada
dir yolo11n.pt

REM Jika belum ada, download otomatis saat pertama kali run
REM Atau download manual dari:
REM https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11n.pt
```

### Step 3: Test RealSense Camera

```cmd
REM Install RealSense SDK (jika belum):
REM https://github.com/IntelRealSense/librealsense/releases

REM Test camera:
realsense-viewer
```

**Pastikan camera terdeteksi dan menampilkan video!**

---

## 🔌 KONEKSI BLUETOOTH KE ROBOT

### **Opsi A: Windows Native Bluetooth**

#### Step 1: Pair ESP32 via Windows Settings

1. Buka **Settings** → **Devices** → **Bluetooth & other devices**
2. Klik **Add Bluetooth or other device**
3. Pilih **Bluetooth**
4. Cari nama ESP32 (biasanya: "ESP32_SDSC" atau "HC-05")
5. Masukkan PIN jika diminta (default: `1234` atau `0000`)
6. Wait sampai status "Connected"

#### Step 2: Cek COM Port

1. Buka **Device Manager**
2. Expand **Ports (COM & LPT)**
3. Cari "Standard Serial over Bluetooth link (COMx)"
4. **Catat nomor COM port** (misal: COM5)

#### Step 3: Test Koneksi

```cmd
REM Test apakah port bisa dibuka
python -c "import serial; s=serial.Serial('COM5', 115200, timeout=1); print('OK'); s.close()"
```

---

### **Opsi B: Linux/WSL (rfcomm)**

Jika pakai Linux atau WSL di Windows:

#### Step 1: Setup rfcomm

```bash
# Install bluez
sudo apt-get install bluez bluez-tools rfkill

# Enable bluetooth
sudo rfkill unblock bluetooth
sudo systemctl start bluetooth

# Scan for devices
sudo hcitool scan
# Catat MAC address ESP32 (misal: 98:D3:31:F5:9A:8C)
```

#### Step 2: Bind rfcomm

```bash
# Bind to rfcomm0
sudo rfcomm bind 0 98:D3:31:F5:9A:8C 1

# Check
ls -l /dev/rfcomm0
# Should show: crw-rw---- 1 root dialout ...
```

#### Step 3: Connect

```bash
# Connect (this blocks, so run in separate terminal)
sudo rfcomm connect 0 98:D3:31:F5:9A:8C 1

# Output should show:
# Connected /dev/rfcomm0 to 98:D3:31:F5:9A:8C on channel 1
# Press CTRL-C for hangup
```

---

## ▶️ MENJALANKAN bluetooth_sdsc.py

### **Method 1: GUI Mode (Recommended)**

#### Step 1: Buka Terminal/CMD

```cmd
cd "d:\Vroomniwheel\SDSC Omniwheel"
```

#### Step 2: Jalankan Script

```cmd
python bluetooth_sdsc.py
```

#### Step 3: GUI Window Muncul

Window akan muncul dengan judul:
```
Bluetooth SDSC Controller v1.1 - Social Force Navigation [Improved: 3x Faster Evasion]
```

#### Step 4: Connect Bluetooth

Di GUI:
1. **Klik tombol "Refresh"** - Scan available ports
2. **Pilih port** dari dropdown (Windows: COMx, Linux: /dev/rfcommx)
3. **Klik "Connect"**
4. Status akan berubah: `Bluetooth: Connected to COMx [135° CW rotation active]`

#### Step 5: Connect Gamepad

1. Nyalakan gamepad (Bluetooth atau USB)
2. Tunggu beberapa detik
3. Status di GUI akan berubah: `Controller connected: <gamepad name>`

#### Step 6: Test Movement

1. **Hold B4 (deadman button)** - biasanya tombol belakang kiri
2. **Move left stick** - robot akan bergerak
3. **Release B4** - robot stop

---

### **Method 2: Command Line Mode**

Jika tidak mau pakai GUI:

```cmd
python -c "
import bluetooth_sdsc
# Auto-connect mode akan dijalankan
"
```

---

## 🎮 KONTROL GAMEPAD

### **Layout Tombol:**

```
┌─────────────────────────────────────────────────┐
│                                                 │
│    B6 (Rotate Left)         B7 (Rotate Right)  │
│           ↺                        ↻            │
│                                                 │
│         Left Stick                              │
│      ↑ Forward (Y)                              │
│      ↓ Backward                                 │
│   ← Strafe Left (X)                             │
│   → Strafe Right                                │
│                                                 │
│   B4 (DEADMAN - Hold to Enable)                 │
│   [●]                                           │
│                                                 │
└─────────────────────────────────────────────────┘
```

### **Cara Pakai:**

1. **Hold B4** sepanjang waktu untuk enable robot
2. **Push left stick forward/back** untuk maju/mundur
3. **Push left stick left/right** untuk strafe
4. **Press B6/B7** untuk rotasi
5. **Release B4** untuk immediate stop

**⚠️ PENTING:** Robot **HANYA BERGERAK** saat B4 ditekan (safety feature!)

---

## 📹 VISUALISASI CAMERA

Setelah script jalan, akan muncul **2 windows**:

### **Window 1: GUI Control Panel**
- Bluetooth connection status
- Gamepad status
- Social Force status (humans, distance, zone)
- Log output

### **Window 2: Camera Visualization (OpenCV)**
- Video feed dari RealSense
- Bounding boxes untuk detected humans
- Distance label
- Proxemic zone indicator (color-coded circles)
- Force vector (purple arrow)

**Color Codes:**
- 🟢 **Green circle** = PUBLIC zone (>3.6m)
- 🟡 **Yellow circle** = SOCIAL zone (1.2-3.6m)
- 🟠 **Orange circle** = PERSONAL zone (0.45-1.2m)
- 🔴 **Red circle** = INTIMATE zone (<0.45m) ⚠️

---

## 📊 MONITORING OUTPUT

### **Terminal Log Examples:**

```
[12:34:56] ✅ Joystick: Xbox 360 Controller
[12:34:57] Loading YOLOv11 model...
[12:34:59] ✅ Camera initialized: 640x480
[12:35:00] ✅ Detection thread started
[12:35:02] Bluetooth: Connected to COM5 [135° CW rotation active]
```

**Saat Ada Human Terdeteksi:**
```
[12:35:10] 🟢 EARLY EVASION (3.42m) - PREPARING (80%)
[12:35:11] 🟡 SOCIAL ZONE (2.85m) - AVOIDING (60%)
[12:35:12] 🟠 PERSONAL ZONE (1.15m) - SLOW DOWN (30%)
```

**Ini yang TIDAK boleh muncul:**
```
[12:35:13] 🔴 INTIMATE ZONE (0.38m) - EMERGENCY STOP  ❌ BAD!
```

---

## ⚙️ KONFIGURASI PARAMETER (Optional)

Jika mau adjust behavior, edit file `bluetooth_sdsc.py`:

### **Ganti Control Speed:**

```python
# Line ~63-65
SPEED_SCALE = 0.5      # 0.3 = slower, 0.7 = faster
ROT_SCALE = 0.5        # Rotation speed
STICK_DEADZONE = 0.12  # Smaller = more sensitive
```

### **Ganti Safety Zones:**

```python
# Line ~100-110
R_INTIMATE = 0.45      # Emergency stop distance
R_PERSONAL = 1.20      # Slow down distance
R_SOCIAL = 3.60        # Avoidance distance
R_EVASION_START = 3.50 # Early evasion start
```

### **Ganti Force Multipliers:**

```python
# Line ~115-118
LATERAL_MULTIPLIER_SOCIAL = 3.0   # 2.0 = gentle, 4.0 = aggressive
LATERAL_MULTIPLIER_PERSONAL = 5.0 # Critical zone response
```

---

## 🔍 TROUBLESHOOTING

### **Problem 1: Script Tidak Jalan**

**Error:** `ModuleNotFoundError: No module named 'pygame'`

**Solusi:**
```cmd
pip install pygame pyserial opencv-python numpy pyrealsense2 ultralytics
```

---

### **Problem 2: Camera Tidak Terdeteksi**

**Error:** `RuntimeError: No RealSense devices detected`

**Solusi:**
1. Cek USB cable terhubung
2. Test dengan `realsense-viewer`
3. Install RealSense SDK dari: https://github.com/IntelRealSense/librealsense/releases
4. Restart laptop

---

### **Problem 3: Bluetooth Tidak Connect**

**Error:** `Serial Exception: could not open port COMx`

**Solusi Windows:**
1. Buka Device Manager
2. Cek apakah "Standard Serial over Bluetooth link" ada
3. Right-click → Properties → Port Settings
4. Set Bits per second: 115200
5. Restart Bluetooth service:
   ```cmd
   net stop bthserv
   net start bthserv
   ```

**Solusi Linux:**
```bash
# Re-bind rfcomm
sudo rfcomm release 0
sudo rfcomm bind 0 <MAC_ADDRESS> 1
sudo rfcomm connect 0 <MAC_ADDRESS> 1
```

---

### **Problem 4: Gamepad Tidak Terdeteksi**

**Error:** `Controller disconnected`

**Solusi:**
1. Pastikan gamepad dalam mode pairing
2. Check di Windows Game Controllers settings
3. Test dengan `joy.cpl` (Windows)
4. Restart script

**Test gamepad in Python:**
```python
import pygame
pygame.init()
pygame.joystick.init()
print(f"Joysticks: {pygame.joystick.get_count()}")
if pygame.joystick.get_count() > 0:
    j = pygame.joystick.Joystick(0)
    j.init()
    print(f"Name: {j.get_name()}")
```

---

### **Problem 5: Detection Tidak Jalan**

**Error:** Detection rate 0%, No humans detected

**Solusi:**
1. Pastikan YOLO model ada: `dir yolo11n.pt`
2. Check camera window shows video
3. Stand di depan camera (1-3 meter)
4. Check lighting (terlalu gelap?)
5. Check confidence threshold:
   ```python
   YOLO_CONFIDENCE = 0.5  # Lower = more detections (0.3)
   ```

---

### **Problem 6: Robot Tidak Bergerak**

**Possible Causes:**
1. **Deadman not pressed** - Hold B4!
2. **ESP32 not receiving** - Check serial monitor
3. **Window not focused** - Click GUI window
4. **Bluetooth disconnected** - Check status

**Debug:**
```python
# Add print statement in build_packet_with_sfm():
print(f"Packet: {packet}")  # Should show <x,y,w>
```

---

## 📋 CHECKLIST STARTUP

Sebelum jalankan, pastikan:

- [ ] Python 3 installed
- [ ] All pip packages installed
- [ ] RealSense camera terhubung & tested
- [ ] Gamepad terhubung & tested
- [ ] ESP32 powered on
- [ ] Bluetooth paired (Windows) atau rfcomm bound (Linux)
- [ ] yolo11n.pt ada di folder
- [ ] Lighting cukup untuk detection
- [ ] Open space untuk testing (min 3x3 meter)

---

## 🚀 QUICK START COMMAND

**Windows - Satu Perintah:**
```cmd
cd "d:\Vroomniwheel\SDSC Omniwheel" && python bluetooth_sdsc.py
```

**Linux/WSL:**
```bash
cd /mnt/d/Vroomniwheel/SDSC\ Omniwheel
python3 bluetooth_sdsc.py
```

---

## 🎯 TESTING FLOW

### **Step-by-Step First Test:**

1. **Jalankan script**
   ```cmd
   python bluetooth_sdsc.py
   ```

2. **Wait for initialization**
   - Camera starts: ✅
   - YOLO loads: ✅
   - Detection thread: ✅

3. **Connect Bluetooth**
   - Refresh ports
   - Select COM/rfcomm
   - Click Connect
   - Status: Connected ✅

4. **Connect Gamepad**
   - Status: Controller connected ✅

5. **Test tanpa manusia**
   - Hold B4
   - Move stick forward
   - Robot bergerak ✅
   - Release B4
   - Robot stop ✅

6. **Test dengan manusia**
   - Stand 4m di depan robot
   - Hold B4
   - Drive forward slowly
   - Watch terminal:
     - 🟢 EARLY EVASION at ~3.5m
     - 🟡 SOCIAL at ~3.0m
     - Robot bergerak ke samping ✅
   - Min distance > 0.6m ✅

---

## 📞 SUPPORT

Jika masih ada masalah:

1. **Check log file** (jika ada error stack trace)
2. **Try different USB port** (untuk camera)
3. **Try different COM port** (untuk bluetooth)
4. **Restart semua hardware** (camera, ESP32, gamepad)
5. **Check Python version**: `python --version` (need 3.7+)

---

## 🎊 SUCCESS!

Jika sudah jalan, kamu akan lihat:

✅ GUI window terbuka  
✅ Camera window menampilkan video + detections  
✅ Gamepad terdeteksi  
✅ Bluetooth connected  
✅ Robot bergerak saat B4 ditekan  
✅ Robot menghindar saat ada manusia  
✅ Terminal menampilkan zone transitions  

**SELAMAT! Sistem sudah ready untuk dipakai! 🎉**

---

## 📚 REFERENSI

- **Full Integration Details:** `BLUETOOTH_INTEGRATION_COMPLETE.md`
- **Visual Comparison:** `INTEGRATION_VISUAL_SUMMARY.md`
- **Testing Guide:** `TESTING_QUICK_START.txt`
- **Project Summary:** `PROJECT_SUMMARY.md`

---

**Version:** bluetooth_sdsc.py v2.1.1  
**Date:** 2026-10-11  
**Status:** ✅ READY TO USE

---

*"Hold B4, move stick, avoid humans - that's it!"* 🚀
