# 📁 Files Index - Tester102_4

## Quick Navigation

| Category | Files | Purpose |
|----------|-------|---------|
| 🎮 **Main Program** | `manual_camera_movement_tester.py` | Data collection tool |
| 📊 **Data Files** | `sample_data.csv` | Exported sample data |
| 📈 **Visualization** | `visualize_csv.py`<br>`plot_from_samples.py`<br>`quick_stats.py` | Analysis tools |
| 📖 **Documentation** | `README.md`<br>`VISUALIZATION_GUIDE.md`<br>`DATA_ANALYSIS_SUMMARY.md`<br>`SAMPLING_GUIDE.md` | User guides |
| 📝 **Reference** | `QUICK_REFERENCE.txt`<br>`QUICK_START.txt`<br>`FILES_INDEX.md` | Quick ref |
| 📋 **History** | `CHANGELOG.md`<br>`INTEGRATION_SUMMARY.md`<br>`INTEGRATION_UPDATE.md` | Version history |
| 🤖 **Model** | `yolo11n.pt` | YOLO detection |
| ⚙️ **Config** | `requirements.txt` | Dependencies |

---

## Detailed File Descriptions

### 🎮 Main Programs

#### `manual_camera_movement_tester.py`
**Type:** Python Script (Main)  
**Size:** ~800 lines  
**Purpose:** Manual camera movement tester with proxemic speed control

**Features:**
- WASD keyboard control
- Real-time human detection (YOLO11)
- Proxemic zone classification
- Speed adjustment (0.3-1.0 m/s)
- 2D trajectory tracking
- Movement command output
- Live visualization

**Usage:**
```bash
python manual_camera_movement_tester.py
```

**Requirements:**
- Intel RealSense D435/D455
- Python 3.6+
- See `requirements.txt`

---

### 📊 Data Files

#### `sample_data.csv`
**Type:** CSV Data File  
**Created:** 2026-10-06  
**Samples:** 9 data points  
**Duration:** ~13 minutes  
**Distance:** 1.284 m

**Structure:**
```csv
Sample,Time_s,Position_X_m,Position_Y_m,Velocity_X_ms,Velocity_Y_ms,
Speed_ms,Zone,Humans_Count,Closest_Distance_m,SFM_Force_X_N,
SFM_Force_Y_N,Command,Displacement_X_m,Displacement_Y_m
```

**15 Columns:**
1. Sample number (1-9)
2. Time in seconds
3-4. Position X, Y (meters)
5-6. Velocity X, Y (m/s)
7. Speed magnitude (m/s)
8. Proxemic zone
9. Number of humans detected
10. Distance to closest human (m)
11-12. SFM Force X, Y (Newtons)
13. Movement command
14-15. Displacement X, Y (m)

**Import:**
```python
import pandas as pd
df = pd.read_csv('sample_data.csv')
```

---

### 📈 Visualization Tools

#### `visualize_csv.py` ⭐ RECOMMENDED
**Type:** Python Script (Visualization)  
**Size:** ~400 lines  
**Purpose:** Comprehensive dashboard generator

**Output:** 6 plots in one figure
1. Trajectory map with zones
2. Speed over time
3. Distance to humans
4. SFM force magnitude
5. Velocity vector field
6. Force vector field

**Plus:** Statistical summary in terminal

**Usage:**
```bash
python visualize_csv.py
# Output: social_nav_analysis_YYYYMMDD_HHMMSS.png
```

**Dependencies:** pandas, matplotlib, numpy

---

#### `plot_from_samples.py`
**Type:** Python Script (Alternative Plotter)  
**Size:** ~600 lines  
**Purpose:** Plot from CSV or hardcoded data

**Modes:**
- CSV mode (default)
- Hardcoded data mode (`--hardcoded`)

**Output:** 2 subplots
1. Trajectory map
2. Time series (speed, force, humans)

