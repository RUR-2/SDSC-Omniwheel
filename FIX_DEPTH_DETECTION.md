# 🔧 Fix: Human Detection Depth Problem

## 🚨 Problem Identified

**Symptom dari screenshot:**
- ✅ Person detected (0.79 confidence)
- ❌ F_rep: 0.00N (no repulsive force)
- ❌ Zone: PUBLIC (999.00m) - jarak salah besar!

**Root Cause:**
Depth value dari RealSense camera tidak terbaca dengan benar di titik tengah detection box, menyebabkan distance = 0 atau invalid, sehingga detection di-skip.

---

## ✅ Solution Implemented

### **Fix #1: Multi-Point Depth Sampling**

**Masalah:**
```python
# OLD - hanya sample 1 titik:
distance = depth_frame.get_distance(cx, cy)
if distance <= MIN_DISTANCE or distance > MAX_DISTANCE:
    continue  # Skip detection jika center invalid
```

**Solusi:**
```python
# NEW - sample 5 titik (center + 4 arah):
distance = depth_frame.get_distance(cx, cy)

if distance <= MIN_DISTANCE or distance > MAX_DISTANCE:
    # Try multiple points:
    sample_points = [
        (cx, cy),                           # center
        (cx, cy - height*0.25),            # upper-center (dada)
        (cx, cy + height*0.25),            # lower-center (pinggang)
        (cx - width*0.15, cy),             # left-center
        (cx + width*0.15, cy),             # right-center
    ]
    
    valid_depths = []
    for sx, sy in sample_points:
        d = depth_frame.get_distance(sx, sy)
        if MIN_DISTANCE < d <= MAX_DISTANCE:
            valid_depths.append(d)
    
    # Use median of valid depths
    distance = sorted(valid_depths)[len(valid_depths) // 2]
```

**Why this works:**
- Titik center kadang kena baju/rambut yang reflektif → depth invalid
- Sampling multiple points meningkatkan robustness
- Median filter menghilangkan outliers
- Upper-center (dada) biasanya paling reliable

---

### **Fix #2: Debug Visualization**

Added real-time depth debugging di OpenCV window:

```
DEBUG Depth@center: 0.000m     ← Shows raw center depth
DEBUG Avg depth (3x3): 1.234m  ← Shows average dari 9 titik
DEBUG Valid samples: 7/9       ← Shows berapa titik valid
```

**Cara pakai:**
1. Jalankan bluetooth_sdsc.py
2. Lihat OpenCV window (bawah kiri)
3. Check apakah "DEBUG Depth@center" = 0.000m
4. Jika ya, tapi "Avg depth" ada nilai → Fix berhasil!

---

### **Fix #3: Enhanced Logging**

Terminal sekarang menampilkan:

**Successful detection:**
```
✅ Detected ID1: dist=1.23m, 2D=1.25m, pos=(1.20,0.15), conf=0.79
```

**Failed detection (no valid depth):**
```
⚠️ No valid depth for detection at (320,240), bbox confidence 0.79
```

**Multi-point sampling used:**
```
✅ Used multi-point sampling: 1.23m from 4 valid points
```

---

## 🧪 How to Test the Fix

### **Step 1: Jalankan dengan debug mode**

```cmd
cd "d:\Vroomniwheel\SDSC Omniwheel"
python bluetooth_sdsc.py
```

### **Step 2: Check OpenCV window**

Perhatikan bagian bawah kiri screen:
- `DEBUG Depth@center: X.XXXm` - Should show actual distance
- `DEBUG Avg depth (3x3): X.XXXm` - Should be similar
- `DEBUG Valid samples: N/9` - Should be at least 5/9

### **Step 3: Check Terminal logs**

Harus muncul salah satu:
```
✅ Detected ID1: dist=1.23m, ...  ← GOOD
```

ATAU jika masih gagal:
```
⚠️ No valid depth for detection at (x,y), bbox confidence 0.XX  ← BAD
```

### **Step 4: Check GUI**

Di GUI window, perhatikan:
- **Humans:** Harus > 0
- **Closest:** Harus menampilkan jarak real (0.5m - 5m)
- **Zone:** Harus PUBLIC/SOCIAL/PERSONAL (bukan 999m!)
- **Repulsion:** Harus > 0.00N kalau ada human dekat

