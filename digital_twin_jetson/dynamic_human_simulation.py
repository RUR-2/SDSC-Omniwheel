#!/usr/bin/env python3
"""
Dynamic Human Simulation - Improved SFM Controller
===================================================
Simulasi robot dengan manusia yang bergerak mendekat
menggunakan parameter SFM yang sudah diperbaharui (v1.1)

Scenario:
- Human: Bergerak dari (0, 4.2) → (0, 0) dengan kecepatan 1.2 m/s
- Robot: Mulai dari (0, 0) bergerak forward dengan kecepatan awal 1.0 m/s
- Sample rate: 4 Hz (setiap 0.25s)
- Field of view: 100 degrees

Author: Brone Social Nav Team
Date: 2026-10-06
"""

import math
import json
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
# Parameters (from improved social_force_controller.py v1.1)
# ══════════════════════════════════════════════════════════════════

# SFM Parameters
SFM_V0 = 0.25          # m/s - desired velocity
SFM_TAU = 0.5          # s - relaxation time
SFM_A = 5.0            # N - repulsive force magnitude
SFM_B = 0.8            # m - repulsive force range
SFM_MASS = 5.0         # kg - robot mass
SFM_MAX_SPEED = 0.6    # m/s - max speed

# Safety zones
R_INTIMATE = 0.45      # m
R_PERSONAL = 1.20      # m
R_SOCIAL = 3.60        # m
R_EVASION_START = 3.50 # m - early activation

# Improved parameters (v1.1)
LATERAL_MULTIPLIER_FAR = 2.0
LATERAL_MULTIPLIER_SOCIAL = 3.0
LATERAL_MULTIPLIER_PERSONAL = 5.0
LATERAL_MULTIPLIER_INTIMATE = 8.0

SPEED_MULTIPLIER_SOCIAL = 0.6
SPEED_MULTIPLIER_PERSONAL = 0.3

# Simulation parameters
DT = 0.25              # s - sample interval (4 Hz)
FOV_ANGLE = 100        # degrees - field of view
MAX_SAMPLES = 100      # safety limit


def get_lateral_multiplier(distance):
    """Get lateral force multiplier based on distance"""
    if distance < R_INTIMATE:
        return LATERAL_MULTIPLIER_INTIMATE
    elif distance < R_PERSONAL:
        return LATERAL_MULTIPLIER_PERSONAL
    elif distance < R_SOCIAL:
        return LATERAL_MULTIPLIER_SOCIAL
    elif distance < R_EVASION_START:
        return LATERAL_MULTIPLIER_FAR
    else:
        return 1.0


def get_speed_multiplier(distance):
    """Get speed reduction multiplier based on distance"""
    if distance < R_INTIMATE:
        return 0.0  # STOP
    elif distance < R_PERSONAL:
        return SPEED_MULTIPLIER_PERSONAL
    elif distance < R_SOCIAL:
        return SPEED_MULTIPLIER_SOCIAL
    elif distance < R_EVASION_START:
        return 0.8  # early evasion
    else:
        return 1.0


def get_zone(distance):
    """Get proxemic zone name"""
    if distance < R_INTIMATE:
        return "INTIMATE"
    elif distance < R_PERSONAL:
        return "PERSONAL"
    elif distance < R_SOCIAL:
        return "SOCIAL"
    else:
        return "PUBLIC"


def is_in_fov(robot_x, robot_y, robot_theta, human_x, human_y, fov_degrees):
    """Check if human is in robot's field of view"""
    # Vector from robot to human
    dx = human_x - robot_x
    dy = human_y - robot_y
    
    # Angle to human
    angle_to_human = math.atan2(dy, dx)
    
    # Angle difference
    angle_diff = angle_to_human - robot_theta
    
    # Normalize to [-pi, pi]
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    # Check if within FOV
    fov_rad = math.radians(fov_degrees / 2)
    return abs(angle_diff) <= fov_rad


def sfm_goal_force(robot_vx, robot_vy, goal_vx, goal_vy):
    """Calculate goal force"""
    fx = SFM_MASS / SFM_TAU * (goal_vx - robot_vx)
    fy = SFM_MASS / SFM_TAU * (goal_vy - robot_vy)
    return fx, fy


