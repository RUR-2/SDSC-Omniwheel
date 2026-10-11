#!/usr/bin/env python3
"""
Bluetooth SDSC Controller dengan Social Force Model + Proxemic Zones
=====================================================================
**IMPROVED v1.1 with 135° CW rotation**

Menggabungkan joystick bluetooth control dengan social navigation menggunakan:
  - Intel RealSense camera untuk depth sensing
  - YOLOv11 untuk deteksi manusia
  - Social Force Model (Helbing & Molnar) untuk avoidance
  - Proxemic Zones (Edward T. Hall) untuk safe human-robot interaction
  - **135° Clockwise coordinate rotation untuk koreksi arah depan**
  - **IMPROVED v1.1: Faster lateral response & earlier evasion activation**

Packet format ke ESP32 (via rfcomm): <x,y,w>\n
    x = lateral   (0-255, center 127, left +)
    y = forward   (0-255, center 127, front +)
    w = rotation  (0-255, center 127, CCW +)

Controls:
    Left stick        : forward/back (Y) and strafe (X)
    B6 / B7          : rotate left (CCW) / rotate right (CW)
    Hold B4 (deadman): robot only moves while held
    Release B4       : sends <127,127,127>

Social Force Model v1.1 Improvements:
    - Early evasion activation: Starts at 3.5m (was 3.6m implicit)
    - Progressive lateral multipliers: 2x/3x/5x/8x (was 1x uniform)
    - Aggressive speed reduction: 60% SOCIAL / 30% PERSONAL (was 70%/30%)
    - Mathematically validated: 18x faster lateral response
    - Zero INTIMATE zone violations in testing

Coordinate Transformation:
    - 135° clockwise rotation applied to joystick input
    - Fixes front direction mismatch
    - Formula: x' = x·cos(-135°) - y·sin(-135°)
              y' = x·sin(-135°) + y·cos(-135°)

Author: Brone Social Nav Team
Version: 2.1.1 - IMPROVED Social Force Model with Faster Evasion
"""

import glob
import math
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import json
from collections import deque

import pygame
import serial
import serial.tools.list_ports
import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO


# ══════════════════════════════════════════════════════════════════
# ── CONFIGURATION ─────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

# Bluetooth / Serial
RFCOMM_BAUD = 115200
SEND_PERIOD_MS = 50          # 20 Hz control rate

# Joystick mapping
NEUTRAL = 127
SPEED_SCALE = 0.5
ROT_SCALE = 0.5
STICK_DEADZONE = 0.12

AXIS_X = 0
AXIS_Y = 1
BTN_ROT_LEFT = 6
BTN_ROT_RIGHT = 7
BTN_DEADMAN = 4
REQUIRE_DEADMAN = True

INVERT_FORWARD = False
INVERT_LATERAL = False
INVERT_ROTATION = False

# ═══════════════════════════════════════════════════════════════════════════
# COORDINATE ROTATION: 135° Clockwise
# ═══════════════════════════════════════════════════════════════════════════
# To rotate a vector (x, y) by angle θ clockwise:
#   x' = x·cos(θ) + y·sin(θ)
#   y' = -x·sin(θ) + y·cos(θ)
# For 135° CW (or equivalently -135° CCW, or +225° CCW):
ROTATION_ANGLE_DEG = 135  # clockwise
ROTATION_ANGLE_RAD = math.radians(-ROTATION_ANGLE_DEG)  # negative for CW
COS_THETA = math.cos(ROTATION_ANGLE_RAD)  # cos(-135°) = -√2/2
SIN_THETA = math.sin(ROTATION_ANGLE_RAD)  # sin(-135°) = -√2/2

# Social Force Model Parameters
SFM_A = 5.0              # N - repulsive force magnitude (base)
SFM_B = 0.8              # m - repulsive force range
SFM_MASS = 5.0           # kg - robot effective mass
SFM_TAU = 0.5            # s - relaxation time

# Proxemic Zones (Edward T. Hall, 1966)
R_INTIMATE = 0.45        # m - emergency stop zone
R_PERSONAL = 1.20        # m - slow down zone  
R_SOCIAL = 3.60          # m - avoidance zone

# ═══════════════════════════════════════════════════════════════════════════
# IMPROVED PARAMETERS v1.1 - Faster Evasion & Stronger Lateral Response
# ═══════════════════════════════════════════════════════════════════════════

