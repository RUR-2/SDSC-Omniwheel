#!/usr/bin/env python3
"""
Bluetooth SDSC Controller v2 — NO Speed Reduction Mode
=======================================================
**Identik dengan bluetooth_sdsc.py v1.1, dengan satu perbedaan:**

MODE INI: Robot TIDAK pernah diperlambat oleh SFM.
  - INTIMATE zone  : robot BERHENTI penuh (emergency stop) ✅
  - PERSONAL zone  : kecepatan TIDAK dikurangi (vs 30% di v1)
  - SOCIAL zone    : kecepatan TIDAK dikurangi (vs 60% di v1)
  - Early evasion  : kecepatan TIDAK dikurangi (vs 80% di v1)

Gaya repulsif SFM tetap aktif → robot tetap berbelok menghindari manusia,
hanya saja tidak melambat. Berguna untuk membandingkan dampak speed-reduction
pada uji coba Social Force Model.

Packet format ke ESP32 (via rfcomm): <x,y,w>\n
    x = lateral   (0-255, center 127, left +)
    y = forward   (0-255, center 127, front +)
    w = rotation  (0-255, center 127, CCW +)

Controls:
    Left stick        : forward/back (Y) and strafe (X)
    B6 / B7          : rotate left (CCW) / rotate right (CW)
    Hold B4 (deadman): robot only moves while held
    Release B4       : sends <127,127,127>

Coordinate Transformation:
    - 135° clockwise rotation applied to joystick input
    - Formula: x' = x·cos(-135°) - y·sin(-135°)
              y' = x·sin(-135°) + y·cos(-135°)

Author: Brone Social Nav Team
Version: 2.0 - No Speed Reduction (Direction-Only SFM)
"""

import glob
import math
import os
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
ROTATION_ANGLE_DEG = 135  # clockwise
ROTATION_ANGLE_RAD = math.radians(-ROTATION_ANGLE_DEG)  # negative for CW
COS_THETA = math.cos(ROTATION_ANGLE_RAD)  # cos(-135°) = -√2/2
SIN_THETA = math.sin(ROTATION_ANGLE_RAD)  # sin(-135°) = -√2/2

# ═══════════════════════════════════════════════════════════════════════════
# Social-DSC Parameters  (ported from pimpysim/sim.js — Chen & Liu, IECON 2024)
# ═══════════════════════════════════════════════════════════════════════════

# Proxemic Zones
R_INTIMATE = 0.45   # m
R_PERSONAL = 1.20   # m
R_SOCIAL   = 3.60   # m

# SIM — F_pa: Pedestrian Avoidance Force (Eq. 16)
AP = 2.0    # repulsion amplitude (N)
BP = 0.8    # repulsion range (m)
DP = 0.0    # offset distance

# Legacy SFM aliases (mencegah NameError jika ada referensi ke variabel v1)
SFM_A = AP
SFM_B = BP
SFM_MASS = 5.0
SFM_TAU = 0.5

# SIM — F_sr: Social Rule Force (Eq. 21)  — right-hand traffic
KSR = 1.0   # sigmoid gain
BSR = 3.0   # sigmoid steepness
DSR = 0.2   # lateral offset (right-hand-side bias)

# SIM global
KSIM = 0.35 # velocity output scaling (paper: 0.3)
WPA  = 1.0  # weight F_pa
WPP  = 0.5  # weight F_pp (pedestrian priority)
WSR  = 0.5  # weight F_sr (social rule)

# Asymmetric Gaussian zone shape (metres)
SIGMA_H = 2.4   # ahead of pedestrian  (= ΔT·||v|| = 2s × 1.2m/s)
SIGMA_R = 1.2   # behind pedestrian
SIGMA_L = 1.2   # lateral

# DSC eigenvalue sigmoid steepness
LAMBDA_V_K = 10.0