def sfm_repulsive_force(robot_x, robot_y, human_x, human_y, distance):
    """Calculate repulsive force with lateral multiplier"""
    dx = robot_x - human_x
    dy = robot_y - human_y
    
    if distance < 1e-6:
        return 100.0, 0.0
    
    # Base magnitude
    mag = SFM_A * math.exp(-distance / SFM_B)
    
    # Apply lateral multiplier (v1.1 improvement)
    lateral_mult = get_lateral_multiplier(distance)
    mag *= lateral_mult
    
    # Direction (away from human)
    fx = mag * dx / distance
    fy = mag * dy / distance
    
    return fx, fy


def simulate_dynamic_encounter():
    """Run simulation of robot encountering moving human"""
    
    print("="*80)
    print("DYNAMIC HUMAN ENCOUNTER SIMULATION")
    print("Using Improved SFM Controller (v1.1)")
    print("="*80)
    print()
    print("Scenario:")
    print("  • Human: (0, 4.2) → (0, 0) at 1.2 m/s")
    print("  • Robot: (0, 0) → forward at initial 1.0 m/s")
    print("  • Sample rate: 4 Hz (every 0.25s)")
    print("  • Field of view: 100 degrees")
    print()
    
    # Initial conditions
    robot_x = 0.0
    robot_y = 0.0
    robot_theta = math.pi / 2  # facing forward (90 degrees)
    robot_vx = 0.0
    robot_vy = 1.0  # 1.0 m/s forward
    
    human_x = 0.0
    human_y = 4.2
    human_vx = 0.0
    human_vy = -1.2  # moving toward origin
    
    # Desired goal velocity (forward)
    goal_vx = 0.0
    goal_vy = SFM_V0  # 0.25 m/s forward
    
    time = 0.0
    sample_num = 0
    samples = []
    
    print("Starting simulation...")
    print()
    
    while sample_num < MAX_SAMPLES:
        # Calculate distance
        dx = human_x - robot_x
        dy = human_y - robot_y
        distance = math.hypot(dx, dy)
        
        # Check if human in FOV
        in_fov = is_in_fov(robot_x, robot_y, robot_theta, human_x, human_y, FOV_ANGLE)
        
        if not in_fov:
            print(f"Sample #{sample_num+1}: Human out of FOV - Simulation ended")
            break
        
        # Get zone
        zone = get_zone(distance)
        
        # Calculate SFM forces
        fx_goal, fy_goal = sfm_goal_force(robot_vx, robot_vy, goal_vx, goal_vy)
        fx_rep, fy_rep = sfm_repulsive_force(robot_x, robot_y, human_x, human_y, distance)
        
        # Total force
        fx_total = fx_goal + fx_rep
        fy_total = fy_goal + fy_rep
        
        # Acceleration
        ax = fx_total / SFM_MASS
        ay = fy_total / SFM_MASS
        
        # Update velocity (Euler integration)
        vx_new = robot_vx + ax * DT
        vy_new = robot_vy + ay * DT
        
        # Limit to max speed
        speed = math.hypot(vx_new, vy_new)
        if speed > SFM_MAX_SPEED:
            vx_new = vx_new / speed * SFM_MAX_SPEED
            vy_new = vy_new / speed * SFM_MAX_SPEED
        
        # Apply zone-based speed reduction (v1.1)
        speed_mult = get_speed_multiplier(distance)
        vx_new *= speed_mult
        vy_new *= speed_mult
        
        # Calculate force magnitude
        force_mag = math.hypot(fx_rep, fy_rep)
        
        # Get lateral multiplier for logging
        lateral_mult = get_lateral_multiplier(distance)
        
        # Store sample
        sample = {
            'sample': sample_num + 1,
            'time': round(time, 2),
            'robot_x': round(robot_x, 3),
            'robot_y': round(robot_y, 3),
            'robot_vx': round(robot_vx, 3),
            'robot_vy': round(robot_vy, 3),
            'robot_speed': round(math.hypot(robot_vx, robot_vy), 3),
            'human_x': round(human_x, 3),
            'human_y': round(human_y, 3),
            'distance': round(distance, 3),
            'zone': zone,
            'force_x': round(fx_rep, 2),
            'force_y': round(fy_rep, 2),
            'force_magnitude': round(force_mag, 2),
            'lateral_multiplier': lateral_mult,
            'speed_multiplier': speed_mult
        }
        samples.append(sample)
        
        # Print sample
        print(f"Sample #{sample_num+1:2d} | t={time:5.2f}s | "
              f"Robot: ({robot_x:5.2f}, {robot_y:5.2f}) | "
              f"Human: ({human_x:5.2f}, {human_y:5.2f}) | "
              f"d={distance:5.2f}m | "
              f"Zone: {zone:8s} | "
              f"F={force_mag:6.2f}N ({lateral_mult}x) | "
              f"V={math.hypot(robot_vx, robot_vy):4.2f}m/s")
        
        # Update robot state
        robot_vx = vx_new
        robot_vy = vy_new
        robot_x += robot_vx * DT
        robot_y += robot_vy * DT
        robot_theta = math.atan2(robot_vy, robot_vx)
        
        # Update human state
        human_x += human_vx * DT
        human_y += human_vy * DT
        
        # Check if human passed through (behind robot)
        if human_y < -0.5:
            print(f"\nSample #{sample_num+1}: Human passed robot - Simulation ended")
            break
        
        # Next iteration
        time += DT
        sample_num += 1
    
    print()
    print("="*80)
    print("SIMULATION COMPLETE")
    print("="*80)
    print(f"Total samples: {len(samples)}")
    print(f"Duration: {time:.2f} seconds")
    print(f"Final robot position: ({robot_x:.2f}, {robot_y:.2f})")
    print(f"Final human position: ({human_x:.2f}, {human_y:.2f})")
    
    # Statistics
    min_distance = min(s['distance'] for s in samples)
    max_force = max(s['force_magnitude'] for s in samples)
    intimate_count = sum(1 for s in samples if s['zone'] == 'INTIMATE')
    
    print()
    print("Statistics:")
    print(f"  • Minimum distance: {min_distance:.2f}m")
    print(f"  • Maximum force: {max_force:.2f}N")
    print(f"  • INTIMATE violations: {intimate_count}")
    
    if intimate_count == 0:
        print("  ✅ No INTIMATE zone violations - System performed safely!")
    else:
        print(f"  ⚠️ {intimate_count} INTIMATE zone violations detected")
    
    print("="*80)
    
    return samples