---

## 🔍 Troubleshooting Depth Issues

### **Problem: Depth masih 0.000m**

**Possible causes:**

#### 1. **IR Emitter Mati**
RealSense butuh IR emitter untuk depth sensing.

**Check:**
```cmd
realsense-viewer
```

Di viewer window:
- Pilih Stereo Module
- Check "Emitter Enabled" = ON
- Set "Laser Power" = 150-360 mW

**Fix in code:**
Add setelah `self.pipeline.start(self.config)`:
```python
# Enable IR emitter
depth_sensor = self.profile.get_device().first_depth_sensor()
depth_sensor.set_option(rs.option.emitter_enabled, 1)
depth_sensor.set_option(rs.option.laser_power, 240)  # 240 mW
```

---

#### 2. **Distance Terlalu Dekat/Jauh**

RealSense D435:
- Min: ~0.3m
- Max: ~10m (indoor), ~3m (reliable)

**Check parameters:**
```python
MIN_DISTANCE = 0.1  # m - too small? Try 0.3
MAX_DISTANCE = 10.0  # m - too large? Try 5.0
```

**Recommended:**
```python
MIN_DISTANCE = 0.3   # RealSense minimum
MAX_DISTANCE = 5.0   # Reliable indoor range
```

---

#### 3. **Surface Reflektif/Gelap**

Depth sensing gagal pada:
- ❌ Kaca/cermin (reflektif)
- ❌ Baju hitam/gelap (absorb IR)
- ❌ Rambut panjang (transparan ke IR)
- ❌ Backlit subjects (silhouette)

**Solution:**
- Gunakan normal lighting (jangan backlit)
- Avoid testing dengan baju hitam polos
- Test di ruangan dengan lighting cukup
- Jarak optimal: 1-3 meter

---

#### 4. **Camera Alignment Issue**

Depth dan color frame harus aligned.

**Check:**
```python
# Ensure alignment is set up correctly
self.align = rs.align(rs.stream.color)  # Align depth TO color
```

**In detect_once():**
```python
aligned_frames = self.align.process(frames)
depth_frame = aligned_frames.get_depth_frame()
color_frame = aligned_frames.get_color_frame()

# Both must be valid!
if not depth_frame or not color_frame:
    return None, None
```

---

#### 5. **USB Bandwidth Issue**

RealSense butuh USB 3.0 dengan bandwidth cukup.

**Check:**
```cmd
realsense-viewer
```

Di log, cari:
```
USB 3.x detected
```

Jika muncul "USB 2.0", depth quality jelek!

**Fix:**
- Gunakan USB 3.0 port (biasanya biru)
- Jangan share hub dengan device lain
- Try different USB port
- Reduce FPS:
  ```python
  CAMERA_FPS = 15  # instead of 30
  ```

---

## 📊 Expected Behavior After Fix

### **BEFORE (Broken):**
```
Detection Window:
  person 0.79
  F_rep: 0.00N
  Zone: PUBLIC (999.00m)

Terminal:
  (no logs, detection skipped)

GUI:
  Humans: 0
  Closest: --
  Zone: PUBLIC
  Repulsion: 0.00N
```

### **AFTER (Fixed):**
```
Detection Window:
  ID1 1.23m
  (1.20, 0.15)
  F_rep: 2.34N
  Zone: SOCIAL (1.23m)
  DEBUG Depth@center: 1.230m
  DEBUG Avg depth (3x3): 1.228m
  DEBUG Valid samples: 8/9

Terminal:
  ✅ Detected ID1: dist=1.23m, 2D=1.25m, pos=(1.20,0.15), conf=0.79
  🟡 SOCIAL ZONE (1.23m) - AVOIDING (60%)

GUI:
  Humans: 1
  Closest: 1.23m
  Zone: SOCIAL
  Repulsion: 2.34N
```

---

## 🎯 Validation Checklist

Test dengan human pada berbagai jarak:

- [ ] **3.5m** - Early evasion
  - Expected: 🟢 EARLY EVASION (3.5m)
  - Force: ~0.5N
  
- [ ] **2.5m** - SOCIAL zone
  - Expected: 🟡 SOCIAL ZONE (2.5m) - AVOIDING (60%)
  - Force: ~2.0N
  