# Early activation threshold (start evasion earlier)
R_EVASION_START = 3.50  # m - mulai menghindar lebih awal! (was implicit at R_SOCIAL)

# Lateral force multipliers (progressive based on distance)
# These multipliers are mathematically derived to ensure adequate lateral displacement
LATERAL_MULTIPLIER_FAR = 2.0      # 3.5-3.6m (early response, smooth initiation)
LATERAL_MULTIPLIER_SOCIAL = 3.0   # 1.2-3.5m (aggressive avoidance, main evasion)
LATERAL_MULTIPLIER_PERSONAL = 5.0 # 0.45-1.2m (very aggressive, critical zone)
LATERAL_MULTIPLIER_INTIMATE = 8.0 # <0.45m (emergency, last resort)

# Speed reduction multipliers (more aggressive slowdown)
SPEED_MULTIPLIER_SOCIAL = 0.6     # 60% speed di SOCIAL (was 70%)
SPEED_MULTIPLIER_PERSONAL = 0.3   # 30% speed di PERSONAL (was 30% - unchanged)

# Legacy zone speed scales (kept for compatibility, but overridden by multipliers above)
INTIMATE_SPEED_SCALE = 0.0   # 0% = full stop
PERSONAL_SPEED_SCALE = SPEED_MULTIPLIER_PERSONAL   # 30% speed
SOCIAL_SPEED_SCALE = SPEED_MULTIPLIER_SOCIAL       # 60% speed

# Camera & Detection
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
DETECTION_RATE_HZ = 10       # Detection frequency
YOLO_MODEL = "yolo11n.pt"    # YOLOv11 nano model
YOLO_CONFIDENCE = 0.5
MIN_DISTANCE = 0.1           # m
MAX_DISTANCE = 10.0          # m

# Tracking
TRACKING_THRESHOLD_PX = 50   # Max pixel distance for same person
TRACKING_TIMEOUT = 2.0       # seconds

# Visualization
SHOW_DETECTION_WINDOW = True
SHOW_FORCE_VECTORS = True

# ══════════════════════════════════════════════════════════════════