# Camera & Detection
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
DETECTION_RATE_HZ = 10       # Detection frequency
YOLO_ENGINE_MODEL = "yolo11n.engine"  # TensorRT FP16 engine (prioritas Jetson)
YOLO_PT_MODEL = "yolo11n.pt"          # PyTorch model (fallback / sumber export)
YOLO_MODEL = YOLO_ENGINE_MODEL if os.path.exists(YOLO_ENGINE_MODEL) else YOLO_PT_MODEL
YOLO_HALF = True             # Gunakan FP16 inference untuk kurangi beban GPU & Unified Memory
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
        self.last_frame = None        # Cache frame terakhir untuk visualisasi
        self.last_results = None      # Cache YOLO results terakhir
        self.last_debug_depth = None  # Cache statistik depth untuk visualisasi (tanpa wait_for_frames di thread viz)
        self.lock = threading.Lock()
        
        # Tracking
        self.next_id = 1
        self.tracked_humans = {}  # {id: (cx, cy, last_seen_time)}
        
        # YOLO model (prioritaskan TensorRT FP16 .engine di Jetson)
        self.active_model_path = YOLO_MODEL
        self.model = self._load_yolo_model()
        
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
    
    def _load_yolo_model(self):
        """Load TensorRT FP16 engine (.engine) jika ada, atau auto-export dari .pt di CUDA/Jetson."""
        if os.path.exists(YOLO_ENGINE_MODEL):
            self.logger(f"🚀 Loading TensorRT FP16 engine: {YOLO_ENGINE_MODEL}...")
            self.active_model_path = YOLO_ENGINE_MODEL
            return YOLO(YOLO_ENGINE_MODEL, task="detect")

        if os.path.exists(YOLO_PT_MODEL):
            try:
                import torch
                if torch.cuda.is_available():
                    self.logger(
                        f"⚡ {YOLO_ENGINE_MODEL} belum ada. Export otomatis TensorRT FP16 dari {YOLO_PT_MODEL}..."
                    )
                    pt_model = YOLO(YOLO_PT_MODEL)
                    exported_path = pt_model.export(format="engine", half=True, imgsz=640)
                    engine_path = str(exported_path) if exported_path else YOLO_ENGINE_MODEL
                    if os.path.exists(engine_path):
                        self.logger(f"✅ TensorRT FP16 engine siap: {engine_path}")
                        self.active_model_path = engine_path
                        return YOLO(engine_path, task="detect")
            except Exception as e:
                self.logger(
                    f"⚠️ Auto-export TensorRT dilewati ({e}). Fallback ke PyTorch {YOLO_PT_MODEL}."
                )

        self.logger(f"Loading YOLOv11 PyTorch model: {YOLO_PT_MODEL}...")
        self.active_model_path = YOLO_PT_MODEL
        return YOLO(YOLO_PT_MODEL)

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
                self.logger("⚠️ Missing depth or color frame")
                return None, None
            
            frame = np.asanyarray(color_frame.get_data())
            
            # YOLO inference (class 0 = person, FP16 untuk kurangi beban GPU & Unified Memory)
            results = self.model(
                frame,
                classes=[0],
                conf=YOLO_CONFIDENCE,
                half=YOLO_HALF,
                verbose=False,
            )
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
            # Hitung statistik debug depth di sini (satu kali pada 10 Hz) agar
            # thread visualisasi tidak perlu memanggil pipeline.wait_for_frames() lagi.
            debug_depth = None
            if len(boxes) > 0:
                x1_d, y1_d, x2_d, y2_d = map(int, boxes[0][:4])
                cx_debug = (x1_d + x2_d) // 2
                cy_debug = (y1_d + y2_d) // 2
                w_d, h_d = depth_frame.get_width(), depth_frame.get_height()
                depth_center = (
                    depth_frame.get_distance(cx_debug, cy_debug)
                    if (0 <= cx_debug < w_d and 0 <= cy_debug < h_d)
                    else 0.0
                )
                depths_around = []
                for dy in (-20, 0, 20):
                    for dx in (-20, 0, 20):
                        sx, sy = cx_debug + dx, cy_debug + dy
                        if 0 <= sx < w_d and 0 <= sy < h_d:
                            d = depth_frame.get_distance(sx, sy)
                            if d > 0:
                                depths_around.append(d)
                debug_depth = {
                    'center': depth_center,
                    'avg': (sum(depths_around) / len(depths_around)) if depths_around else None,
                    'valid_count': len(depths_around),
                }
            
            detections = []
            
            for box, conf in zip(boxes, confidences):
                if conf < YOLO_CONFIDENCE:
                    continue
                
                x1, y1, x2, y2 = map(int, box[:4])
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                # Try center first
                distance = depth_frame.get_distance(cx, cy)
                
                # If center is invalid, try sampling multiple points in the bounding box
                if distance <= MIN_DISTANCE or distance > MAX_DISTANCE:
                    sample_points = [
                        (cx, cy),
                        (cx, int(cy - (y2-y1)*0.25)),
                        (cx, int(cy + (y2-y1)*0.25)),
                        (int(cx - (x2-x1)*0.15), cy),
                        (int(cx + (x2-x1)*0.15), cy),
                    ]
                    
                    valid_depths = []
                    for sx, sy in sample_points:
                        if 0 <= sx < depth_frame.get_width() and 0 <= sy < depth_frame.get_height():
                            d = depth_frame.get_distance(sx, sy)
                            if MIN_DISTANCE < d <= MAX_DISTANCE:
                                valid_depths.append(d)
                    
                    if len(valid_depths) == 0:
                        self.logger(f"⚠️ No valid depth for detection at ({cx},{cy}), bbox confidence {conf:.2f}")
                        continue
                    
                    distance = sorted(valid_depths)[len(valid_depths) // 2]
                    self.logger(f"✅ Used multi-point sampling: {distance:.2f}m from {len(valid_depths)} valid points")
                
                # Tracking
                human_id = self.match_detection_to_track(cx, cy)
                
                # Transform to robot frame
                cam_x, cam_y, cam_z = self.pixel_to_camera_frame(cx, cy, distance)
                robot_x, robot_y, robot_z = self.camera_to_robot_frame(cam_x, cam_y, cam_z)
                
                # Calculate 2D distance for logging
                dist_2d = math.hypot(robot_x, robot_y)
                
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
                
                self.logger(f"✅ Detected ID{human_id}: dist={distance:.2f}m, 2D={dist_2d:.2f}m, pos=({robot_x:.2f},{robot_y:.2f}), conf={conf:.2f}")
            
            # Update shared state
            with self.lock:
                self.detections = detections
                self.last_frame = frame
                self.last_results = results[0]
                self.last_debug_depth = debug_depth
            
            return frame, results[0]
        
        except Exception as e:
            self.logger(f"Detection error: {e}")
            return None, None
    
    def get_detections(self):
        """Get current detections (thread-safe)"""
        with self.lock:
            return self.detections.copy()
    
    def get_last_frame(self):
        """Get last captured frame dan YOLO results (thread-safe)."""
        with self.lock:
            return self.last_frame, self.last_results
    
    def get_last_debug_depth(self):
        """Get cached depth debug statistics (thread-safe, tanpa menyentuh RealSense pipeline)."""
        with self.lock:
            return self.last_debug_depth.copy() if self.last_debug_depth else None
    
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
    """
    Social-DSC Modulator — ported dari pimpysim/sim.js
    Implementasi: Chen & Liu, IECON 2024
    "Dynamical System based Socially-aware Navigation for Mobile Robot"

    Algoritma:
      1. F_pa  — Pedestrian Avoidance Force  (Eq. 16-18)
      2. F_pp  — Pedestrian Priority Force   (Eq. 19-20)
      3. F_sr  — Social Rule Force           (Eq. 21-22)
      4. f_SIM — Gabungan ke-tiga force      (Eq. 14-15)
      5. M     — DSC Modulation Matrix       (Eq. 5-13)
      6. v_out = M · (v_nominal + f_SIM)     (Eq. 10)

    Input/output ke bluetooth tidak berubah.
    INTIMATE zone tetap emergency stop.
    """

    def __init__(self, logger_callback=None):
        self.logger = logger_callback or print

        # Public state (dibaca oleh UI & visualisasi)
        self.detections          = []
        self.closest_human_dist  = 999.0
        self.closest_human_zone  = "PUBLIC"
        self.fx_rep              = 0.0   # total f_SIM x (untuk label "Repulsion")
        self.fy_rep              = 0.0   # total f_SIM y

    # ──────────────────────────────────────────────────────────────
    # Zona proxemik
    # ──────────────────────────────────────────────────────────────
    def get_proxemic_zone(self, dist):
        if dist < R_INTIMATE: return "INTIMATE"
        if dist < R_PERSONAL: return "PERSONAL"
        if dist < R_SOCIAL:   return "SOCIAL"
        return "PUBLIC"

    # ──────────────────────────────────────────────────────────────
    # Fungsi bantu (porting dari sim.js)
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _dot(ax, ay, bx, by):
        return ax * bx + ay * by

    @staticmethod
    def _cross2d(ax, ay, bx, by):
        return ax * by - ay * bx

    @staticmethod
    def _norm(x, y):
        m = math.hypot(x, y) or 1e-9
        return x / m, y / m

    # ──────────────────────────────────────────────────────────────
    # Γ — Asymmetric Gaussian distance (Eq. 3)
    #   Returns Γ; Γ = 1 is the zone boundary
    # ──────────────────────────────────────────────────────────────
    def _gamma(self, rx, ry, hx, hy, h_angle):
        dx, dy = rx - hx, ry - hy
        cos_a, sin_a = math.cos(h_angle), math.sin(h_angle)
        d_long =  cos_a * dx + sin_a * dy   # along heading
        d_lat  = -sin_a * dx + cos_a * dy   # lateral
        sigma_long = SIGMA_H if d_long >= 0 else SIGMA_R
        return (d_long / sigma_long) ** 2 + (d_lat / SIGMA_L) ** 2

    # Numerical gradient of Γ w.r.t. robot position
    def _gamma_grad(self, rx, ry, hx, hy, h_angle):
        eps = 0.001
        g0 = self._gamma(rx,       ry,       hx, hy, h_angle)
        gx = (self._gamma(rx + eps, ry,       hx, hy, h_angle) - g0) / eps
        gy = (self._gamma(rx,       ry + eps, hx, hy, h_angle) - g0) / eps
        return gx, gy

    # ──────────────────────────────────────────────────────────────
    # λv — approach-velocity eigenvalue (Eq. 7)
    # ──────────────────────────────────────────────────────────────
    def _lambda_v(self, rx, ry, rvx, rvy, hx, hy, hvx, hvy):
        rel_vx, rel_vy = rvx - hvx, rvy - hvy
        dir_x,  dir_y  = rx  - hx,  ry  - hy
        d_dot = self._dot(rel_vx, rel_vy, dir_x, dir_y)
        return 1.0 / (1.0 + math.exp(-LAMBDA_V_K * d_dot))

    # ──────────────────────────────────────────────────────────────
    # DSC Modulation matrix for one human (Eq. 5-9)
    # Returns 2×2 matrix elements m00, m01, m10, m11 and Gamma
    # ──────────────────────────────────────────────────────────────
    def _dsc_modulation_one(self, rx, ry, rvx, rvy, hx, hy, h_angle, h_speed):
        Gamma = self._gamma(rx, ry, hx, hy, h_angle)

        hvx = math.cos(h_angle) * h_speed
        hvy = math.sin(h_angle) * h_speed
        lv  = self._lambda_v(rx, ry, rvx, rvy, hx, hy, hvx, hvy)

        inv   = 1.0 / max(Gamma, 0.01)
        lam_n = lv + (1 - lv) * (1 - inv)   # Eq. 7 — 0 at boundary
        lam_e = lv + (1 - lv) * (1 + inv)   # Eq. 8 — large at boundary

        gx, gy = self._gamma_grad(rx, ry, hx, hy, h_angle)
        nx, ny = self._norm(gx, gy)          # normal vector
        ex, ey = -ny, nx                     # tangent (90° CCW)

        # M = E D E^T  (E orthogonal)
        m00 = lam_n * nx * nx + lam_e * ex * ex
        m01 = lam_n * nx * ny + lam_e * ex * ey
        m10 = lam_n * ny * nx + lam_e * ey * ex
        m11 = lam_n * ny * ny + lam_e * ey * ey
        return m00, m01, m10, m11, Gamma

    # ──────────────────────────────────────────────────────────────
    # Combined modulation matrix — weighted avg (Eq. 11-13)
    # ──────────────────────────────────────────────────────────────
    def _combined_modulation(self, rx, ry, rvx, rvy, humans_info):
        """
        humans_info: list of (hx, hy, h_angle, h_speed)
        Returns: m00, m01, m10, m11
        """
        if not humans_info:
            return 1.0, 0.0, 0.0, 1.0

        mats = [self._dsc_modulation_one(rx, ry, rvx, rvy, hx, hy, ang, spd)
                for hx, hy, ang, spd in humans_info]

        if len(mats) == 1:
            m00, m01, m10, m11, _ = mats[0]
            return m00, m01, m10, m11

        Gammas = [m[4] for m in mats]

        # ω'_i = Π_{j≠i} (Γ_j − 1)  [Eq. 13]
        omega_prime = []
        for i in range(len(Gammas)):
            prod = 1.0
            for j, gj in enumerate(Gammas):
                if j != i:
                    prod *= max(gj - 1.0, 0.0)
            omega_prime.append(prod)

        sum_w = sum(omega_prime) or 1.0
        omega = [w / sum_w for w in omega_prime]  # [Eq. 12]

        cm00 = sum(omega[i] * mats[i][0] for i in range(len(mats)))
        cm01 = sum(omega[i] * mats[i][1] for i in range(len(mats)))
        cm10 = sum(omega[i] * mats[i][2] for i in range(len(mats)))
        cm11 = sum(omega[i] * mats[i][3] for i in range(len(mats)))
        return cm00, cm01, cm10, cm11

    # ──────────────────────────────────────────────────────────────
    # SIM Forces
    # ──────────────────────────────────────────────────────────────
    def _compute_fpa(self, rx, ry, humans_info):
        """F_pa — Pedestrian Avoidance (Eq. 16-18)"""
        fx, fy = 0.0, 0.0
        for hx, hy, _, _ in humans_info:
            dx, dy = rx - hx, ry - hy
            dist   = math.hypot(dx, dy)
            if dist < 1e-6:
                fx += 50.0; continue
            mag = AP * math.exp((DP - dist) / BP)
            fx += mag * dx / dist
            fy += mag * dy / dist
        return fx, fy

    def _compute_fpp(self, rx, ry, humans_info):
        """F_pp — Pedestrian Priority (Eq. 19-20)
        Attacts robot toward a point 1 m to the right of each pedestrian,
        clearing the pedestrian's forward path.
        """
        fx, fy = 0.0, 0.0
        for hx, hy, h_angle, _ in humans_info:
            dx, dy = rx - hx, ry - hy
            dist   = math.hypot(dx, dy)
            if dist > R_SOCIAL * 1.1 or dist < 1e-6:
                continue
            hfx = math.cos(h_angle)
            hfy = math.sin(h_angle)
            lx, ly = -hfy, hfx  # left-normal of pedestrian

            # Target = 1 m to pedestrian's right (−left)
            tx, ty = hx - lx, hy - ly
            tdx, tdy = tx - rx, ty - ry
            tdist = math.hypot(tdx, tdy)
            if tdist < 1e-6:
                continue
            mag = AP * 0.5 * math.exp((DP - dist) / BP)
            fx += mag * tdx / tdist
            fy += mag * tdy / tdist
        return fx, fy

    def _compute_fsr(self, rx, ry, humans_info):
        """F_sr — Social Rule / right-hand traffic (Eq. 21-22)"""
        fx, fy = 0.0, 0.0
        for hx, hy, h_angle, _ in humans_info:
            dx, dy = rx - hx, ry - hy
            dist   = math.hypot(dx, dy)
            if dist > R_SOCIAL or dist < 1e-6:
                continue
            nvx = math.cos(h_angle)
            nvy = math.sin(h_angle)
            # left-normal of pedestrian heading
            nv_lx, nv_ly = -nvy, nvx

            # λr = cross(nv, ξ̃) − δ  [Eq. 22]
            lambda_r = self._cross2d(nvx, nvy, dx / dist, dy / dist) - DSR
            sigmoid  = 1.0 / (1.0 + math.exp(-BSR * lambda_r))

            mag = KSR * sigmoid
            fx += mag * nv_lx
            fy += mag * nv_ly
        return fx, fy

    def _compute_fsim(self, rx, ry, humans_info):
        """f_SIM — combine F_pa, F_pp, F_sr and normalise (Eq. 14-15)"""
        fpa_x, fpa_y = self._compute_fpa(rx, ry, humans_info)
        fpp_x, fpp_y = self._compute_fpp(rx, ry, humans_info)
        fsr_x, fsr_y = self._compute_fsr(rx, ry, humans_info)

        Fx = WPA * fpa_x + WPP * fpp_x + WSR * fsr_x
        Fy = WPA * fpa_y + WPP * fpp_y + WSR * fsr_y
        mag = math.hypot(Fx, Fy)

        # Store for diagnostics (F_pa as "repulsion" shown in UI)
        self.fx_rep = fpa_x
        self.fy_rep = fpa_y
        self._fsr_x = fsr_x
        self._fsr_y = fsr_y

        if mag < 0.01:
            return 0.0, 0.0
        return KSIM * Fx / mag, KSIM * Fy / mag

    # ──────────────────────────────────────────────────────────────
    # Main entry — modulate_velocity
    # Signature identik dengan v1/v2 sehingga read_input() tidak perlu diubah
    # ──────────────────────────────────────────────────────────────
    def modulate_velocity(self, vx_desired, vy_desired, vw_desired, detections):
        """
        Social-DSC velocity modulation.

        Args:
            vx_desired : forward velocity [-1, 1]
            vy_desired : lateral velocity [-1, 1]
            vw_desired : angular velocity [-1, 1]
            detections : list dari HumanDetector.get_detections()

        Returns:
            (vx_mod, vy_mod, vw_mod)
        """
        self.detections = detections

        if not detections:
            self.closest_human_dist = 999.0
            self.closest_human_zone = "PUBLIC"
            self.fx_rep = 0.0
            self.fy_rep = 0.0
            return vx_desired, vy_desired, vw_desired

        # ── Konversi detections → format internal ──────────────────
        # Robot berada di origin (0, 0) dalam robot frame
        # hx = forward (x), hy = lateral (y)
        # Heading manusia: tidak tersedia dari kamera → 0 rad (hadap depan)
        # Speed manusia: tidak diketahui → 0 (asumsi diam)
        humans_info = []  # list of (hx, hy, h_angle, h_speed)
        closest_dist = 999.0

        for det in detections:
            hx    = det['position']['x']   # forward
            hy    = det['position']['y']   # lateral
            dist  = math.hypot(hx, hy)
            if dist < closest_dist:
                closest_dist = dist
            # Heading manusia diperkirakan: menghadap robot (berlawanan arah)
            h_angle = math.atan2(-hy, -hx)
            h_speed = 0.0   # tidak ada odometri manusia dari kamera
            humans_info.append((hx, hy, h_angle, h_speed))

        self.closest_human_dist = closest_dist
        self.closest_human_zone = self.get_proxemic_zone(closest_dist)

        # ── INTIMATE → emergency stop (safety invariant) ────────────
        if self.closest_human_zone == "INTIMATE":
            self.logger(f"[INTIMATE] {closest_dist:.2f}m — EMERGENCY STOP")
            self.fx_rep = 0.0
            self.fy_rep = 0.0
            return 0.0, 0.0, 0.0

        # ── f_SIM: social inference forces ─────────────────────────
        # Robot position = (0, 0), velocity = (vx_desired, vy_desired)
        fsim_x, fsim_y = self._compute_fsim(0.0, 0.0, humans_info)

        # ── Combined nominal + SIM ──────────────────────────────────
        f_total_x = vx_desired + fsim_x
        f_total_y = vy_desired + fsim_y

        # ── DSC modulation matrix M ─────────────────────────────────
        m00, m01, m10, m11 = self._combined_modulation(
            0.0, 0.0, vx_desired, vy_desired, humans_info
        )

        # ── ξ̇ = M · f_total  (Eq. 10) ──────────────────────────────
        vx_mod = m00 * f_total_x + m01 * f_total_y
        vy_mod = m10 * f_total_x + m11 * f_total_y
        vw_mod = vw_desired

        # ── Speed cap: preserve direction, cap magnitude at [-1, 1] ─
        speed = math.hypot(vx_mod, vy_mod)
        if speed > 1.0:
            vx_mod /= speed
            vy_mod /= speed

        zone = self.closest_human_zone
        if zone == "PERSONAL":
            self.logger(f"[PERSONAL] {closest_dist:.2f}m — DSC active")
        elif zone == "SOCIAL":
            self.logger(f"[SOCIAL]   {closest_dist:.2f}m — DSC active")

        return vx_mod, vy_mod, vw_mod

    def get_status(self):
        """Get current status — kompatibel dengan update_ui() yang sudah ada."""
        return {
            'closest_dist': self.closest_human_dist,
            'zone':         self.closest_human_zone,
            'num_humans':   len(self.detections),
            'fx_rep':       self.fx_rep,   # F_pa x
            'fy_rep':       self.fy_rep,   # F_pa y
        }


# ══════════════════════════════════════════════════════════════════
# ── Bluetooth & Joystick ──────────────────────────────────────────
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
    """Apply 135° clockwise rotation to coordinate system."""
    x_rot = x * COS_THETA - y * SIN_THETA
    y_rot = x * SIN_THETA + y * COS_THETA
    return x_rot, y_rot


def build_packet_with_sfm(axes, buttons, vx_mod, vy_mod, vw_mod):
    """
    Build packet dari kecepatan yang sudah dimodulasi SFM.
    modulate_velocity sudah dipanggil di read_input() sebelum fungsi ini.
    """
    def btn(i):
        return buttons[i] if 0 <= i < len(buttons) else 0

    # Deadman switch
    if REQUIRE_DEADMAN and not btn(BTN_DEADMAN):
        return f"<{NEUTRAL},{NEUTRAL},{NEUTRAL}>\n"

    # Convert to packet (vx=forward, vy=lateral, vw=rotation)
    return f"<{to_byte(vy_mod)},{to_byte(vx_mod)},{to_byte(vw_mod)}>\n"


def compute_joystick_velocity(axes, buttons):
    """
    Baca joystick dan konversi ke vektor kecepatan (forward, lateral, rotation)
    dalam range [-1, 1]. Belum termodulasi SFM.
    """
    def btn(i):
        return buttons[i] if 0 <= i < len(buttons) else 0

    raw_x = axes[AXIS_X] if AXIS_X < len(axes) else 0.0
    raw_y = axes[AXIS_Y] if AXIS_Y < len(axes) else 0.0

    lateral_input = -deadzone(raw_x)
    forward_input = -deadzone(raw_y)

    lateral, forward = rotate_coordinates(lateral_input, forward_input)

    lateral *= SPEED_SCALE
    forward *= SPEED_SCALE

    rotation = (btn(BTN_ROT_LEFT) - btn(BTN_ROT_RIGHT)) * ROT_SCALE

    if INVERT_FORWARD:
        forward = -forward
    if INVERT_LATERAL:
        lateral = -lateral
    if INVERT_ROTATION:
        rotation = -rotation

    return forward, lateral, rotation


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
    try:
        connect_button.config(text="Connect", state=tk.NORMAL)
        status_serial.set(msg)
    except NameError:
        pass


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
        status_serial.set(f"Bluetooth: Connected to {port} [135° CW | NO speed reduction]")
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

    # ─────────────────────────────────────────────────────────────────
    # Hitung kecepatan joystick (jika ada) dan panggil modulate_velocity
    # SATU KALI — terlepas dari apakah joystick terhubung atau
    # window punya fokus — agar panel UI selalu ter-update.
    # ─────────────────────────────────────────────────────────────────
    vx, vy, vw = 0.0, 0.0, 0.0
    axes_cache = []
    buttons_cache = []

    if connected and joystick:
        try:
            axes_cache = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
            buttons_cache = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
            if root.focus_displayof() is not None:
                vx, vy, vw = compute_joystick_velocity(axes_cache, buttons_cache)
        except pygame.error:
            pass

    # Panggil SFM satu kali — update state untuk UI sekaligus modulasi arah
    if sfm_modulator:
        vx, vy, vw = sfm_modulator.modulate_velocity(vx, vy, vw, detections)

    # Build packet
    packet = neutral_packet()
    if connected and joystick and axes_cache:
        try:
            packet = build_packet_with_sfm(axes_cache, buttons_cache, vx, vy, vw)
        except pygame.error:
            pass

    # Send packet
    if packet.strip() != last_packet:
        last_packet = packet.strip()

    if ser and ser.is_open and not send(packet):
        close_serial("Bluetooth: Lost connection!")

    # Update UI
    update_ui(detections)

    root.after(SEND_PERIOD_MS, read_input)


def update_ui(detections):
    """Update UI with detection and SFM status"""
    if sfm_modulator:
        status = sfm_modulator.get_status()

        num_humans_label.config(text=f"Humans: {status['num_humans']}")
        closest_dist_label.config(text=f"Closest: {status['closest_dist']:.2f}m")
        zone_label.config(text=f"Zone: {status['zone']}")

        zone_colors = {
            "INTIMATE": "red",
            "PERSONAL": "orange",
            "SOCIAL": "yellow",
            "PUBLIC": "green"
        }
        zone_label.config(fg=zone_colors.get(status['zone'], "black"))

        fx = status['fx_rep']
        fy = status['fy_rep']
        force_mag = math.hypot(fx, fy)
        force_label.config(text=f"Repulsion: {force_mag:.2f}N")


# ══════════════════════════════════════════════════════════════════
# ── Visualization Window (separate thread) ────────────────────────
# ══════════════════════════════════════════════════════════════════

def run_visualization():
    """Run OpenCV visualization window.

    Seluruh pembacaan frame dan statistik depth menggunakan cache dari
    HumanDetector (get_last_frame & get_last_debug_depth) sehingga TIDAK pernah
    memanggil detector.pipeline.wait_for_frames() atau detector.align.process()
    dari thread visualisasi.
    """
    if not detector:
        return

    frame_dt = 1.0 / CAMERA_FPS
    last_raw_frame = None
    cached_base_annotated = None

    while True:
        t_loop_start = time.time()
        frame, results = detector.get_last_frame()

        if frame is None:
            time.sleep(0.05)
            continue

        # Render results.plot() hanya saat ada frame baru dari detector (10 Hz),
        # bukan di-plot ulang 30x/detik yang memicu salinan tensor GPU/Unified Memory.
        if frame is not last_raw_frame or cached_base_annotated is None:
            last_raw_frame = frame
            cached_base_annotated = results.plot() if results else frame.copy()

        annotated = cached_base_annotated.copy()

        detections = detector.get_detections()
        debug_depth = detector.get_last_debug_depth()

        # DEBUG: Show depth frame statistics (dari cache detect_once, tanpa wait_for_frames)
        if debug_depth is not None:
            cv2.putText(annotated, f"DEBUG Depth@center: {debug_depth['center']:.3f}m",
                       (10, CAMERA_HEIGHT - 60), cv2.FONT_HERSHEY_SIMPLEX,
                       0.5, (0, 255, 255), 1)
            if debug_depth['avg'] is not None:
                cv2.putText(annotated, f"DEBUG Avg depth (3x3): {debug_depth['avg']:.3f}m",
                           (10, CAMERA_HEIGHT - 40), cv2.FONT_HERSHEY_SIMPLEX,
                           0.5, (0, 255, 255), 1)
                cv2.putText(annotated, f"DEBUG Valid samples: {debug_depth['valid_count']}/9",
                           (10, CAMERA_HEIGHT - 20), cv2.FONT_HERSHEY_SIMPLEX,
                           0.5, (0, 255, 255), 1)

        # Annotate with distance and ID
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            cx, cy = det['pixel_x'], det['pixel_y']
            dist = det['distance']
            hid = det['id']

            cv2.putText(annotated, f"ID{hid} {dist:.2f}m",
                       (x1, max(y1 - 10, 20)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            pos_text = f"({det['position']['x']:.2f}, {det['position']['y']:.2f})"
            cv2.putText(annotated, pos_text,
                       (x1, max(y1 - 35, 45)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)

            dist_2d = math.hypot(det['position']['x'], det['position']['y'])
            zone = sfm_modulator.get_proxemic_zone(dist_2d) if sfm_modulator else "PUBLIC"
            zone_colors = {
                "INTIMATE": (0, 0, 255),
                "PERSONAL": (0, 165, 255),
                "SOCIAL": (0, 255, 255),
                "PUBLIC": (0, 255, 0)
            }
            color = zone_colors.get(zone, (255, 255, 255))
            cv2.circle(annotated, (cx, cy), 5, color, -1)

        # Draw force vector
        if SHOW_FORCE_VECTORS and sfm_modulator:
            status = sfm_modulator.get_status()
            fx = status['fx_rep']
            fy = status['fy_rep']

            scale = 20
            center_x = CAMERA_WIDTH // 2
            center_y = CAMERA_HEIGHT // 2

            end_x = int(center_x + fy * scale)
            end_y = int(center_y - fx * scale)

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

        # v2 mode indicator
        cv2.putText(annotated, "MODE: NO SPEED REDUCTION",
                   (10, info_y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 255), 2)

        cv2.imshow("Bluetooth SDSC v2 - Human Detection [No Speed Reduction]", annotated)

        elapsed = time.time() - t_loop_start
        sleep_ms = max(1, int((frame_dt - elapsed) * 1000))

        key = cv2.waitKey(sleep_ms) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()


# ══════════════════════════════════════════════════════════════════
# ── GUI Setup ─────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

root = tk.Tk()
root.title("Bluetooth SDSC Controller v2 - NO Speed Reduction [Direction-Only SFM]")
root.geometry("900x620")

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

# Mode indicator
tk.Label(top_frame, text="🚀 NO SPEED REDUCTION", font=("Arial", 9, "bold"),
         fg="white", bg="#CC0000").pack(side="right", padx=10)

tk.Label(top_frame, text="🔄 135° CW", font=("Arial", 9, "bold"),
         fg="orange", bg="#FFE5B4").pack(side="right", padx=5)

# ── Mode Info Banner ─────────────────────────────────────────────
banner = tk.Frame(root, bg="#330000", relief="groove", borderwidth=2)
banner.pack(fill="x", padx=10, pady=2)
tk.Label(banner,
         text="v2 MODE: SFM hanya mengubah ARAH gerak (tidak mengurangi kecepatan). "
              "Emergency stop tetap aktif di zona INTIMATE (<0.45m).",
         font=("Consolas", 8, "bold"), fg="#FF6666", bg="#330000").pack(pady=4)

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

# Speed mode indicator per zone
speed_row = tk.Frame(sfm_frame)
speed_row.pack(fill="x", pady=2)
tk.Label(speed_row, text="Speed per zone →", font=("Consolas", 8), fg="grey").pack(side="left", padx=5)
tk.Label(speed_row, text="INTIMATE: STOP", font=("Consolas", 8, "bold"), fg="red").pack(side="left", padx=4)
tk.Label(speed_row, text="PERSONAL: 100%", font=("Consolas", 8, "bold"), fg="orange").pack(side="left", padx=4)
tk.Label(speed_row, text="SOCIAL: 100%", font=("Consolas", 8, "bold"), fg="#AAAA00").pack(side="left", padx=4)
tk.Label(speed_row, text="PUBLIC: 100%", font=("Consolas", 8, "bold"), fg="green").pack(side="left", padx=4)

# ── Bottom Frame: Log Window ──────────────────────────────────────
log_frame = tk.Frame(root, relief="groove", borderwidth=2)
log_frame.pack(fill="both", expand=True, padx=10, pady=5)

tk.Label(log_frame, text="EVENT LOG:", font=("Arial", 10, "bold")).pack(anchor="w")

log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9))
log_text.pack(fill="both", expand=True, padx=5, pady=5)

# ── Footer ────────────────────────────────────────────────────────
footer = tk.Label(root,
                 text=f"Hold B{BTN_DEADMAN} to move | Social-DSC: Ap={AP}, Bp={BP} | "
                      f"Zones: Intimate={R_INTIMATE}m (STOP), Personal={R_PERSONAL}m, Social={R_SOCIAL}m | "
                      f"v2: NO speed reduction",
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
        log_message("Initializing human detector...")
        detector = HumanDetector(logger_callback=log_message)
        detector.start()

        log_message("Initializing Social Force Model (v2 - No Speed Reduction)...")
        sfm_modulator = SocialForceModulator(logger_callback=log_message)

        log_message("✅ All systems initialized")
        log_message("🔄 COORDINATE ROTATION: 135° Clockwise ACTIVE")
        log_message("🚀 MODE: Direction-Only SFM — NO speed reduction in any zone")
        log_message("🔴 SAFETY: Emergency stop STILL active in INTIMATE zone (<0.45m)")
        log_message(f"📷 Camera: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
        log_message(f"🧠 YOLO: {detector.active_model_path} (FP16={YOLO_HALF})")
        log_message(f"⚙️  Social-DSC: Ap={AP}N, Bp={BP}m, KSIM={KSIM}")
        log_message(f"🛡️  Zones: Intimate={R_INTIMATE}m (STOP), Personal={R_PERSONAL}m, Social={R_SOCIAL}m")
        log_message("Ready for operation!")

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

log_message("=== Bluetooth SDSC Controller v2 Started (No Speed Reduction) ===")
log_message("Press B4 (deadman) and use left stick to move")
log_message("SFM will deflect direction to avoid humans — speed unchanged")
log_message("ONLY intimate zone (<0.45m) triggers emergency stop")

root.mainloop()

# Cleanup
if detector:
    detector.stop()
pygame.quit()
cv2.destroyAllWindows()
