#!/usr/bin/env python3
"""
Camera-Based Avoidance Command Tester with Manual Sampling
===========================================================
Program untuk menguji perintah menghindar robot dengan kamera yang digeser manual.
User menggeser kamera secara fisik manual dengan kecepatan ~1 m/s menuju target.
Robot mendeteksi manusia dan memberikan PERINTAH ARAH MENGHINDAR secara manual sampling.

Concept:
  - User menggeser kamera secara FISIK (manual, bukan keyboard)
  - User tekan SPACE untuk sampling setiap 1/4 detik (250ms)
  - Robot mendeteksi manusia dengan RealSense + YOLO
  - Robot menghitung arah menghindar otomatis (SFM-based)
  - Output: PERINTAH GERAK untuk 0.25 detik (direction + X/Y axis displacement)
  - Data tersimpan untuk analisis trajectory
  - Tujuan: validasi algoritma avoidance dengan sampling manual

Features:
  - Manual sampling interval 0.25 detik (SPACE key)
  - Automatic avoidance direction calculation
  - RealSense depth camera + YOLO detection
  - Proxemic zone speed adjustment
  - Displacement commands (X/Y for 0.25s)
  - SFM repulsive force for avoidance
  - CSV export dan trajectory plotting

Usage:
    python3 manual_camera_movement_tester.py
    
    Kemudian GESER KAMERA SECARA FISIK (manual) menuju target.
    Tekan SPACE untuk sampling setiap 1/4 detik.

Controls:
    [SPACE] - Take sample (manual sampling setiap 1/4 detik)
    [R] - Reset statistics
    [S] - Save data to CSV
    [Q] - Quit and show trajectory graph

Author: Brone Social Nav Team
Version: 3.0 - Manual Sampling Integration
Date: 2026-10-04
"""

import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import math
import time
import sys
import os
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for better compatibility
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
# ── Configuration Parameters ──────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

# Sampling interval
SAMPLE_INTERVAL = 0.25  # seconds (1/4 detik) - manual sampling

# Proxemic zones (meters)
R_INTIMATE = 0.45      # Emergency stop zone
R_PERSONAL = 1.20      # Slow down zone  
R_SOCIAL = 3.60        # Caution zone

# Speed parameters
BASE_SPEED = 1.0       # m/s - initial/target speed
SPEED_INTIMATE = 0.0   # m/s - stop in intimate zone
SPEED_PERSONAL = 0.3   # m/s - slow in personal zone
SPEED_SOCIAL = 0.6     # m/s - moderate in social zone
SPEED_PUBLIC = 1.0     # m/s - full speed in public zone

# Social Force Model parameters
SFM_A = 5.0            # N - repulsive force magnitude
SFM_B = 0.8            # m - repulsive force range
SFM_WEIGHT = 0.3       # Weight for avoidance vs goal direction
SFM_TAU = 0.5          # Time constant for goal force
SFM_MASS = 5.0         # Robot mass (kg)

# Default target direction (forward)
DEFAULT_TARGET = np.array([0.0, 1.0])  # Forward (Y+)

# Display settings
SHOW_ZONES = True
SHOW_FORCES = True
SHOW_TRAJECTORY = False  # Not applicable for manual camera movement
TRAIL_LENGTH = 50        # Number of position points to keep


# ══════════════════════════════════════════════════════════════════
# ── Data Classes ──────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

class SampleData:
    """Data structure for each manual sample"""
    def __init__(self):
        self.timestamp = 0.0
        self.position = [0.0, 0.0]  # Camera position (accumulated)
        self.velocity = [0.0, 0.0]  # Current velocity
        self.target_direction = [0.0, 1.0]  # Target direction (normalized)
        self.avoidance_direction = [0.0, 1.0]  # Avoidance direction (normalized)
        self.current_speed = 0.0
        self.target_speed = 0.0
        self.num_humans = 0
        self.closest_distance = float('inf')
        self.proxemic_zone = "PUBLIC"
        self.sfm_force = [0.0, 0.0]  # Total SFM force
        self.displacement = [0.0, 0.0]  # Displacement for 0.25s (X+right, Y+forward)


