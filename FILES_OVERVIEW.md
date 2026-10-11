# 📁 Bluetooth SDSC - File Overview

Dokumentasi lengkap semua file yang dibuat untuk Bluetooth SDSC Controller.

---

## 🎯 Main Files

### `bluetooth_sdsc.py` ⭐
**File utama** - Controller dengan Social Force Model + Proxemic Zones

**Features:**
- Bluetooth joystick control
- YOLOv11 human detection
- Intel RealSense depth camera integration
- Social Force Model untuk avoidance
- Proxemic zones (Intimate/Personal/Social/Public)
- Real-time OpenCV visualization
- Enhanced Tkinter GUI
- Multi-threaded detection
- Event logging

**Usage:**
```bash
python3 bluetooth_sdsc.py
```

**Lines:** ~800 lines
**Dependencies:** pygame, pyserial, opencv-python, ultralytics, torch, pyrealsense2, numpy

---

### `bluetooth.py` (Original)
**File asli** - Basic Bluetooth joystick control tanpa social navigation

**Features:**
- Basic joystick control via Bluetooth
- Simple Tkinter GUI
- Axis/button visualization
- Deadman switch

**Status:** Retained untuk backward compatibility
**Usage:** Untuk control dasar tanpa camera/detection

---

## 📚 Documentation Files

### `README_SDSC.md`
**Dokumentasi lengkap** - Comprehensive documentation

**Contents:**
- Feature overview (4 main features)
- Hardware & software requirements
- Installation guide (step-by-step)
- Usage instructions
- Configuration reference
- Tuning guide (problem-solution pairs)
- Packet format specification
- Troubleshooting (Bluetooth, Camera, YOLO, Performance)
- Technical details (coordinate frames, SFM equations, tracking algorithm)
- References (academic papers)
- TODO / Future work
- Support information

**Length:** ~500 lines
**Target:** Complete reference untuk users dan developers

---

### `QUICKSTART.md`
**Quick start guide** - Get running in 5 minutes

**Contents:**
- Prerequisites checklist
- Installation (automatic & manual)
- Setup (Bluetooth, hardware)
- Run instructions
- Expected behavior
- Quick tuning
- Common issues
- Performance targets
- Cheat sheet
- Success criteria

**Length:** ~300 lines
**Target:** New users yang ingin cepat mulai

---

### `CHANGELOG_SDSC.md`
**Version history** - Detailed changelog

**Contents:**
- v2.0.0 release notes (major features)
- Added features (categorized)
- Changed from v1.0
- Bug fixes
- Dependencies
- Performance metrics
- Technical details
- Known limitations
- Future work
- v1.0.0 reference
- Version comparison table
- Migration guide
- Acknowledgments

**Length:** ~400 lines
**Target:** Track development progress

---

### `FILES_OVERVIEW.md`
**This file** - Overview semua files

**Purpose:** Navigate dan understand project structure

---

## ⚙️ Configuration Files

### `config_sdsc.yaml`
**External configuration** - YAML config untuk tuning tanpa edit code

**Sections:**
- Bluetooth/Serial settings
- Joystick mapping
- Social Force Model parameters
- Proxemic zones configuration
- Camera & detection settings
- Tracking parameters
- Visualization options
- Behavior presets (conservative, aggressive, crowded, testing)
- Tuning notes

**Length:** ~150 lines
**Status:** ⚠️ Currently NOT loaded by code (future enhancement)
**Usage:** Reference untuk parameter meanings

---

### `requirements_sdsc.txt`
**Python dependencies** - pip requirements file

**Contents:**
```
pygame>=2.5.0              # Joystick
pyserial>=3.5              # Bluetooth
opencv-python>=4.8.0       # Vision
ultralytics>=8.0.0         # YOLO
torch>=2.0.0              # AI backend
pyrealsense2>=2.54.0      # Camera
numpy>=1.24.0             # Numeric
```

**Usage:**
```bash
pip install -r requirements_sdsc.txt
```

---

## 🛠️ Utility Scripts

### `install_sdsc.sh`
**Installation script** - One-click setup untuk Linux