- [ ] **1.5m** - SOCIAL zone (close)
  - Expected: 🟡 SOCIAL ZONE (1.5m)
  - Force: ~5.0N
  
- [ ] **1.0m** - PERSONAL zone
  - Expected: 🟠 PERSONAL ZONE (1.0m) - SLOW DOWN (30%)
  - Force: ~15N
  
- [ ] **0.6m** - PERSONAL zone (critical)
  - Expected: 🟠 PERSONAL ZONE (0.6m)
  - Force: ~30N

**NEVER should see:**
- ❌ Zone: PUBLIC (999.00m)
- ❌ F_rep: 0.00N (when human visible)
- ❌ Closest: --

---

## 🛠️ Advanced Debug: Manual Depth Test

Jika masih bermasalah, test depth sensing secara manual:

**Create test_depth.py:**
```python
import pyrealsense2 as rs
import numpy as np

pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

profile = pipeline.start(config)

# Enable emitter
depth_sensor = profile.get_device().first_depth_sensor()
depth_sensor.set_option(rs.option.emitter_enabled, 1)

align = rs.align(rs.stream.color)

print("Stand 1-2 meters in front of camera...")
print("Reading depth at center (320, 240)...")

for i in range(10):
    frames = pipeline.wait_for_frames()
    aligned_frames = align.process(frames)
    depth_frame = aligned_frames.get_depth_frame()
    
    if depth_frame:
        # Center point
        d_center = depth_frame.get_distance(320, 240)
        
        # Sample 3x3
        depths = []
        for dy in [-20, 0, 20]:
            for dx in [-20, 0, 20]:
                d = depth_frame.get_distance(320+dx, 240+dy)
                if d > 0:
                    depths.append(d)
        
        avg = sum(depths) / len(depths) if depths else 0
        
        print(f"{i+1}. Center: {d_center:.3f}m, Avg 3x3: {avg:.3f}m, Valid: {len(depths)}/9")

pipeline.stop()
```

**Run:**
```cmd
python test_depth.py
```

**Expected output:**
```
1. Center: 1.234m, Avg 3x3: 1.230m, Valid: 9/9
2. Center: 1.235m, Avg 3x3: 1.232m, Valid: 9/9
...
```

**If you see:**
```
1. Center: 0.000m, Avg 3x3: 0.000m, Valid: 0/9  ← BAD! Camera issue
```

Then problem is hardware/driver, not code!

---

## 📞 Still Having Issues?

### **Scenario 1: All depths = 0.000m**

**Diagnosis:** Hardware/driver problem

**Fix:**
1. Update RealSense SDK/firmware
2. Try different USB port (USB 3.0)
3. Check IR emitter with phone camera (should see red dots)
4. Restart camera

---

### **Scenario 2: Depth works in realsense-viewer, not in script**

**Diagnosis:** Alignment or timing issue

**Fix:**
```python
# Add post-processing filters
from rs import spatial_filter, temporal_filter, hole_filling_filter

self.spatial = rs.spatial_filter()
self.temporal = rs.temporal_filter()
self.hole_filling = rs.hole_filling_filter()

# In detect_once():
depth_frame = aligned_frames.get_depth_frame()
depth_frame = self.spatial.process(depth_frame)
depth_frame = self.temporal.process(depth_frame)
depth_frame = self.hole_filling.process(depth_frame)
```

---

### **Scenario 3: Works sometimes, fails others**

**Diagnosis:** Surface/lighting dependent

**Fix:**
- Ensure consistent lighting
- Avoid testing with highly reflective/absorptive materials
- Increase sample size from 5 to 9 points
- Use temporal averaging

---

## ✅ Summary of Changes

**File Modified:** `bluetooth_sdsc.py`

**Changes:**
1. Multi-point depth sampling (5 points → median)
2. Debug visualization overlay
3. Enhanced logging
4. Better error messages

**Lines changed:** ~60

**Testing required:**
- Visual confirmation of depth values on screen
- Terminal log validation
- GUI status verification
- Real-world distance accuracy check

---

**Version:** bluetooth_sdsc.py v2.1.1 + Depth Fix  
**Date:** 2026-10-11  
**Status:** ✅ Ready for Testing

---

*"If you can't measure it, you can't improve it. Now we can see the depth!"* 📏