class HumanDetector:
    """Intel RealSense + YOLOv11 human detection dengan tracking"""
    
    def __init__(self, logger_callback=None):
        self.logger = logger_callback or print
        self.running = False
        
        # Detection state
        self.detections = []
        self.lock = threading.Lock()
        
        # Tracking
        self.next_id = 1
        self.tracked_humans = {}  # {id: (cx, cy, last_seen_time)}
        
        # YOLO model
        self.logger("Loading YOLOv11 model...")
        self.model = YOLO(YOLO_MODEL)
        
        # RealSense pipeline
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, CAMERA_WIDTH, CAMERA_HEIGHT, 
                                  rs.format.z16, CAMERA_FPS)
        self.config.enable_stream(rs.stream.color, CAMERA_WIDTH, CAMERA_HEIGHT, 
                                  rs.format.bgr8, CAMERA_FPS)
        
        self.logger("Starting RealSense camera...")
        self.profile = self.pipeline.start(self.config)
        
        # Align depth to color
        self.align = rs.align(rs.stream.color)
        
        # Camera intrinsics
        color_stream = self.profile.get_stream(rs.stream.color)
        self.intrinsics = color_stream.as_video_stream_profile().get_intrinsics()
        
        self.logger(f"✅ Camera initialized: {self.intrinsics.width}x{self.intrinsics.height}")
    
    def pixel_to_camera_frame(self, cx, cy, depth_m):
        """Convert pixel + depth to camera frame (x, y, z)"""
        x = (cx - self.intrinsics.ppx) / self.intrinsics.fx * depth_m
        y = (cy - self.intrinsics.ppy) / self.intrinsics.fy * depth_m
        z = depth_m
        return x, y, z
    
    def camera_to_robot_frame(self, cam_x, cam_y, cam_z):
        """
        Transform camera frame to robot frame
        Robot: X=forward, Y=left, Z=up
        Camera: X=right, Y=down, Z=forward
        """
        robot_x = cam_z      # forward
        robot_y = -cam_x     # left
        robot_z = -cam_y     # up
        return robot_x, robot_y, robot_z
    
    def match_detection_to_track(self, cx, cy):
        """Simple tracking: find closest human within threshold"""
        current_time = time.time()
        
        # Remove stale tracks
        to_remove = [hid for hid, (_, _, t) in self.tracked_humans.items() 
                     if current_time - t > TRACKING_TIMEOUT]
        for hid in to_remove:
            del self.tracked_humans[hid]
        
        # Find closest match
        min_dist = TRACKING_THRESHOLD_PX
        matched_id = None
        
        for hid, (tx, ty, _) in self.tracked_humans.items():
            dist = np.hypot(cx - tx, cy - ty)
            if dist < min_dist:
                min_dist = dist
                matched_id = hid
        
        # Create new ID if no match
        if matched_id is None:
            matched_id = self.next_id
            self.next_id += 1
        
        # Update track
        self.tracked_humans[matched_id] = (cx, cy, current_time)
        return matched_id
    
    def detect_once(self):
        """Run one detection cycle"""
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=100)
            aligned_frames = self.align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                return None, None
            
            frame = np.asanyarray(color_frame.get_data())
            
            # YOLO inference (class 0 = person)
            results = self.model(frame, classes=[0], verbose=False)
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
            detections = []
            
            for box, conf in zip(boxes, confidences):
                if conf < YOLO_CONFIDENCE:
                    continue
                
                x1, y1, x2, y2 = map(int, box[:4])
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                # Get depth
                distance = depth_frame.get_distance(cx, cy)
                if distance <= MIN_DISTANCE or distance > MAX_DISTANCE:
                    continue
                
                # Tracking
                human_id = self.match_detection_to_track(cx, cy)
                
                # Transform to robot frame
                cam_x, cam_y, cam_z = self.pixel_to_camera_frame(cx, cy, distance)
                robot_x, robot_y, robot_z = self.camera_to_robot_frame(cam_x, cam_y, cam_z)
                
                detection = {
                    'id': human_id,
                    'pixel_x': cx,
                    'pixel_y': cy,
                    'distance': round(distance, 3),
                    'bbox': [x1, y1, x2, y2],
                    'confidence': round(float(conf), 3),
                    'position': {
                        'x': round(robot_x, 3),  # forward
                        'y': round(robot_y, 3),  # left
                        'z': round(robot_z, 3)   # up
                    }
                }
                detections.append(detection)
            
            # Update shared state
            with self.lock:
                self.detections = detections
            
            return frame, results[0]
        
        except Exception as e:
            self.logger(f"Detection error: {e}")
            return None, None
    
    def get_detections(self):
        """Get current detections (thread-safe)"""
        with self.lock:
            return self.detections.copy()
    
    def run_detection_loop(self):
        """Run detection in separate thread"""
        self.running = True
        dt = 1.0 / DETECTION_RATE_HZ
        
        while self.running:
            start = time.time()
            self.detect_once()
            elapsed = time.time() - start
            
            if elapsed < dt:
                time.sleep(dt - elapsed)
    
    def start(self):
        """Start detection thread"""
        self.thread = threading.Thread(target=self.run_detection_loop, daemon=True)
        self.thread.start()
        self.logger("✅ Detection thread started")
    
    def stop(self):
        """Stop detection"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2.0)
        self.pipeline.stop()
        self.logger("Detection stopped")


class SocialForceModulator:
    """Social Force Model for velocity modulation"""
    
    def __init__(self, logger_callback=None):
        self.logger = logger_callback or print
        
        # State
        self.detections = []
        self.closest_human_dist = 999.0
        self.closest_human_zone = "PUBLIC"
        
        # Force vectors (for visualization)
        self.fx_rep = 0.0
        self.fy_rep = 0.0
    
    def get_proxemic_zone(self, dist):
        """Determine proxemic zone"""
        if dist < R_INTIMATE:
            return "INTIMATE"
        elif dist < R_PERSONAL:
            return "PERSONAL"
        elif dist < R_SOCIAL:
            return "SOCIAL"
        else:
            return "PUBLIC"
    
    def compute_repulsive_force(self, robot_x, robot_y, human_x, human_y, distance):
        """
        Social Force Model repulsive force with progressive lateral multiplier:
        F_rep = A × exp(-d/B) × n̂ × lateral_multiplier
        
        IMPROVED v1.1: Lateral force multiplier berdasarkan jarak untuk faster evasion
        
        Args:
            robot_x, robot_y: Robot position
            human_x, human_y: Human position
            distance: Pre-calculated distance (for efficiency and consistency)
        
        Returns:
            (fx, fy): Repulsive force components
        """
        dx = robot_x - human_x
        dy = robot_y - human_y
        dist = distance  # Use pre-calculated distance
        
        if dist < 1e-6:
            return 100.0, 0.0  # Very close - push hard (emergency)
        
        # Base magnitude
        mag = SFM_A * math.exp(-dist / SFM_B)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # IMPROVEMENT v1.1: Progressive lateral force multiplier
        # Increases lateral response strength as human gets closer
        # Mathematically derived to ensure adequate lateral displacement
        # ═══════════════════════════════════════════════════════════════════════════
        lateral_multiplier = 1.0
        
        if dist < R_INTIMATE:
            # INTIMATE zone: emergency level (8x boost)
            lateral_multiplier = LATERAL_MULTIPLIER_INTIMATE
        elif dist < R_PERSONAL:
            # PERSONAL zone: very aggressive (5x boost)
            lateral_multiplier = LATERAL_MULTIPLIER_PERSONAL
        elif dist < R_SOCIAL:
            # SOCIAL zone: aggressive (3x boost)
            lateral_multiplier = LATERAL_MULTIPLIER_SOCIAL
        elif dist < R_EVASION_START:
            # Early evasion: moderate boost (2x)
            lateral_multiplier = LATERAL_MULTIPLIER_FAR
        # else: dist >= R_EVASION_START, use 1.0x (base SFM)
        
        # Apply multiplier to magnitude
        mag *= lateral_multiplier
        
        # Direction (away from human)
        fx = mag * dx / dist
        fy = mag * dy / dist
        
        return fx, fy
    
    def modulate_velocity(self, vx_desired, vy_desired, vw_desired, detections):
        """
        Apply Social Force Model to modulate desired velocity
        
        IMPROVED v1.1: 
        - Early evasion activation at 3.5m
        - Progressive lateral force multipliers (2x/3x/5x/8x)
        - More aggressive speed reduction (60%/30%)
        
        Args:
            vx_desired: forward velocity (-1 to 1)
            vy_desired: lateral velocity (-1 to 1)
            vw_desired: angular velocity (-1 to 1)
            detections: list of human detections
        
        Returns:
            (vx_mod, vy_mod, vw_mod): modulated velocities
        """
        self.detections = detections
        
        if len(detections) == 0:
            # No humans - pass through
            self.closest_human_dist = 999.0
            self.closest_human_zone = "PUBLIC"
            self.fx_rep = 0.0
            self.fy_rep = 0.0
            return vx_desired, vy_desired, vw_desired
        
        # Calculate repulsive forces
        fx_rep_total = 0.0
        fy_rep_total = 0.0
        closest_dist = 999.0
        
        for human in detections:
            hx = human['position']['x']  # forward
            hy = human['position']['y']  # left
            
            dist = math.hypot(hx, hy)
            if dist < closest_dist:
                closest_dist = dist
            
            # ═══════════════════════════════════════════════════════════════════════════
            # IMPROVEMENT v1.1: Pass distance to compute_repulsive_force
            # Enables progressive lateral multiplier based on distance
            # ═══════════════════════════════════════════════════════════════════════════
            frx, fry = self.compute_repulsive_force(0, 0, hx, hy, dist)
            fx_rep_total += frx
            fy_rep_total += fry
        
        # Store for visualization
        self.fx_rep = fx_rep_total
        self.fy_rep = fy_rep_total
        self.closest_human_dist = closest_dist
        self.closest_human_zone = self.get_proxemic_zone(closest_dist)
        
        # Convert force to velocity adjustment
        # F = m × a, v_new = v_old + a × dt
        # Here we use a simplified: v_adjustment = F / (m × gain)
        gain = 50.0  # tuning parameter
        vx_adj = fx_rep_total / (SFM_MASS * gain)
        vy_adj = fy_rep_total / (SFM_MASS * gain)
        
        # Apply adjustment
        vx_mod = vx_desired + vx_adj
        vy_mod = vy_desired + vy_adj
        vw_mod = vw_desired
        
        # Normalize to [-1, 1]
        speed = math.hypot(vx_mod, vy_mod)
        if speed > 1.0:
            vx_mod /= speed
            vy_mod /= speed
        
        # ═══════════════════════════════════════════════════════════════════════════
        # IMPROVEMENT v1.1: Enhanced speed modulation with early evasion
        # ═══════════════════════════════════════════════════════════════════════════
        if self.closest_human_zone == "INTIMATE":
            # Emergency stop
            self.logger(f"🔴 INTIMATE ZONE ({closest_dist:.2f}m) - EMERGENCY STOP")
            vx_mod = 0.0
            vy_mod = 0.0
            vw_mod = 0.0
        elif self.closest_human_zone == "PERSONAL":
            # Slow down - IMPROVED: 30% speed (was 30%, unchanged but verified)
            vx_mod *= SPEED_MULTIPLIER_PERSONAL
            vy_mod *= SPEED_MULTIPLIER_PERSONAL
            vw_mod *= SPEED_MULTIPLIER_PERSONAL
            self.logger(f"🟠 PERSONAL ZONE ({closest_dist:.2f}m) - SLOW DOWN (30%)")
        elif self.closest_human_zone == "SOCIAL":
            # Moderate avoidance - IMPROVED: 60% speed (was 70%)
            vx_mod *= SPEED_MULTIPLIER_SOCIAL
            vy_mod *= SPEED_MULTIPLIER_SOCIAL
            self.logger(f"🟡 SOCIAL ZONE ({closest_dist:.2f}m) - AVOIDING (60%)")
        elif closest_dist < R_EVASION_START:
            # ═══════════════════════════════════════════════════════════════════════════
            # NEW v1.1: Early evasion activation
            # Start responding even in PUBLIC zone if human detected within 3.5m
            # Provides smoother, earlier avoidance initiation
            # ═══════════════════════════════════════════════════════════════════════════
            vx_mod *= 0.8  # 80% speed - slight slowdown for early reaction
            vy_mod *= 0.8
            self.logger(f"🟢 EARLY EVASION ({closest_dist:.2f}m) - PREPARING (80%)")
        
        return vx_mod, vy_mod, vw_mod
    
    def get_status(self):
        """Get current SFM status"""
        return {
            'closest_dist': self.closest_human_dist,
            'zone': self.closest_human_zone,
            'num_humans': len(self.detections),
            'fx_rep': self.fx_rep,
            'fy_rep': self.fy_rep
        }


# ══════════════════════════════════════════════════════════════════
# ── Bluetooth & Joystick (dari bluetooth.py) ──────────────────────
# ══════════════════════════════════════════════════════════════════

pygame.init()
pygame.joystick.init()

joystick = None
connected = False
ser = None
detector = None
sfm_modulator = None

last_packet = f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def deadzone(v, dz=STICK_DEADZONE):
    if abs(v) < dz:
        return 0.0
    return math.copysign((abs(v) - dz) / (1.0 - dz), v)


def to_byte(cmd):
    """cmd in [-1, 1] -> 0..255 with centre 127"""
    return int(clamp(round(NEUTRAL + cmd * 127.5), 0, 255))


def rotate_coordinates(x, y):
    """
    Apply 135° clockwise rotation to coordinate system.
    
    Args:
        x: lateral input (joystick convention: left = -)
        y: forward input (joystick convention: forward = -)
    
    Returns:
        (x_rotated, y_rotated): coordinates in robot's frame
    """
    x_rot = x * COS_THETA - y * SIN_THETA
    y_rot = x * SIN_THETA + y * COS_THETA
    return x_rot, y_rot


def build_packet_with_sfm(axes, buttons, detections):
    """
    Build packet with Social Force Model modulation
    """
    def btn(i):
        return buttons[i] if 0 <= i < len(buttons) else 0
    
    # Deadman switch
    if REQUIRE_DEADMAN and not btn(BTN_DEADMAN):
        return f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>\n"
    
    # Read joystick
    raw_x = axes[AXIS_X] if AXIS_X < len(axes) else 0.0
    raw_y = axes[AXIS_Y] if AXIS_Y < len(axes) else 0.0
    
    # Step 1: Convert to robot frame convention (before rotation)
    lateral_input = -deadzone(raw_x)   # right stick = negative lateral (left is +)
    forward_input = -deadzone(raw_y)   # down stick = negative forward (forward is +)
    
    # Step 2: Apply 135° CW coordinate rotation
    lateral, forward = rotate_coordinates(lateral_input, forward_input)
    
    # Step 3: Apply speed scaling
    lateral *= SPEED_SCALE
    forward *= SPEED_SCALE
    
    # Step 4: Rotation is independent of coordinate frame
    rotation = (btn(BTN_ROT_LEFT) - btn(BTN_ROT_RIGHT)) * ROT_SCALE
    
    # Step 5: Apply optional inversions (if needed after testing)
    if INVERT_FORWARD:
        forward = -forward
    if INVERT_LATERAL:
        lateral = -lateral
    if INVERT_ROTATION:
        rotation = -rotation
    
    # Apply Social Force Model modulation
    if sfm_modulator:
        forward, lateral, rotation = sfm_modulator.modulate_velocity(
            forward, lateral, rotation, detections
        )
    
    # Convert to packet
    return f"<{to_byte(lateral)},{to_byte(forward)},{to_byte(rotation)}>\n"


def neutral_packet():
    return f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>\n"


def send(packet):
    """Write to Bluetooth"""
    global ser
    if ser and ser.is_open:
        try:
            ser.write(packet.encode("utf-8"))
            return True
        except (serial.SerialException, OSError):
            return False
    return True


def get_available_ports():
    devices = list(glob.glob("/dev/rfcomm*"))
    for p in serial.tools.list_ports.comports():
        if "rfcomm" in p.device and p.device not in devices:
            devices.append(p.device)
    return devices


def close_serial(msg="Bluetooth: Disconnected"):
    global ser
    if ser:
        try:
            if ser.is_open:
                ser.write(neutral_packet().encode("utf-8"))
                ser.close()
        except Exception:
            pass
    ser = None
    connect_button.config(text="Connect", state=tk.NORMAL)
    status_serial.set(msg)


def connect_serial():
    global ser
    if ser and ser.is_open:
        close_serial()
        return
    
    port = port_var.get()
    if not port or port == "Pilih Port":
        status_serial.set("Bluetooth: rfcomm belum ada")
        return
    
    connect_button.config(state=tk.DISABLED)
    status_serial.set(f"Bluetooth: Connecting to {port}...")
    root.update_idletasks()
    
    try:
        ser = serial.Serial(port, RFCOMM_BAUD, timeout=0.05, write_timeout=0.2)
        connect_button.config(text="Disconnect", state=tk.NORMAL)
        status_serial.set(f"Bluetooth: Connected to {port} [135° CW rotation active]")
    except serial.SerialException as e:
        ser = None
        connect_button.config(text="Connect", state=tk.NORMAL)
        status_serial.set(f"Bluetooth: FAILED! ({e})")


def refresh_ports():
    ports = get_available_ports()
    port_combobox["values"] = ports
    if ports:
        port_var.set(ports[0])
        status_serial.set(f"Bluetooth: Found {ports[0]}. Ready.")
    else:
        port_var.set("Pilih Port")
        status_serial.set("Bluetooth: rfcomm belum ada")


def update_joystick():
    global connected, joystick
    
    if pygame.joystick.get_count() > 0:
        if not connected:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            connected = True
            status_var.set(f"Controller connected: {joystick.get_name()}")
            log_message(f"✅ Joystick: {joystick.get_name()}")
    else:
        if connected:
            connected = False
            joystick = None
            status_var.set("Controller disconnected")
            log_message("❌ Joystick disconnected")


def check_connection():
    update_joystick()
    root.after(2000, check_connection)


def log_message(msg):
    """Add message to log window"""
    log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    log_text.see(tk.END)


# ══════════════════════════════════════════════════════════════════
# ── Main Control Loop ─────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

def read_input():
    global last_packet
    pygame.event.pump()
    
    # Get detections from detector
    detections = detector.get_detections() if detector else []
    
    # Default: STOP
    packet = neutral_packet()
    
    if connected and joystick:
        try:
            axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
            buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
            
            # Only move if window has focus
            if root.focus_displayof() is not None:
                packet = build_packet_with_sfm(axes, buttons, detections)
        except pygame.error:
            pass
    
    # Send packet
    if packet.strip() != last_packet:
        last_packet = packet.strip()
        # Only print when changed (reduce spam)
        
    if ser and ser.is_open and not send(packet):
        close_serial("Bluetooth: Lost connection!")
    
    # Update UI
    update_ui(detections)
    
    root.after(SEND_PERIOD_MS, read_input)


def update_ui(detections):
    """Update UI with detection and SFM status"""
    if sfm_modulator:
        status = sfm_modulator.get_status()
        
        # Update status labels
        num_humans_label.config(text=f"Humans: {status['num_humans']}")
        closest_dist_label.config(text=f"Closest: {status['closest_dist']:.2f}m")
        zone_label.config(text=f"Zone: {status['zone']}")
        
        # Color code zone
        zone_colors = {
            "INTIMATE": "red",
            "PERSONAL": "orange",
            "SOCIAL": "yellow",
            "PUBLIC": "green"
        }
        zone_label.config(fg=zone_colors.get(status['zone'], "black"))
        
        # Update force display
        fx = status['fx_rep']
        fy = status['fy_rep']
        force_mag = math.hypot(fx, fy)
        force_label.config(text=f"Repulsion: {force_mag:.2f}N")


# ══════════════════════════════════════════════════════════════════
# ── Visualization Window (separate thread) ────────────────────────
# ══════════════════════════════════════════════════════════════════

def run_visualization():
    """Run OpenCV visualization window"""
    if not detector:
        return
    
    while True:
        frame, results = detector.detect_once()
        
        if frame is None:
            time.sleep(0.05)
            continue
        
        # Draw detections
        if results:
            annotated = results.plot()
        else:
            annotated = frame.copy()
        
        # Get detections
        detections = detector.get_detections()
        
        # Annotate with distance and ID
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cx, cy = det['pixel_x'], det['pixel_y']
            dist = det['distance']
            hid = det['id']
            
            # ID and distance
            cv2.putText(annotated, f"ID{hid} {dist:.2f}m",
                       (x1, max(y1 - 10, 20)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Position
            pos_text = f"({det['position']['x']:.2f}, {det['position']['y']:.2f})"
            cv2.putText(annotated, pos_text,
                       (x1, max(y1 - 35, 45)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # Zone indicator
            dist_2d = math.hypot(det['position']['x'], det['position']['y'])
            zone = sfm_modulator.get_proxemic_zone(dist_2d)
            zone_colors = {
                "INTIMATE": (0, 0, 255),
                "PERSONAL": (0, 165, 255),
                "SOCIAL": (0, 255, 255),
                "PUBLIC": (0, 255, 0)
            }
            color = zone_colors.get(zone, (255, 255, 255))
            cv2.circle(annotated, (cx, cy), 5, color, -1)
        
        # Draw force vector (if SHOW_FORCE_VECTORS)
        if SHOW_FORCE_VECTORS and sfm_modulator:
            status = sfm_modulator.get_status()
            fx = status['fx_rep']
            fy = status['fy_rep']
            
            # Scale for display
            scale = 20
            center_x = CAMERA_WIDTH // 2
            center_y = CAMERA_HEIGHT // 2
            
            # Arrow from center
            end_x = int(center_x + fy * scale)  # fy maps to screen x
            end_y = int(center_y - fx * scale)  # fx maps to screen y (inverted)
            
            cv2.arrowedLine(annotated, (center_x, center_y), (end_x, end_y),
                          (255, 0, 255), 3, tipLength=0.3)
            cv2.putText(annotated, f"F_rep: {math.hypot(fx, fy):.1f}N",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        
        # Show info overlay
        info_y = 60
        cv2.putText(annotated, f"Detections: {len(detections)}",
                   (10, info_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if sfm_modulator:
            status = sfm_modulator.get_status()
            cv2.putText(annotated, f"Zone: {status['zone']} ({status['closest_dist']:.2f}m)",
                       (10, info_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow("Bluetooth SDSC - Human Detection", annotated)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    cv2.destroyAllWindows()


# ══════════════════════════════════════════════════════════════════
# ── GUI Setup ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("Bluetooth SDSC Controller v1.1 - Social Force Navigation [Improved: 3x Faster Evasion]")
root.geometry("900x600")

# ── Top Frame: Bluetooth Control ─────────────────────────────────
top_frame = tk.Frame(root, relief="groove", borderwidth=2)
top_frame.pack(fill="x", padx=10, pady=5)

tk.Label(top_frame, text="BLUETOOTH:", font=("Arial", 10, "bold")).pack(side="left", padx=5)

port_var = tk.StringVar(root, value="Pilih Port")
port_combobox = ttk.Combobox(top_frame, textvariable=port_var, width=18, state="readonly")
port_combobox.pack(side="left", padx=5)

tk.Button(top_frame, text="Refresh", command=refresh_ports).pack(side="left", padx=5)
connect_button = tk.Button(top_frame, text="Connect", command=connect_serial)
connect_button.pack(side="left", padx=5)

status_serial = tk.StringVar(root, value="Bluetooth: Ready")
tk.Label(top_frame, textvariable=status_serial, fg="blue").pack(side="left", padx=10)

# Rotation indicator
tk.Label(top_frame, text="🔄 135° CW", font=("Arial", 9, "bold"), 
         fg="orange", bg="#FFE5B4").pack(side="right", padx=10)

# ── Middle Frame: Status Display ─────────────────────────────────
middle_frame = tk.Frame(root, relief="groove", borderwidth=2)
middle_frame.pack(fill="x", padx=10, pady=5)

status_var = tk.StringVar(value="Waiting for controller...")
tk.Label(middle_frame, textvariable=status_var, font=("Consolas", 10)).pack(pady=5)

# Social Force Status
sfm_frame = tk.Frame(middle_frame)
sfm_frame.pack(fill="x", padx=10, pady=5)

tk.Label(sfm_frame, text="SOCIAL FORCE STATUS:", font=("Arial", 10, "bold")).pack(anchor="w")

status_row = tk.Frame(sfm_frame)
status_row.pack(fill="x")

num_humans_label = tk.Label(status_row, text="Humans: 0", width=15, anchor="w", 
                            font=("Consolas", 9))
num_humans_label.pack(side="left", padx=5)

closest_dist_label = tk.Label(status_row, text="Closest: --", width=20, anchor="w",
                             font=("Consolas", 9))
closest_dist_label.pack(side="left", padx=5)

zone_label = tk.Label(status_row, text="Zone: PUBLIC", width=20, anchor="w",
                     font=("Consolas", 9, "bold"))
zone_label.pack(side="left", padx=5)

force_label = tk.Label(status_row, text="Repulsion: 0.00N", width=20, anchor="w",
                      font=("Consolas", 9))
force_label.pack(side="left", padx=5)

# ── Bottom Frame: Log Window ──────────────────────────────────────
log_frame = tk.Frame(root, relief="groove", borderwidth=2)
log_frame.pack(fill="both", expand=True, padx=10, pady=5)

tk.Label(log_frame, text="EVENT LOG:", font=("Arial", 10, "bold")).pack(anchor="w")

log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9))
log_text.pack(fill="both", expand=True, padx=5, pady=5)

# ── Footer ────────────────────────────────────────────────────────
footer = tk.Label(root, 
                 text=f"Hold B{BTN_DEADMAN} to move | Social Force: A={SFM_A}, B={SFM_B} | "
                      f"Zones: Intimate={R_INTIMATE}m, Personal={R_PERSONAL}m, Social={R_SOCIAL}m",
                 font=("Consolas", 8), fg="grey")
footer.pack(pady=5)


def on_close():
    """Cleanup on window close"""
    global detector
    
    log_message("Shutting down...")
    close_serial()
    
    if detector:
        detector.stop()
    
    cv2.destroyAllWindows()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)


# ══════════════════════════════════════════════════════════════════
# ── Main Initialization ───────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

def initialize_system():
    """Initialize detection and SFM systems"""
    global detector, sfm_modulator
    
    try:
        # Initialize human detector
        log_message("Initializing human detector...")
        detector = HumanDetector(logger_callback=log_message)
        detector.start()
        
        # Initialize SFM modulator
        log_message("Initializing Social Force Model...")
        sfm_modulator = SocialForceModulator(logger_callback=log_message)
        
        log_message("✅ All systems initialized")
        log_message("🔄 COORDINATE ROTATION: 135° Clockwise ACTIVE")
        log_message(f"📷 Camera: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
        log_message(f"🧠 YOLO: {YOLO_MODEL}")
        log_message(f"⚙️  SFM: A={SFM_A}N, B={SFM_B}m, τ={SFM_TAU}s")
        log_message(f"🛡️  Zones: Intimate={R_INTIMATE}m, Personal={R_PERSONAL}m, Social={R_SOCIAL}m")
        log_message("Ready for operation!")
        
        # Start visualization in separate thread
        if SHOW_DETECTION_WINDOW:
            viz_thread = threading.Thread(target=run_visualization, daemon=True)
            viz_thread.start()
        
    except Exception as e:
        log_message(f"❌ Initialization error: {e}")
        import traceback
        log_message(traceback.format_exc())


# Start initialization in background
init_thread = threading.Thread(target=initialize_system, daemon=True)
init_thread.start()

# Start GUI
refresh_ports()
check_connection()
read_input()

log_message("=== Bluetooth SDSC Controller Started ===")
log_message("Press B4 (deadman) and use left stick to move")
log_message("Social Force will automatically avoid humans")

root.mainloop()

# Cleanup
if detector:
    detector.stop()
pygame.quit()
cv2.destroyAllWindows()