**What it does:**
1. Check Python version (>= 3.8)
2. Install system dependencies (apt packages)
3. Add RealSense repository
4. Install RealSense SDK
5. Install Python dependencies
6. Download YOLOv11 model
7. Setup Bluetooth service
8. Add user to dialout group
9. Create udev rules
10. Test all components
11. Show next steps

**Usage:**
```bash
bash install_sdsc.sh
```

**Length:** ~200 lines
**Platform:** Linux only (Ubuntu/Debian)

---

### `test_components.py`
**Component testing** - Diagnostic tool untuk test individual components

**Tests:**
1. **Joystick test**
   - Detection (pygame)
   - Info (name, axes, buttons)
   - Input testing (5 seconds)

2. **Bluetooth test**
   - pyserial import
   - Port listing
   - Connection attempt
   - Send test packet

3. **Camera test**
   - pyrealsense2 import
   - Pipeline start
   - Device info
   - Intrinsics
   - Frame capture (5 seconds)

4. **YOLO test**
   - torch/ultralytics import
   - CUDA check
   - Model loading
   - Inference test
   - Speed benchmark

**Usage:**
```bash
# Test all
python3 test_components.py

# Test specific component
python3 test_components.py joystick
python3 test_components.py bluetooth
python3 test_components.py camera
python3 test_components.py yolo
```

**Length:** ~400 lines
**Output:** Formatted test results dengan ✅/❌ indicators

---

## 🗂️ Directory Structure

```
SDSC Omniwheel/
├── bluetooth_sdsc.py          ⭐ Main controller
├── bluetooth.py                  Original (v1.0)
│
├── README_SDSC.md               📚 Complete docs
├── QUICKSTART.md                🚀 Quick start
├── CHANGELOG_SDSC.md            📝 Version history
├── FILES_OVERVIEW.md            📁 This file
│
├── config_sdsc.yaml             ⚙️ Configuration
├── requirements_sdsc.txt        📦 Dependencies
│
├── install_sdsc.sh              🛠️ Installation
└── test_components.py           🧪 Testing utility
```

---

## 📊 File Statistics

| File | Type | Lines | Purpose |
|------|------|-------|---------|
| bluetooth_sdsc.py | Python | ~800 | Main controller |
| bluetooth.py | Python | ~300 | Original (v1.0) |
| README_SDSC.md | Markdown | ~500 | Full documentation |
| QUICKSTART.md | Markdown | ~300 | Quick guide |
| CHANGELOG_SDSC.md | Markdown | ~400 | Version history |
| FILES_OVERVIEW.md | Markdown | ~250 | This file |
| config_sdsc.yaml | YAML | ~150 | Config reference |
| requirements_sdsc.txt | Text | ~10 | Dependencies |
| install_sdsc.sh | Shell | ~200 | Installation |
| test_components.py | Python | ~400 | Testing |
| **TOTAL** | | **~3,310** | Complete package |

---

## 🎯 Usage Workflows

### First Time Setup
```
1. READ: QUICKSTART.md
2. RUN: bash install_sdsc.sh
3. RUN: python3 test_components.py
4. SETUP: Bluetooth binding
5. RUN: python3 bluetooth_sdsc.py
```

### Daily Usage
```
1. Connect hardware (camera, joystick)
2. Verify Bluetooth: ls /dev/rfcomm0
3. Run: python3 bluetooth_sdsc.py
4. Use: Hold B4 + move stick
```

### Troubleshooting
```
1. RUN: python3 test_components.py
2. CHECK: Component-specific test output
3. READ: README_SDSC.md → Troubleshooting section
4. CHECK: GUI log window for errors
```

### Tuning
```
1. READ: README_SDSC.md → Configuration section
2. EDIT: bluetooth_sdsc.py → CONFIGURATION section
3. REFERENCE: config_sdsc.yaml for parameter meanings
4. TEST: Run and observe behavior
5. ITERATE: Adjust parameters
```

### Understanding Code
```
1. READ: FILES_OVERVIEW.md (this file)
2. READ: CHANGELOG_SDSC.md → Technical Details
3. READ: README_SDSC.md → Technical Details
4. STUDY: bluetooth_sdsc.py → Class/function comments
```