# ══════════════════════════════════════════════════════════════════
# ── Helper Functions ──────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

def get_proxemic_zone_and_speed(distance):
    """
    Determine proxemic zone and corresponding speed
    
    Returns:
        zone_name: str
        zone_color: tuple (B,G,R)
        target_speed: float (m/s)
    """
    if distance < R_INTIMATE:
        return "INTIMATE", (0, 0, 255), SPEED_INTIMATE  # Red
    elif distance < R_PERSONAL:
        return "PERSONAL", (0, 165, 255), SPEED_PERSONAL  # Orange
    elif distance < R_SOCIAL:
        return "SOCIAL", (0, 255, 255), SPEED_SOCIAL  # Yellow
    else:
        return "PUBLIC", (0, 255, 0), SPEED_PUBLIC  # Green


def calculate_speed_adjustment(detections):
    """
    Calculate speed based on closest human in proxemic zones
    
    Args:
        detections: list of detection dicts with 'distance' key
        
    Returns:
        adjusted_speed: float (m/s)
        zone_name: str
        closest_dist: float (m)
    """
    if len(detections) == 0:
        return SPEED_PUBLIC, "PUBLIC", float('inf')
    
    # Find closest human
    closest = min(detections, key=lambda d: d['distance'])
    distance = closest['distance']
    
    zone_name, _, speed = get_proxemic_zone_and_speed(distance)
    
    return speed, zone_name, distance


def sfm_repulsive_force(distance, direction_x, direction_y):
    """
    Calculate SFM repulsive force from human
    F_rep = A × exp(−d/B) × n̂
    
    Args:
        distance: distance to human (m)
        direction_x, direction_y: unit vector FROM human TO robot
    
    Returns:
        fx, fy: force components (N)
    """
    if distance < 0.01:
        magnitude = 100.0  # Very close - maximum repulsion
    else:
        magnitude = SFM_A * math.exp(-distance / SFM_B)
    
    fx = magnitude * direction_x
    fy = magnitude * direction_y
    
    return fx, fy


def calculate_avoidance_direction(detections, target_direction, camera_center_x, camera_center_y, scale):
    """
    Calculate avoidance direction combining target goal and obstacle avoidance
    
    Args:
        detections: list of human detections with distance and position
        target_direction: desired direction vector (from user, default forward)
        camera_center_x, camera_center_y: camera center in pixels
        scale: pixels per meter conversion
        
    Returns:
        final_direction: resultant direction (normalized)
        total_force: total avoidance force (fx, fy)
        has_humans: whether humans are detected
    """
    if len(detections) == 0:
        # No humans - go straight to target
        return target_direction, (0.0, 0.0), False
    
    # Calculate total repulsive force from all humans
    total_fx = 0.0
    total_fy = 0.0
    
    for det in detections:
        cx, cy = det['center']
        distance = det['distance']
        
        # Direction from robot (camera center) to human
        dx_pixel = cx - camera_center_x
        dy_pixel = cy - camera_center_y
        
        # Convert to meters
        dx_meter = dx_pixel / scale
        dy_meter = -dy_pixel / scale  # Y inverted in screen coords
        
        dist_2d = math.hypot(dx_meter, dy_meter)
        
        # Unit vector from human to robot (repulsive direction)
        if dist_2d > 0.01:
            dir_x = -dx_meter / dist_2d  # Away from human
            dir_y = -dy_meter / dist_2d
        else:
            dir_x = 0.0
            dir_y = 1.0  # Push forward if too close
        
        # Calculate repulsive force
        fx, fy = sfm_repulsive_force(distance, dir_x, dir_y)
        
        total_fx += fx
        total_fy += fy
    
    # Convert force to avoidance direction (simplified)
    force_magnitude = math.hypot(total_fx, total_fy)
    
    if force_magnitude > 0.01:
        avoidance_dir_x = total_fx / force_magnitude
        avoidance_dir_y = total_fy / force_magnitude
    else:
        avoidance_dir_x = 0.0
        avoidance_dir_y = 0.0
    
    # Combine target direction with avoidance
    # final = (1 - weight) * target + weight * avoidance
    combined_x = (1.0 - SFM_WEIGHT) * target_direction[0] + SFM_WEIGHT * avoidance_dir_x
    combined_y = (1.0 - SFM_WEIGHT) * target_direction[1] + SFM_WEIGHT * avoidance_dir_y
    
    # Normalize
    combined_magnitude = math.hypot(combined_x, combined_y)
    if combined_magnitude > 0.01:
        final_direction = np.array([combined_x / combined_magnitude, 
                                   combined_y / combined_magnitude])
    else:
        final_direction = target_direction
    
    return final_direction, (total_fx, total_fy), True