def save_to_csv(samples, filename='dynamic_simulation.csv'):
    """Save samples to CSV"""
    if not samples:
        return
    
    # CSV header
    header = ','.join(samples[0].keys())
    
    # CSV rows
    rows = []
    for s in samples:
        row = ','.join(str(v) for v in s.values())
        rows.append(row)
    
    # Write file
    csv_content = header + '\n' + '\n'.join(rows)
    
    with open(filename, 'w') as f:
        f.write(csv_content)
    
    print(f"\n✅ Data saved to: {filename}")


def save_to_json(samples, filename='dynamic_simulation.json'):
    """Save samples to JSON"""
    if not samples:
        return
    
    data = {
        'scenario': {
            'description': 'Dynamic human encounter - moving toward robot',
            'human_start': [0.0, 4.2],
            'human_velocity': [0.0, -1.2],
            'robot_start': [0.0, 0.0],
            'robot_initial_velocity': [0.0, 1.0],
            'sample_rate': 4.0,
            'fov_degrees': 100
        },
        'parameters': {
            'sfm_a': SFM_A,
            'sfm_b': SFM_B,
            'lateral_multipliers': {
                'far': LATERAL_MULTIPLIER_FAR,
                'social': LATERAL_MULTIPLIER_SOCIAL,
                'personal': LATERAL_MULTIPLIER_PERSONAL,
                'intimate': LATERAL_MULTIPLIER_INTIMATE
            },
            'speed_multipliers': {
                'social': SPEED_MULTIPLIER_SOCIAL,
                'personal': SPEED_MULTIPLIER_PERSONAL
            }
        },
        'samples': samples,
        'statistics': {
            'total_samples': len(samples),
            'duration': samples[-1]['time'] if samples else 0,
            'min_distance': min(s['distance'] for s in samples) if samples else 0,
            'max_force': max(s['force_magnitude'] for s in samples) if samples else 0,
            'intimate_violations': sum(1 for s in samples if s['zone'] == 'INTIMATE')
        },
        'generated': datetime.now().isoformat()
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Data saved to: {filename}")


def main():
    """Main function"""
    # Run simulation
    samples = simulate_dynamic_encounter()
    
    # Save results
    save_to_csv(samples)
    save_to_json(samples)
    
    print("\n📊 Use the CSV file with visualization scripts to see graphs")
    print("   Or create HTML report from JSON data")


if __name__ == '__main__':
    main()