**Usage:**
```bash
python plot_from_samples.py
python plot_from_samples.py --hardcoded
# Output: trajectory_plot_YYYYMMDD_HHMMSS.png
```

**Note:** Contains hardcoded sample data as backup

---

#### `quick_stats.py`
**Type:** Python Script (Statistics)  
**Size:** ~300 lines  
**Purpose:** Fast statistical analysis without plots

**Output:** Terminal text only
- Basic info
- Time analysis
- Position & distance
- Speed statistics
- Zone distribution
- Human detection metrics
- Force analysis
- Command distribution
- Safety violations check

**Usage:**
```bash
python quick_stats.py                # Use sample_data.csv
python quick_stats.py mydata.csv     # Specify file
```

**Fast:** Runs in <1 second

---

### 📖 Documentation Files

#### `README.md`
**Type:** Markdown Documentation (Main)  
**Size:** ~500 lines  
**Purpose:** Complete user guide

**Sections:**
- Description & goals
- Features
- Installation
- Usage instructions
- Keyboard controls
- Test scenarios
- Output interpretation
- Troubleshooting
- Data collection
- Parameter tuning

**Audience:** All users (beginners to advanced)

---

#### `VISUALIZATION_GUIDE.md`
**Type:** Markdown Documentation (Specialized)  
**Size:** ~300 lines  
**Purpose:** Visualization tool guide

**Contents:**
- Tool overview
- Graph descriptions
- Statistics explained
- Requirements
- Usage workflow
- Analysis tips
- Troubleshooting
- Customization
- Advanced usage

**When to read:** Before using visualization tools

---

#### `DATA_ANALYSIS_SUMMARY.md`
**Type:** Markdown Documentation (Analysis)  
**Size:** ~400 lines  
**Purpose:** Sample data analysis report

**Contains:**
- Quick start commands
- Key metrics summary
- Visualization outputs
- Interpretation guide
- Validation results
- Recommendations
- Statistical summary
- Commands reference

**When to read:** After collecting data

---

#### `SAMPLING_GUIDE.md`
**Type:** Markdown Documentation (Tutorial)  
**Purpose:** Manual sampling tutorial

**Topics:**
- Sampling workflow
- Camera positioning
- Data recording
- Best practices

---

### 📝 Quick Reference Files

#### `QUICK_REFERENCE.txt`
**Type:** Plain Text Reference  
**Size:** Short (~50 lines)  
**Purpose:** Command cheatsheet

**Contains:**
- Keyboard shortcuts
- Zone definitions
- Speed values
- Common commands

**Format:** Plain text (easy copy-paste)

---

#### `QUICK_START.txt`
**Type:** Plain Text Guide  
**Purpose:** Fast setup guide

**For:** First-time users

---

#### `FILES_INDEX.md` (this file)
**Type:** Markdown Documentation (Index)  
**Purpose:** File navigation guide

---

### 📋 History & Logs

#### `CHANGELOG.md`
**Type:** Markdown (Version History)  
**Purpose:** Track changes over versions

**Format:**
```markdown
## [Version] - Date
### Added
### Changed
### Fixed
```

---

#### `INTEGRATION_SUMMARY.md`
**Type:** Markdown (Technical)  
**Purpose:** Integration documentation

---

#### `INTEGRATION_UPDATE.md`
**Type:** Markdown (Technical)  
**Purpose:** Update notes

---

### 🤖 Model Files

#### `yolo11n.pt`
**Type:** PyTorch Model File  
**Size:** ~6 MB  
**Purpose:** Human detection model

**Model:** YOLOv11 Nano  
**Input:** RGB image  
**Output:** Bounding boxes + class + confidence  
**Classes:** 80 (COCO dataset)  
**Target:** Person (class 0)