def get_movement_command(vx, vy, speed):
    """
    Convert velocity to movement command with axis info
    
    Args:
        vx, vy: velocity components (m/s)
        speed: magnitude (m/s)
        
    Returns:
        command_str: formatted command string
        arrow: direction arrow symbol
        axis_info: X, Y components
    """
    if speed < 0.01:
        return "STOP", "⊙", (0.0, 0.0)
    
    # Determine primary direction
    angle = math.degrees(math.atan2(vy, vx))
    
    if -22.5 <= angle < 22.5:
        direction = "RIGHT"
        arrow = "→"
    elif 22.5 <= angle < 67.5:
        direction = "FWD-RIGHT"
        arrow = "↗"
    elif 67.5 <= angle < 112.5:
        direction = "FORWARD"
        arrow = "↑"
    elif 112.5 <= angle < 157.5:
        direction = "FWD-LEFT"
        arrow = "↖"
    elif angle >= 157.5 or angle < -157.5:
        direction = "LEFT"
        arrow = "←"
    elif -157.5 <= angle < -112.5:
        direction = "BACK-LEFT"
        arrow = "↙"
    elif -112.5 <= angle < -67.5:
        direction = "BACKWARD"
        arrow = "↓"
    else:
        direction = "BACK-RIGHT"
        arrow = "↘"
    
    command = f"{arrow} {direction}"
    axis_info = (vx, vy)
    
    return command, arrow, axis_info


def calculate_displacement(vx, vy, dt=SAMPLE_INTERVAL):
    """
    Calculate displacement for sampling interval
    Output format: X+ = right, Y+ = forward
    Internal: vx = X-axis (right), vy = Y-axis (forward)
    
    Args:
        vx, vy: velocity components (m/s)
        dt: time interval (seconds)
    
    Returns:
        dx_right, dy_forward: displacement in meters
    """
    dx_right = vx * dt
    dy_forward = vy * dt
    return dx_right, dy_forward


def save_samples_to_csv(samples, filename=None):
    """Save sample data to CSV file"""
    if len(samples) == 0:
        print("⚠ No samples to save")
        return None
    
    if filename is None:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use current directory instead of hardcoded folder
        filename = f"trajectory_{timestamp_str}.csv"
    
    data = []
    for i, sample in enumerate(samples):
        row = {
            'sample_id': i + 1,
            'timestamp': sample.timestamp,
            'position_x': sample.position[0],
            'position_y': sample.position[1],
            'velocity_x': sample.velocity[0],
            'velocity_y': sample.velocity[1],
            'target_dir_x': sample.target_direction[0],
            'target_dir_y': sample.target_direction[1],
            'avoid_dir_x': sample.avoidance_direction[0],
            'avoid_dir_y': sample.avoidance_direction[1],
            'current_speed': sample.current_speed,
            'target_speed': sample.target_speed,
            'num_humans': sample.num_humans,
            'closest_distance': sample.closest_distance,
            'proxemic_zone': sample.proxemic_zone,
            'sfm_force_x': sample.sfm_force[0],
            'sfm_force_y': sample.sfm_force[1],
            'displacement_x': sample.displacement[0],
            'displacement_y': sample.displacement[1]
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"\n✓ Saved: {filename}")
    return filename