---

## 🔍 Key Classes & Functions

### `bluetooth_sdsc.py` Structure

#### Classes:

**`HumanDetector`**
- Purpose: Manage RealSense + YOLO detection
- Key methods:
  - `detect_once()`: Single detection cycle
  - `pixel_to_camera_frame()`: Coordinate transform
  - `match_detection_to_track()`: Simple tracking
  - `run_detection_loop()`: Background thread
  - `get_detections()`: Thread-safe getter

**`SocialForceModulator`**
- Purpose: Compute SFM and modulate velocity
- Key methods:
  - `compute_repulsive_force()`: Calculate F_rep
  - `get_proxemic_zone()`: Determine zone
  - `modulate_velocity()`: Apply SFM to joystick input
  - `get_status()`: Get current state

#### Functions:

**Main Loop:**
- `read_input()`: 20 Hz control loop
- `build_packet_with_sfm()`: Velocity modulation
- `update_ui()`: GUI updates

**Bluetooth:**
- `connect_serial()`: Establish connection
- `send()`: Write packet
- `get_available_ports()`: Scan rfcomm

**GUI:**
- `update_joystick()`: Joystick detection
- `log_message()`: Append to log
- `on_close()`: Cleanup

**Visualization:**
- `run_visualization()`: OpenCV window thread

---

## 📝 Code Style

### Naming Conventions
- **Classes:** PascalCase (`HumanDetector`)
- **Functions:** snake_case (`compute_repulsive_force()`)
- **Constants:** UPPER_SNAKE_CASE (`SFM_A`, `R_INTIMATE`)
- **Variables:** snake_case (`closest_dist`)

### Documentation Style
- **Module docstrings:** Multi-line dengan description, input/output, author
- **Function docstrings:** One-line atau multi-line dengan args/returns
- **Inline comments:** Explain non-obvious logic

### Configuration Style
- Constants grouped in `CONFIGURATION` section
- Clear section headers dengan `# ── Section ──`
- Comments dengan units (m, N, s, Hz)
- Default values chosen untuk safety

---

## 🔧 Maintenance

### Adding New Features
1. Document in CHANGELOG_SDSC.md
2. Update README_SDSC.md if user-facing
3. Add configuration parameters di `CONFIGURATION`
4. Add test di `test_components.py` if applicable
5. Update version number

### Bug Fixes
1. Document in CHANGELOG_SDSC.md
2. Add to troubleshooting di README_SDSC.md
3. Consider adding diagnostic di `test_components.py`

### Parameter Tuning
1. Test dengan different scenarios
2. Document results in comments
3. Update recommended ranges di config_sdsc.yaml
4. Add to tuning guide di README_SDSC.md

---

## 🚀 Future Enhancements

### Planned Additions
- [ ] Load config from `config_sdsc.yaml` (YAML parsing)
- [ ] ROS 2 integration (nodes, topics)
- [ ] Path planning module (A* + SFM)
- [ ] Telemetry logging (CSV export)
- [ ] Web dashboard (Flask/WebSocket)
- [ ] Multi-robot coordination

### File Additions
- `bluetooth_sdsc_ros2.py`: ROS 2 wrapper
- `path_planner.py`: A* + SFM planner
- `telemetry_logger.py`: Data logging
- `web_dashboard.py`: Web interface
- `multi_robot_coordinator.py`: Formation control

---

## 📞 Support & Contact

### Documentation Locations
- **Full docs:** README_SDSC.md
- **Quick start:** QUICKSTART.md
- **Version history:** CHANGELOG_SDSC.md
- **This overview:** FILES_OVERVIEW.md

### Getting Help
1. Read relevant documentation
2. Run `python3 test_components.py`
3. Check troubleshooting sections
4. Review log output
5. Check hardware connections

---

## 📜 License

MIT License - Free to use and modify

---

**Project:** Bluetooth SDSC Controller
**Version:** 2.0.0
**Team:** Brone Social Nav Team
**Last Updated:** 2024-12-31

**Happy Coding! 🤖✨**
