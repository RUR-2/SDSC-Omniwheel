#!/usr/bin/env python3
"""
Tester102 - Manual Movement Sampling with Social Force Calculation
===================================================================
Testing tool untuk robot omniwheel yang rusak (tidak bisa bergerak).

Features:
  - Robot digerakkan manual oleh user
  - User press SPACE untuk sampling setiap 1/4 detik
  - Social force calculation dengan initial velocity 1.0 m/s
  - RealSense + YOLO untuk deteksi manusia
  - Output: Grafik trajectory + displacement command
  - Displacement format: X+ = kanan, Y+ = depan (contoh: +0.4X +0.5Y)

Controls:
  - SPACE: Ambil sample berikutnya
  - Q: Quit dan tampilkan grafik
  - R: Reset trajectory
  - S: Save data to CSV

Author: SDSC Team
Version: 2.0 (Clean rebuild)
Date: 2026-10-04
"""

import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import time
import math
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd


# ══════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════

SAMPLE_INTERVAL = 0.25      # seconds (1/4 detik)
INITIAL_VELOCITY = 1.0      # m/s - kecepatan awal robot

# Social Force Model
SFM_V0 = INITIAL_VELOCITY
SFM_TAU = 0.5
SFM_A = 5.0
SFM_B = 0.8
SFM_MASS = 5.0

# Proxemic zones
R_INTIMATE = 0.45
R_PERSONAL = 1.20
R_SOCIAL = 3.60

# Camera
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FPS = 30

# YOLO
YOLO_MODEL = "yolo11n.pt"
YOLO_CONFIDENCE = 0.5


# ══════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════

class RobotState:
    """State of robot at a sample point"""
    def __init__(self):
        self.timestamp = 0.0
        self.position = [0.0, 0.0]
        self.velocity = [INITIAL_VELOCITY, 0.0]
        self.humans = []
        self.sfm_force = [0.0, 0.0]
        self.next_velocity = [0.0, 0.0]
        self.displacement = [0.0, 0.0]  # X+ = right, Y+ = forward


class HumanDetection:
    """Detected human"""
    def __init__(self, id, position, distance):
        self.id = id
        self.position = position
        self.distance = distance
        self.zone = self._classify_zone(distance)
    
    def _classify_zone(self, dist):
        if dist < R_INTIMATE:
            return "INTIMATE"
        elif dist < R_PERSONAL:
            return "PERSONAL"
        elif dist < R_SOCIAL:
            return "SOCIAL"
        else:
            return "PUBLIC"


# ══════════════════════════════════════════════════════════════════
# Main Tester Class
# ══════════════════════════════════════════════════════════════════