def plot_trajectory(samples):
    """Plot trajectory and time-series data"""
    if len(samples) < 2:
        print("⚠ Need at least 2 samples for plotting")
        return
    
    print("\n📈 Creating trajectory plot...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Extract data
    positions_x = [s.position[0] for s in samples]
    positions_y = [s.position[1] for s in samples]
    times = [s.timestamp for s in samples]
    speeds = [s.current_speed for s in samples]
    forces = [math.hypot(s.sfm_force[0], s.sfm_force[1]) for s in samples]
    num_humans = [s.num_humans for s in samples]
    
    # Plot 1: Trajectory map
    ax1.plot(positions_x, positions_y, 'b-', linewidth=2, label='Camera path')
    ax1.plot(positions_x, positions_y, 'bo', markersize=8, alpha=0.6)
    ax1.plot(positions_x[0], positions_y[0], 'go', markersize=15, label='Start')
    ax1.plot(positions_x[-1], positions_y[-1], 'ro', markersize=15, label='End')
    
    # Draw proxemic zones at last position
    last_pos = samples[-1].position
    circle_intimate = Circle(last_pos, R_INTIMATE, fill=False, edgecolor='r', 
                            linestyle='--', linewidth=2, label='Intimate')
    circle_personal = Circle(last_pos, R_PERSONAL, fill=False, edgecolor='orange', 
                            linestyle='--', linewidth=1.5, label='Personal')
    circle_social = Circle(last_pos, R_SOCIAL, fill=False, edgecolor='yellow', 
                          linestyle='--', linewidth=1, label='Social')
    ax1.add_patch(circle_intimate)
    ax1.add_patch(circle_personal)
    ax1.add_patch(circle_social)
    
    ax1.set_xlabel('X (m) - Right →', fontsize=12)
    ax1.set_ylabel('Y (m) - Forward ↑', fontsize=12)
    ax1.set_title('Camera Trajectory Map', fontsize=14, fontweight='bold')
    ax1.set_aspect('equal')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    
    # Plot 2: Time series
    ax2_twin = ax2.twinx()
    
    line1 = ax2.plot(times, speeds, 'b-', linewidth=2, label='Speed (m/s)')
    line2 = ax2.plot(times, forces, 'r-', linewidth=2, label='SFM Force (N)')
    line3 = ax2_twin.plot(times, num_humans, 'g--', linewidth=2, marker='o', 
                         markersize=4, label='Humans detected')
    
    ax2.set_xlabel('Time (s)', fontsize=12)
    ax2.set_ylabel('Speed / Force', color='b', fontsize=12)
    ax2_twin.set_ylabel('Number of Humans', color='g', fontsize=12)
    ax2.set_title('Time Series Data', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Combine legends
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, fontsize=10)
    
    plt.tight_layout()
    
    # Save figure
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    figname = f"trajectory_plot_{timestamp_str}.png"
    
    try:
        plt.savefig(figname, dpi=150, bbox_inches='tight')
        print(f"✓ Plot saved: {figname}")
    except Exception as e:
        print(f"⚠ Could not save plot: {e}")
    
    # Show plot
    print("\n📊 Displaying trajectory plot...")
    print("   Close the plot window to exit.")
    try:
        plt.show(block=True)
    except Exception as e:
        print(f"⚠ Could not display plot: {e}")
        print("   Plot file saved, you can open it manually.")


def draw_info_panel(frame, target_dir, avoidance_dir, current_speed, 
                    target_speed, zone_name, closest_dist, detections,
                    vx, vy, elapsed_time, total_force, sample_count):
    """Draw comprehensive information panel with sampling info"""
    h, w = frame.shape[:2]
    panel_height = 300
    panel = np.zeros((panel_height, w, 3), dtype=np.uint8)
    
    y_offset = 25
    line_height = 25
    
    # Title
    cv2.putText(panel, "CAMERA-BASED AVOIDANCE COMMAND TESTER (Manual Sampling)", (10, y_offset),
                cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 2)
    y_offset += line_height + 5
    
    # Elapsed time and sample count
    cv2.putText(panel, f"Time: {elapsed_time:.1f}s | Samples: {sample_count}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    y_offset += line_height
    
    # Target direction (default: forward)
    target_angle = math.degrees(math.atan2(target_dir[1], target_dir[0]))
    cv2.putText(panel, f"Target Direction: {target_angle:.1f}° (Forward/Goal)", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 200, 255), 1)
    y_offset += line_height
    
    # Avoidance direction (if different)
    avoid_angle = math.degrees(math.atan2(avoidance_dir[1], avoidance_dir[0]))
    angle_diff = abs(avoid_angle - target_angle)
    if angle_diff > 5:  # Significant deviation
        cv2.putText(panel, f"Avoidance Direction: {avoid_angle:.1f}° (avoiding humans)", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
    else:
        cv2.putText(panel, f"Avoidance Direction: {avoid_angle:.1f}° (no avoidance needed)", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    y_offset += line_height
    
    # Avoidance force
    force_mag = math.hypot(total_force[0], total_force[1])
    cv2.putText(panel, f"Avoidance Force: {force_mag:.2f} N", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    y_offset += line_height
    
    # Speed info
    speed_ratio = (current_speed / BASE_SPEED) * 100 if BASE_SPEED > 0 else 0
    speed_color = (0, 255, 0) if current_speed > 0.5 else (0, 165, 255) if current_speed > 0.1 else (0, 0, 255)
    cv2.putText(panel, f"Current Speed: {current_speed:.3f} m/s ({speed_ratio:.0f}%)", 
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, speed_color, 2)
    y_offset += line_height
    
    # Proxemic zone status
    zone_color_map = {
        "INTIMATE": (0, 0, 255),
        "PERSONAL": (0, 165, 255),
        "SOCIAL": (0, 255, 255),
        "PUBLIC": (0, 255, 0)
    }
    zone_color = zone_color_map.get(zone_name, (255, 255, 255))
    
    if closest_dist < float('inf'):
        cv2.putText(panel, f"Proxemic Zone: {zone_name} (closest: {closest_dist:.2f}m)", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)
    else:
        cv2.putText(panel, f"Proxemic Zone: {zone_name} (no humans)", 
                    (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 1)
    y_offset += line_height
    
    # Movement command (0.25s output)
    command, arrow, (ax, ay) = get_movement_command(vx, vy, current_speed)
    cv2.putText(panel, f"Movement Command (0.25s): {command}", 
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_offset += line_height
    
    # Displacement for 0.25s
    dx_disp, dy_disp = calculate_displacement(vx, vy)
    cv2.putText(panel, f"  Displacement: {dx_disp:+.3f}X  {dy_disp:+.3f}Y  (X+=right, Y+=forward)", 
                (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    y_offset += line_height + 5
    
    # Detected humans
    cv2.line(panel, (10, y_offset - 10), (w - 10, y_offset - 10), (100, 100, 100), 1)
    y_offset += 5
    
    cv2.putText(panel, f"Detected Humans: {len(detections)}", (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    y_offset += line_height
    
    # Human details (max 3)
    if len(detections) > 0:
        for i, det in enumerate(sorted(detections, key=lambda d: d['distance'])[:3]):
            zone_n, zone_c, _ = get_proxemic_zone_and_speed(det['distance'])
            text = f"  Human {i+1}: {det['distance']:.2f}m | {zone_n}"
            cv2.putText(panel, text, (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, zone_c, 1)
            y_offset += 20
    else:
        cv2.putText(panel, "  No humans detected - full speed ahead!", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
    
    # Combine
    combined = np.vstack([frame, panel])
    return combined


def draw_visualization(frame, detections, target_dir, avoidance_dir, total_force):
    """Draw zones, detections, direction arrows, and forces on frame"""
    h, w = frame.shape[:2]
    center_x, center_y = w // 2, h // 2
    
    # Calculate pixel scale (rough approximation)
    fov_h = 69.0  # RealSense FOV
    scale = 100  # pixels per meter (approximate at 2m)
    
    # Draw proxemic zones
    if SHOW_ZONES:
        zones = [
            (R_INTIMATE, (0, 0, 255), 2, "INTIMATE"),
            (R_PERSONAL, (0, 165, 255), 2, "PERSONAL"),
            (R_SOCIAL, (0, 255, 255), 1, "SOCIAL")
        ]
        for radius, color, thickness, label in zones:
            pixel_radius = int(radius * scale)
            cv2.circle(frame, (center_x, center_y), pixel_radius, color, thickness)
    
    # Draw detections
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        zone_name, zone_color, _ = get_proxemic_zone_and_speed(det['distance'])
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), zone_color, 2)
        
        label = f"{det['distance']:.2f}m | {zone_name}"
        cv2.putText(frame, label, (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)
    
    # Draw robot/camera position
    cv2.circle(frame, (center_x, center_y), 12, (255, 0, 0), -1)
    cv2.circle(frame, (center_x, center_y), 15, (255, 255, 255), 2)
    cv2.putText(frame, "CAMERA", (center_x - 35, center_y - 25),
                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 0, 0), 2)
    
    # Draw target direction arrow (blue - goal)
    arrow_len = 80
    target_end_x = int(center_x + target_dir[0] * arrow_len)
    target_end_y = int(center_y - target_dir[1] * arrow_len)  # Y inverted
    cv2.arrowedLine(frame, (center_x, center_y), (target_end_x, target_end_y),
                    (255, 200, 0), 2, tipLength=0.3)  # Cyan - target
    cv2.putText(frame, "TARGET", (target_end_x + 5, target_end_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)
    
    # Draw avoidance direction arrow (green - command)
    avoid_end_x = int(center_x + avoidance_dir[0] * arrow_len * 1.3)
    avoid_end_y = int(center_y - avoidance_dir[1] * arrow_len * 1.3)
    cv2.arrowedLine(frame, (center_x, center_y), (avoid_end_x, avoid_end_y),
                    (0, 255, 0), 3, tipLength=0.25)  # Green - command
    cv2.putText(frame, "COMMAND", (avoid_end_x + 5, avoid_end_y),
                cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 255, 0), 2)
    
    # Draw force vectors (if enabled and humans present)
    if SHOW_FORCES and len(detections) > 0:
        force_scale = 30.0
        force_end_x = int(center_x + total_force[0] * force_scale)
        force_end_y = int(center_y - total_force[1] * force_scale)
        cv2.arrowedLine(frame, (center_x, center_y), (force_end_x, force_end_y),
                        (255, 0, 255), 2, tipLength=0.3)  # Magenta - force
        
        force_mag = math.hypot(total_force[0], total_force[1])
        cv2.putText(frame, f"FORCE: {force_mag:.1f}N", (force_end_x + 5, force_end_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
    
    return frame


# ══════════════════════════════════════════════════════════════════
# ── Main Application ──────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print(" " * 5 + "🎥 CAMERA-BASED AVOIDANCE COMMAND TESTER 🎥")
    print(" " * 10 + "(Manual Sampling Mode)")
    print("=" * 70)
    print()
    print("CONCEPT:")
    print("  User menggeser kamera secara FISIK (manual) menuju target.")
    print("  User tekan SPACE untuk sampling setiap 1/4 detik (250ms).")
    print("  Robot mendeteksi manusia dan memberikan PERINTAH MENGHINDAR.")
    print("  Data disimpan untuk analisis trajectory.")
    print()
    print("Initializing...")
    
    # Load YOLO
    try:
        model = YOLO("yolo11n.pt")
        print("✓ YOLO model loaded")
    except Exception as e:
        print(f"✗ Error loading YOLO: {e}")
        sys.exit(1)
    
    # Configure RealSense
    try:
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        profile = pipeline.start(config)
        align = rs.align(rs.stream.color)
        
        print("✓ RealSense camera initialized")
    except Exception as e:
        print(f"✗ Error initializing camera: {e}")
        sys.exit(1)
    
    print()
    print("=" * 70)
    print("🎮 CONTROLS:")
    print("  [SPACE] - Take sample (manual sampling setiap 0.25s)")
    print("  [R] - Reset statistics and trajectory")
    print("  [S] - Save data to CSV")
    print("  [Q] - Quit and show trajectory graph")
    print()
    print("📊 USAGE:")
    print("  1. GESER KAMERA secara fisik menuju target")
    print("  2. Tekan SPACE untuk sampling setiap 1/4 detik")
    print("  3. Robot menghitung arah menghindar otomatis")
    print("  4. Lihat displacement command untuk 0.25 detik")
    print()
    print("📺 DISPLAY:")
    print("  • Cyan arrow: TARGET direction (goal/forward)")
    print("  • Green arrow: COMMAND direction (avoidance adjusted)")
    print("  • Magenta arrow: FORCE vectors (from humans)")
    print("  • Displacement: X/Y movement for 0.25s (X+=right, Y+=forward)")
    print("=" * 70)
    print()
    print("Starting in 3 seconds...")
    print("▶ Press SPACE to take first sample")
    time.sleep(3)
    
    # State variables
    target_dir = DEFAULT_TARGET.copy()  # Forward by default
    avoidance_dir = target_dir.copy()
    current_speed = BASE_SPEED
    target_speed = BASE_SPEED
    
    # Position tracking (accumulated from displacement)
    position_x = 0.0
    position_y = 0.0
    
    # Sample storage
    samples = []
    sample_count = 0
    
    last_update_time = time.time()
    start_time = time.time()
    
    # Statistics
    total_frames = 0
    frames_with_humans = 0
    
    try:
        while True:
            current_time = time.time()
            elapsed_time = current_time - start_time
            dt = current_time - last_update_time
            
            # Get frames
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                continue
            
            frame = np.asanyarray(color_frame.get_data())
            h, w = frame.shape[:2]
            center_x, center_y = w // 2, h // 2
            
            # Calculate pixel scale
            fov_h = 69.0
            scale = 100  # pixels per meter
            
            # Run YOLO detection
            results = model(frame, classes=[0], verbose=False, conf=0.5)
            
            # Process detections
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
            detections = []
            for box, conf in zip(boxes, confidences):
                x1, y1, x2, y2 = map(int, box[:4])
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)
                
                distance = depth_frame.get_distance(cx, cy)
                
                if 0.1 < distance < 10.0:
                    detections.append({
                        'bbox': (x1, y1, x2, y2),
                        'center': (cx, cy),
                        'distance': distance,
                        'confidence': conf
                    })
            
            # Statistics
            total_frames += 1
            if len(detections) > 0:
                frames_with_humans += 1
            
            # Calculate avoidance direction
            avoidance_dir, total_force, has_humans = calculate_avoidance_direction(
                detections, target_dir, center_x, center_y, scale
            )
            
            # Calculate speed based on proxemic zones
            target_speed, zone_name, closest_dist = calculate_speed_adjustment(detections)
            
            # Smooth speed transition
            speed_change_rate = 2.0  # m/s²
            if current_speed < target_speed:
                current_speed = min(target_speed, current_speed + speed_change_rate * dt)
            elif current_speed > target_speed:
                current_speed = max(target_speed, current_speed - speed_change_rate * dt)
            
            # Calculate velocity using AVOIDANCE direction
            vx = avoidance_dir[0] * current_speed
            vy = avoidance_dir[1] * current_speed
            
            # Draw visualization
            display_frame = draw_visualization(frame, detections, target_dir, 
                                              avoidance_dir, total_force)
            
            # Draw info panel with sample count
            display_frame = draw_info_panel(display_frame, target_dir, avoidance_dir,
                                           current_speed, target_speed, zone_name,
                                           closest_dist, detections, vx, vy, 
                                           elapsed_time, total_force, sample_count)
            
            # Display
            cv2.imshow("Camera-Based Avoidance Command Tester", display_frame)
            
            # Handle keyboard
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' '):
                # MANUAL SAMPLING - Take a sample when SPACE is pressed
                sample = SampleData()
                sample.timestamp = elapsed_time
                sample.position = [position_x, position_y]
                sample.velocity = [vx, vy]
                sample.target_direction = target_dir.tolist()
                sample.avoidance_direction = avoidance_dir.tolist()
                sample.current_speed = current_speed
                sample.target_speed = target_speed
                sample.num_humans = len(detections)
                sample.closest_distance = closest_dist
                sample.proxemic_zone = zone_name
                sample.sfm_force = list(total_force)
                
                # Calculate displacement for 0.25s
                dx_disp, dy_disp = calculate_displacement(vx, vy)
                sample.displacement = [dx_disp, dy_disp]
                
                # Update position (accumulated)
                position_x += dx_disp
                position_y += dy_disp
                
                samples.append(sample)
                sample_count += 1
                
                # Print sample info
                print("\n" + "─" * 70)
                print(f"📍 SAMPLE #{sample_count} at t={elapsed_time:.2f}s")
                print("─" * 70)
                print(f"Position: ({position_x:.3f}, {position_y:.3f}) m")
                print(f"Velocity: ({vx:.3f}, {vy:.3f}) m/s")
                print(f"Speed: {current_speed:.3f} m/s | Zone: {zone_name}")
                print(f"Humans: {len(detections)} | Closest: {closest_dist:.2f}m")
                print(f"SFM Force: ({total_force[0]:.2f}, {total_force[1]:.2f}) N")
                
                command, arrow, _ = get_movement_command(vx, vy, current_speed)
                print(f"Command: {command}")
                print(f"Displacement (0.25s): {dx_disp:+.3f}X  {dy_disp:+.3f}Y")
                print("─" * 70)
                print("▶ Move camera, then press SPACE for next sample")
                
            elif key == ord('q'):
                print("\n👋 Quitting...")
                break
            
            elif key == ord('r'):
                # Reset statistics and trajectory
                samples = []
                sample_count = 0
                position_x = 0.0
                position_y = 0.0
                total_frames = 0
                frames_with_humans = 0
                start_time = time.time()
                current_speed = BASE_SPEED
                print("\n🔄 Statistics and trajectory reset!")
            
            elif key == ord('s'):
                # Save to CSV
                if len(samples) > 0:
                    save_samples_to_csv(samples)
                else:
                    print("\n⚠ No samples to save - press SPACE to take samples first")
            
            last_update_time = current_time
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    
    finally:
        # Cleanup
        pipeline.stop()
        cv2.destroyAllWindows()
        
        print("\n" + "=" * 70)
        print("📊 FINAL STATISTICS:")
        print(f"  Total samples: {sample_count}")
        print(f"  Total frames: {total_frames}")
        print(f"  Frames with humans: {frames_with_humans}")
        if total_frames > 0:
            detection_rate = (frames_with_humans / total_frames) * 100
            print(f"  Detection rate: {detection_rate:.1f}%")
        print(f"  Total time: {elapsed_time:.1f}s")
        if sample_count > 0:
            print(f"  Final position: ({position_x:.3f}, {position_y:.3f}) m")
            print(f"  Distance traveled: {math.hypot(position_x, position_y):.3f} m")
        print("=" * 70)
        
        # Save and plot if samples exist
        if len(samples) > 0:
            print("\n💾 Saving data...")
            save_samples_to_csv(samples)
            
            print("\n📈 Generating trajectory plot...")
            plot_trajectory(samples)
        else:
            print("\n⚠ No samples collected - press SPACE to sample during run")
        
        print("\n✓ Test complete")


if __name__ == '__main__':
    main()