**Source:** [Ultralytics](https://github.com/ultralytics/assets/releases)

**Usage:**
```python
from ultralytics import YOLO
model = YOLO('yolo11n.pt')
results = model(frame, conf=0.5, classes=[0])
```

---

### ⚙️ Configuration Files

#### `requirements.txt`
**Type:** Text (Dependency List)  
**Purpose:** Python package requirements

**Contents:**
```
pyrealsense2>=2.50.0
ultralytics>=8.0.0
opencv-python>=4.5.0
numpy>=1.19.0
pandas>=1.3.0
matplotlib>=3.3.0
```

**Install:**
```bash
pip install -r requirements.txt
```

---

## File Relationships

```
┌─────────────────────────────────────────────┐
│   MANUAL_CAMERA_MOVEMENT_TESTER.PY         │ ← Main program
└────────────┬────────────────────────────────┘
             │ produces
             ↓
      ┌─────────────┐
      │ Console     │ ← Copy data manually
      │ Output      │
      └──────┬──────┘
             │ convert to
             ↓
      ┌──────────────────┐
      │ SAMPLE_DATA.CSV  │ ← Data file
      └─────────┬────────┘
                │ used by
      ┌─────────┴─────────┬──────────────┐
      ↓                   ↓              ↓
┌─────────────┐   ┌──────────────┐   ┌────────────┐
│VISUALIZE    │   │PLOT_FROM     │   │QUICK       │
│_CSV.PY      │   │_SAMPLES.PY   │   │_STATS.PY   │
└──────┬──────┘   └──────┬───────┘   └─────┬──────┘
       │                 │                  │
       ↓                 ↓                  ↓
    [PNG]            [PNG]            [Terminal]
    [Stats]          [CSV]             [Stats]
```

---

## File Usage Matrix

| Task | Files Needed | Optional |
|------|--------------|----------|
| **Collect data** | `manual_camera_movement_tester.py`<br>`yolo11n.pt` | - |
| **Visualize** | `sample_data.csv`<br>`visualize_csv.py` | `VISUALIZATION_GUIDE.md` |
| **Quick stats** | `sample_data.csv`<br>`quick_stats.py` | - |
| **First time** | `README.md`<br>`QUICK_START.txt` | `SAMPLING_GUIDE.md` |
| **Troubleshoot** | `README.md` (section) | `VISUALIZATION_GUIDE.md` |
| **Reference** | `QUICK_REFERENCE.txt` | `FILES_INDEX.md` |

---

## Workflow Paths

### Path 1: First Time User
```
1. README.md (read overview)
2. QUICK_START.txt (setup)
3. manual_camera_movement_tester.py (run)
4. QUICK_REFERENCE.txt (controls)
```

### Path 2: Data Analysis
```
1. manual_camera_movement_tester.py (collect)
2. sample_data.csv (export)
3. visualize_csv.py (analyze)
4. DATA_ANALYSIS_SUMMARY.md (interpret)
```

### Path 3: Troubleshooting
```
1. README.md (troubleshooting section)
2. VISUALIZATION_GUIDE.md (if viz issues)
3. CHANGELOG.md (check versions)
```

---

## File Size Summary

| Category | Est. Size | Files |
|----------|-----------|-------|
| Scripts | ~20 KB | 4 files |
| Documentation | ~100 KB | 9 files |
| Data | ~1 KB | 1 file |
| Model | ~6 MB | 1 file |
| **Total** | **~6.1 MB** | **15 files** |

---

## Last Updated

**Date:** 2026-10-06  
**Version:** Tester102_4  
**Maintainer:** Brone Social Nav Team

---

## Need Help?

| Question | See File |
|----------|----------|
| "How do I start?" | `README.md` or `QUICK_START.txt` |
| "What do these keys do?" | `QUICK_REFERENCE.txt` |
| "How to visualize?" | `VISUALIZATION_GUIDE.md` |
| "What do results mean?" | `DATA_ANALYSIS_SUMMARY.md` |
| "What's in this folder?" | `FILES_INDEX.md` (this file) |
| "How to sample?" | `SAMPLING_GUIDE.md` |
| "What changed?" | `CHANGELOG.md` |

---

**Happy Analyzing! 📊📈🚀**