class ManualSamplingTester:
    def __init__(self):
        print("="*70)
        print("Tester102 - Manual Movement Sampling Tester v2.0")
        print("="*70)
        
        self.samples = []
        self.sample_count = 0
        self.start_time = time.time()
        
        # Robot state (internal coordinates: x=forward, y=left)
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_vx = INITIAL_VELOCITY
        self.robot_vy = 0.0
        
        # Goal
        self.goal_x = 5.0
        self.goal_y = 0.0
        
        # Human tracking
        self.next_human_id = 1
        self.tracked_humans = {}
        
        # Initialize camera
        print("\n[1/3] Initializing RealSense camera...")
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.config.enable_stream(rs.stream.depth, CAM_WIDTH, CAM_HEIGHT, rs.format.z16, CAM_FPS)
        self.config.enable_stream(rs.stream.color, CAM_WIDTH, CAM_HEIGHT, rs.format.bgr8, CAM_FPS)
        
        self.profile = self.pipeline.start(self.config)
        self.align = rs.align(rs.stream.color)
        
        color_stream = self.profile.get_stream(rs.stream.color)
        self.intrinsics = color_stream.as_video_stream_profile().get_intrinsics()
        print(f"   ✓ Camera ready: {CAM_WIDTH}x{CAM_HEIGHT} @ {CAM_FPS} FPS")
        
        # Initialize YOLO
        print("\n[2/3] Loading YOLO model...")
        self.model = YOLO(YOLO_MODEL)
        print(f"   ✓ YOLO loaded: {YOLO_MODEL}")
        
        self.running = True
        
        print("\n[3/3] System ready!")
        print("\n" + "="*70)
        print("CONTROLS:")
        print("  SPACE - Take sample")
        print("  Q     - Quit and show graph")
        print("  R     - Reset")
        print("  S     - Save CSV")
        print("="*70)
        print("\n▶ Press SPACE to take first sample\n")
    
    def pixel_to_camera_frame(self, cx, cy, depth_m):
        """Convert pixel + depth to camera coordinates"""
        x = (cx - self.intrinsics.ppx) / self.intrinsics.fx * depth_m
        y = (cy - self.intrinsics.ppy) / self.intrinsics.fy * depth_m
        z = depth_m
        return x, y, z
    
    def camera_to_robot_frame(self, cam_x, cam_y, cam_z):
        """Transform camera to robot frame"""
        robot_x = cam_z      # forward
        robot_y = -cam_x     # left
        robot_z = -cam_y     # up
        return robot_x, robot_y, robot_z
    
    def match_detection_to_track(self, cx, cy):
        """Simple tracking"""
        min_dist = 50
        matched_id = None
        current_time = time.time()
        
        to_remove = [hid for hid, (_, _, t) in self.tracked_humans.items() 
                     if current_time - t > 2.0]
        for hid in to_remove:
            del self.tracked_humans[hid]
        
        for hid, (tx, ty, _) in self.tracked_humans.items():
            dist = np.hypot(cx - tx, cy - ty)
            if dist < min_dist:
                min_dist = dist
                matched_id = hid
        
        if matched_id is None:
            matched_id = self.next_human_id
            self.next_human_id += 1
        
        self.tracked_humans[matched_id] = (cx, cy, current_time)
        return matched_id
    
    def detect_humans(self, color_frame, depth_frame):
        """Detect humans using YOLO + RealSense"""
        frame = np.asanyarray(color_frame.get_data())
        results = self.model(frame, classes=[0], verbose=False)
        
        boxes = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()
        
        humans = []
        for box, conf in zip(boxes, confidences):
            if conf < YOLO_CONFIDENCE:
                continue
            
            x1, y1, x2, y2 = map(int, box[:4])
            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)
            
            distance = depth_frame.get_distance(cx, cy)
            if distance <= 0.1 or distance > 10.0:
                continue
            
            human_id = self.match_detection_to_track(cx, cy)
            
            cam_x, cam_y, cam_z = self.pixel_to_camera_frame(cx, cy, distance)
            robot_x, robot_y, robot_z = self.camera_to_robot_frame(cam_x, cam_y, cam_z)
            
            human = HumanDetection(human_id, [robot_x, robot_y], distance)
            humans.append(human)
        
        return humans, results[0]
    
    def calculate_sfm_forces(self, robot_pos, robot_vel, humans, goal_pos):
        """Calculate Social Force Model forces"""
        rx, ry = robot_pos
        vx, vy = robot_vel
        gx, gy = goal_pos
        
        # Goal force
        dx = gx - rx
        dy = gy - ry
        dist_to_goal = math.hypot(dx, dy)
        
        if dist_to_goal > 1e-6:
            ex = dx / dist_to_goal
            ey = dy / dist_to_goal
            desired_vx = SFM_V0 * ex
            desired_vy = SFM_V0 * ey
        else:
            desired_vx = 0.0
            desired_vy = 0.0
        
        fx_goal = SFM_MASS / SFM_TAU * (desired_vx - vx)
        fy_goal = SFM_MASS / SFM_TAU * (desired_vy - vy)
        
        # Human repulsion
        fx_rep = 0.0
        fy_rep = 0.0
        
        for human in humans:
            hx, hy = human.position
            dx = rx - hx
            dy = ry - hy
            dist = math.hypot(dx, dy)
            
            if dist < 1e-6:
                fx_rep += 100.0
                fy_rep += 0.0
            else:
                mag = SFM_A * math.exp(-dist / SFM_B)
                fx_rep += mag * dx / dist
                fy_rep += mag * dy / dist
        
        fx_total = fx_goal + fx_rep
        fy_total = fy_goal + fy_rep
        
        return fx_total, fy_total, fx_goal, fy_goal, fx_rep, fy_rep
    
    def calculate_next_velocity(self, fx, fy, vx, vy):
        """Calculate next velocity"""
        ax = fx / SFM_MASS
        ay = fy / SFM_MASS
        
        vx_new = vx + ax * SAMPLE_INTERVAL
        vy_new = vy + ay * SAMPLE_INTERVAL
        
        speed = math.hypot(vx_new, vy_new)
        if speed > 0.6:
            vx_new = vx_new / speed * 0.6
            vy_new = vy_new / speed * 0.6
        
        return vx_new, vy_new
    
    def calculate_displacement(self, vx, vy):
        """
        Calculate displacement for 0.25s
        Output format: X+ = right, Y+ = forward
        Internal: vx = forward, vy = left
        Conversion: X = -vy * dt (right), Y = vx * dt (forward)
        """
        dx_right = -vy * SAMPLE_INTERVAL
        dy_forward = vx * SAMPLE_INTERVAL
        return dx_right, dy_forward
    
    def create_visualization(self, frame, depth_frame, humans, yolo_result):
        """Create enhanced visualization like reference image"""
        display = yolo_result.plot()
        h, w = display.shape[:2]
        
        # Center point
        cx, cy = w // 2, int(h * 0.65)
        
        # Scale for zones
        if len(humans) > 0:
            avg_dist = np.mean([h.distance for h in humans])
            scale = 80 / max(avg_dist, 1.0)
        else:
            scale = 80
        
        # Draw zones
        cv2.circle(display, (cx, cy), int(R_SOCIAL * scale), (0, 255, 255), 2)
        cv2.circle(display, (cx, cy), int(R_PERSONAL * scale), (0, 165, 255), 3)
        cv2.circle(display, (cx, cy), int(R_INTIMATE * scale), (0, 0, 255), 3)
        
        # Robot center
        cv2.circle(display, (cx, cy), 8, (255, 0, 255), -1)
        cv2.circle(display, (cx, cy), 12, (255, 0, 255), 2)
        
        # Command arrow
        current_speed = math.hypot(self.robot_vx, self.robot_vy)
        if current_speed > 0.01:
            arrow_scale = 100
            arrow_end = (
                int(cx + self.robot_vx * arrow_scale),
                int(cy - self.robot_vy * arrow_scale)
            )
            cv2.arrowedLine(display, (cx, cy), arrow_end, (0, 255, 0), 6, tipLength=0.3)
            cv2.putText(display, "COMMAND", (arrow_end[0] - 35, arrow_end[1] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Human labels
        for human in humans:
            zone_color = (0, 255, 255) if human.zone == "SOCIAL" else \
                        (0, 165, 255) if human.zone == "PERSONAL" else (0, 0, 255)
            text = f"{human.distance:.2f}m | {human.zone}"
            # Find approximate position on screen (simplified)
            cv2.putText(display, text, (50, 100 + human.id * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)
        
        # Bottom info panel
        panel_h = 220
        panel = np.zeros((panel_h, w, 3), dtype=np.uint8)
        
        cv2.putText(panel, "CAMERA-BASED AVOIDANCE COMMAND TESTER", (10, 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        
        current_time = time.time() - self.start_time
        cv2.putText(panel, f"Time: {current_time:.2f}s", (10, 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        goal_angle = math.degrees(math.atan2(self.goal_y - self.robot_y, 
                                              self.goal_x - self.robot_x))
        cv2.putText(panel, f"Target Direction: {goal_angle:.1f}? (Forward/Goal)", (10, 78),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        if current_speed > 0.01:
            current_angle = math.degrees(math.atan2(self.robot_vy, self.robot_vx))
        else:
            current_angle = 0.0
        cv2.putText(panel, f"Avoidance Direction: {current_angle:.1f}? (avoiding humans)", (10, 101),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
        
        # Avoidance force (if sampling was done)
        cv2.putText(panel, f"Avoidance Force: ?.?? N (press SPACE)", (10, 124),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        speed_percent = int((current_speed / INITIAL_VELOCITY) * 100) if INITIAL_VELOCITY > 0 else 0
        cv2.putText(panel, f"Current Speed: {current_speed:.3f} m/s ({speed_percent}%)", (10, 151),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        
        # Closest human zone
        closest_dist = 999.0
        closest_zone = "PUBLIC"
        if len(humans) > 0:
            closest_dist = min([h.distance for h in humans])
            closest_zone = min(humans, key=lambda h: h.distance).zone
        
        zone_color = (0, 255, 255) if closest_zone == "SOCIAL" else \
                     (0, 165, 255) if closest_zone == "PERSONAL" else (0, 0, 255)
        cv2.putText(panel, f"Proxemic Zone: {closest_zone} (closest: {closest_dist:.2f}m)", (10, 178),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, zone_color, 2)
        
        # Movement command with displacement
        dx_disp, dy_disp = self.calculate_displacement(self.robot_vx, self.robot_vy)
        cv2.putText(panel, f"Movement Command (0.25s): ??? (press SPACE)", (10, 201),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.putText(panel, f"  {dx_disp:+.3f}X  {dy_disp:+.3f}Y  (X+=right, Y+=forward)", (10, 215),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Top bar
        top_bar = np.zeros((50, w, 3), dtype=np.uint8)
        cv2.putText(top_bar, f"Samples: {self.sample_count}", (10, 32),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.putText(top_bar, "SPACE: Sample | Q: Quit | R: Reset | S: Save", (280, 32),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Combine
        display[:50, :] = top_bar
        display[-panel_h:, :] = panel
        
        return display
    
    def take_sample(self):
        """Take a data sample"""
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
            aligned_frames = self.align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                print("⚠ Failed to get frames")
                return None
            
            # Detect humans
            humans, yolo_result = self.detect_humans(color_frame, depth_frame)
            
            # Calculate forces
            fx, fy, fx_goal, fy_goal, fx_rep, fy_rep = self.calculate_sfm_forces(
                [self.robot_x, self.robot_y],
                [self.robot_vx, self.robot_vy],
                humans,
                [self.goal_x, self.goal_y]
            )
            
            # Calculate next velocity
            vx_next, vy_next = self.calculate_next_velocity(fx, fy, self.robot_vx, self.robot_vy)
            
            # Calculate displacement
            dx_disp, dy_disp = self.calculate_displacement(vx_next, vy_next)
            
            # Create sample
            sample = RobotState()
            sample.timestamp = time.time() - self.start_time
            sample.position = [self.robot_x, self.robot_y]
            sample.velocity = [self.robot_vx, self.robot_vy]
            sample.humans = humans
            sample.sfm_force = [fx, fy]
            sample.next_velocity = [vx_next, vy_next]
            sample.displacement = [dx_disp, dy_disp]
            
            self.samples.append(sample)
            self.sample_count += 1
            
            # Update robot state
            self.robot_vx = vx_next
            self.robot_vy = vy_next
            self.robot_x += vx_next * SAMPLE_INTERVAL
            self.robot_y += vy_next * SAMPLE_INTERVAL
            
            # Display info
            print(f"\n{'='*70}")
            print(f"Sample #{self.sample_count} at t={sample.timestamp:.2f}s")
            print(f"{'='*70}")
            print(f"Position: ({self.robot_x:.3f}, {self.robot_y:.3f}) m")
            print(f"Velocity: ({self.robot_vx:.3f}, {self.robot_vy:.3f}) m/s")
            print(f"Humans detected: {len(humans)}")
            
            if len(humans) > 0:
                print(f"\nHumans:")
                for h in humans:
                    print(f"  ID{h.id}: ({h.position[0]:.2f}, {h.position[1]:.2f})m, "
                          f"dist={h.distance:.2f}m, zone={h.zone}")
            
            print(f"\nSFM Forces:")
            print(f"  Goal: ({fx_goal:.2f}, {fy_goal:.2f}) N")
            print(f"  Repulsive: ({fx_rep:.2f}, {fy_rep:.2f}) N")
            print(f"  Total: ({fx:.2f}, {fy:.2f}) N")
            
            print(f"\nNext velocity: ({vx_next:.3f}, {vy_next:.3f}) m/s")
            print(f"Displacement (0.25s): {dx_disp:+.3f}X {dy_disp:+.3f}Y")
            print(f"{'='*70}")
            print("\n▶ Move robot, then press SPACE for next sample")
            
            # Enhanced visualization
            display = self.create_visualization_after_sample(
                yolo_result, humans, vx_next, vy_next, fx, fy, sample)
            cv2.imshow("Tester102", display)
            
            return sample
            
        except Exception as e:
            print(f"⚠ Error: {e}")
            return None
    
    def create_visualization_after_sample(self, yolo_result, humans, vx_next, vy_next, fx, fy, sample):
        """Create visualization after sampling"""
        display = yolo_result.plot()
        h, w = display.shape[:2]
        
        cx, cy = w // 2, int(h * 0.65)
        
        if len(humans) > 0:
            avg_dist = np.mean([h.distance for h in humans])
            scale = 80 / max(avg_dist, 1.0)
        else:
            scale = 80
        
        cv2.circle(display, (cx, cy), int(R_SOCIAL * scale), (0, 255, 255), 2)
        cv2.circle(display, (cx, cy), int(R_PERSONAL * scale), (0, 165, 255), 3)
        cv2.circle(display, (cx, cy), int(R_INTIMATE * scale), (0, 0, 255), 3)
        cv2.circle(display, (cx, cy), 8, (255, 0, 255), -1)
        
        arrow_scale = 150
        arrow_end = (
            int(cx + vx_next * arrow_scale),
            int(cy - vy_next * arrow_scale)
        )
        cv2.arrowedLine(display, (cx, cy), arrow_end, (0, 255, 0), 6, tipLength=0.3)
        
        speed_next = math.hypot(vx_next, vy_next)
        angle_next = math.degrees(math.atan2(vy_next, vx_next)) if speed_next > 0.01 else 0.0
        
        if -22.5 <= angle_next < 22.5:
            dir_label = "FWD"
        elif 22.5 <= angle_next < 67.5:
            dir_label = "FWD-LEFT"
        elif -67.5 <= angle_next < -22.5:
            dir_label = "FWD-RIGHT"
        else:
            dir_label = "TURN"
        
        closest_dist = min([h.distance for h in humans]) if len(humans) > 0 else 999.0
        closest_zone = min(humans, key=lambda h: h.distance).zone if len(humans) > 0 else "PUBLIC"
        
        panel_h = 220
        panel = np.zeros((panel_h, w, 3), dtype=np.uint8)
        
        cv2.putText(panel, "CAMERA-BASED AVOIDANCE COMMAND TESTER", (10, 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(panel, f"Time: {sample.timestamp:.2f}s", (10, 55),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        goal_angle = math.degrees(math.atan2(self.goal_y - self.robot_y, 
                                              self.goal_x - self.robot_x))
        cv2.putText(panel, f"Target Direction: {goal_angle:.1f}? (Forward/Goal)", (10, 78),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(panel, f"Avoidance Direction: {angle_next:.1f}? (avoiding humans)", (10, 101),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
        
        force_mag = math.hypot(fx, fy)
        cv2.putText(panel, f"Avoidance Force: {force_mag:.2f} N", (10, 124),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        speed_percent = int((speed_next / INITIAL_VELOCITY) * 100) if INITIAL_VELOCITY > 0 else 0
        cv2.putText(panel, f"Current Speed: {speed_next:.3f} m/s ({speed_percent}%)", (10, 151),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        
        zone_color = (0, 255, 255) if closest_zone == "SOCIAL" else \
                     (0, 165, 255) if closest_zone == "PERSONAL" else (0, 0, 255)
        cv2.putText(panel, f"Proxemic Zone: {closest_zone} (closest: {closest_dist:.2f}m)", (10, 178),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.55, zone_color, 2)
        
        cv2.putText(panel, f"Movement Command (0.25s): {dir_label}", (10, 201),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        
        dx_disp, dy_disp = sample.displacement
        cv2.putText(panel, f"  {dx_disp:+.3f}X  {dy_disp:+.3f}Y  (X+=right, Y+=forward)", (10, 215),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        top_bar = np.zeros((50, w, 3), dtype=np.uint8)
        cv2.putText(top_bar, f"Sample #{self.sample_count}", (10, 32),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        
        display[:50, :] = top_bar
        display[-panel_h:, :] = panel
        
        return display
    
    def save_to_csv(self):
        """Save trajectory data"""
        if len(self.samples) == 0:
            print("⚠ No data")
            return
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Tester102/trajectory_{timestamp_str}.csv"
        
        data = []
        for i, s in enumerate(self.samples):
            row = {
                'sample_id': i + 1,
                'timestamp': s.timestamp,
                'robot_x': s.position[0],
                'robot_y': s.position[1],
                'robot_vx': s.velocity[0],
                'robot_vy': s.velocity[1],
                'sfm_fx': s.sfm_force[0],
                'sfm_fy': s.sfm_force[1],
                'next_vx': s.next_velocity[0],
                'next_vy': s.next_velocity[1],
                'disp_x_right': s.displacement[0],
                'disp_y_forward': s.displacement[1],
                'num_humans': len(s.humans)
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        print(f"\n✓ Saved: {filename}")
    
    def plot_trajectory(self):
        """Plot trajectory graph"""
        if len(self.samples) < 2:
            print("⚠ Need at least 2 samples")
            return
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Plot 1: Trajectory
        robot_x = [s.position[0] for s in self.samples]
        robot_y = [s.position[1] for s in self.samples]
        
        ax1.plot(robot_x, robot_y, 'b-', linewidth=2, label='Robot path')
        ax1.plot(robot_x, robot_y, 'bo', markersize=8, alpha=0.6)
        ax1.plot(robot_x[0], robot_y[0], 'go', markersize=15, label='Start')
        ax1.plot(robot_x[-1], robot_y[-1], 'ro', markersize=15, label='End')
        ax1.plot(self.goal_x, self.goal_y, 'g*', markersize=20, label='Goal')
        
        # Human paths
        all_humans = {}
        for sample in self.samples:
            for h in sample.humans:
                if h.id not in all_humans:
                    all_humans[h.id] = []
                hx_world = sample.position[0] + h.position[0]
                hy_world = sample.position[1] + h.position[1]
                all_humans[h.id].append((hx_world, hy_world))
        
        colors = plt.cm.rainbow(np.linspace(0, 1, len(all_humans)))
        for (hid, positions), color in zip(all_humans.items(), colors):
            hx = [p[0] for p in positions]
            hy = [p[1] for p in positions]
            ax1.plot(hx, hy, 'x-', color=color, alpha=0.5, markersize=6, label=f'Human {hid}')
        
        last_pos = self.samples[-1].position
        circle_intimate = Circle(last_pos, R_INTIMATE, fill=False, edgecolor='r', linestyle='--', linewidth=2)
        circle_personal = Circle(last_pos, R_PERSONAL, fill=False, edgecolor='orange', linestyle='--', linewidth=1.5)
        circle_social = Circle(last_pos, R_SOCIAL, fill=False, edgecolor='yellow', linestyle='--', linewidth=1)
        ax1.add_patch(circle_intimate)
        ax1.add_patch(circle_personal)
        ax1.add_patch(circle_social)
        
        ax1.set_xlabel('X (m)')
        ax1.set_ylabel('Y (m)')
        ax1.set_title('Trajectory Map')
        ax1.set_aspect('equal')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)
        
        # Plot 2: Time series
        times = [s.timestamp for s in self.samples]
        velocities = [math.hypot(s.velocity[0], s.velocity[1]) for s in self.samples]
        forces = [math.hypot(s.sfm_force[0], s.sfm_force[1]) for s in self.samples]
        num_humans = [len(s.humans) for s in self.samples]
        
        ax2_twin = ax2.twinx()
        
        line1 = ax2.plot(times, velocities, 'b-', linewidth=2, label='Velocity (m/s)')
        line2 = ax2.plot(times, forces, 'r-', linewidth=2, label='Force (N)')
        line3 = ax2_twin.plot(times, num_humans, 'g--', linewidth=2, label='Humans')
        
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Velocity/Force', color='b')
        ax2_twin.set_ylabel('Humans', color='g')
        ax2.set_title('Time Series')
        ax2.grid(True, alpha=0.3)
        
        lines = line1 + line2 + line3
        labels = [l.get_label() for l in lines]
        ax2.legend(lines, labels)
        
        plt.tight_layout()
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        figname = f"Tester102/trajectory_plot_{timestamp_str}.png"
        plt.savefig(figname, dpi=150, bbox_inches='tight')
        print(f"✓ Saved: {figname}")
        
        plt.show()
    
    def run(self):
        """Main loop"""
        print("\n▶ Starting...")
        
        while self.running:
            try:
                frames = self.pipeline.wait_for_frames(timeout_ms=100)
                aligned_frames = self.align.process(frames)
                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                
                if color_frame and depth_frame:
                    humans, yolo_result = self.detect_humans(color_frame, depth_frame)
                    display = self.create_visualization(
                        np.asanyarray(color_frame.get_data()), depth_frame, humans, yolo_result)
                    cv2.imshow("Tester102", display)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):
                    self.take_sample()
                elif key == ord('q'):
                    self.running = False
                elif key == ord('r'):
                    self.samples = []
                    self.sample_count = 0
                    self.robot_x = 0.0
                    self.robot_y = 0.0
                    self.robot_vx = INITIAL_VELOCITY
                    self.robot_vy = 0.0
                    self.start_time = time.time()
                    print("\n✓ Reset")
                elif key == ord('s'):
                    self.save_to_csv()
            
            except Exception as e:
                print(f"⚠ Error: {e}")
                time.sleep(0.1)
        
        self.pipeline.stop()
        cv2.destroyAllWindows()
        
        if len(self.samples) > 0:
            print(f"\n{'='*70}")
            print(f"RESULTS: {self.sample_count} samples, {self.samples[-1].timestamp:.2f}s")
            print(f"Final: ({self.robot_x:.3f}, {self.robot_y:.3f}) m")
            print(f"{'='*70}")
            self.plot_trajectory()
        
        print("\n✓ Done!")


def main():
    try:
        tester = ManualSamplingTester()
        tester.run()
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted")
    except Exception as e:
        print(f"\n⚠ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
