#!/usr/bin/env python3
"""
Configuration Loader untuk Social Navigation System
===================================================
Utility untuk load config dari YAML file dan generate Python constants.

Usage:
    python3 load_config.py config_social_nav.yaml > config_generated.py
    
Atau import sebagai module:
    from load_config import load_config
    config = load_config('config_social_nav.yaml')
"""

import yaml
import sys
from pathlib import Path


def load_config(config_path='config_social_nav.yaml'):
    """Load configuration from YAML file"""
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def generate_python_constants(config):
    """Generate Python constant definitions from config"""
    
    output = []
    output.append("# Auto-generated configuration constants")
    output.append("# DO NOT EDIT - Edit config_social_nav.yaml instead")
    output.append("")
    
    # Detection
    det = config['detection']
    output.append("# ── Camera & Detection ──")
    output.append(f"YOLO_MODEL_PATH = '{det['model_path']}'")
    output.append(f"YOLO_CONFIDENCE = {det['confidence_threshold']}")
    output.append(f"CAMERA_WIDTH = {det['width']}")
    output.append(f"CAMERA_HEIGHT = {det['height']}")
    output.append(f"CAMERA_FPS = {det['fps']}")
    output.append(f"DETECTION_RATE_HZ = {det['publish_rate_hz']}")
    output.append(f"TRACKING_THRESHOLD_PX = {det['tracking_threshold_pixels']}")
    output.append(f"TRACKING_TIMEOUT = {det['tracking_timeout_seconds']}")
    output.append(f"MIN_DISTANCE = {det['min_distance_m']}")
    output.append(f"MAX_DISTANCE = {det['max_distance_m']}")
    output.append(f"SHOW_VISUALIZATION = {det['show_window']}")
    output.append("")
    
    # SFM
    sfm = config['sfm']
    output.append("# ── Social Force Model ──")
    output.append(f"SFM_V0 = {sfm['desired_velocity']}")
    output.append(f"SFM_TAU = {sfm['relaxation_time']}")
    output.append(f"SFM_MASS = {sfm['effective_mass']}")
    output.append(f"SFM_A = {sfm['repulsion_magnitude']}")
    output.append(f"SFM_B = {sfm['repulsion_range']}")
    output.append(f"MAX_LINEAR = {sfm['max_linear_velocity']}")
    output.append(f"MAX_ANGULAR = {sfm['max_angular_velocity']}")
    output.append(f"SFM_MAX_SPEED = {sfm['max_speed']}")
    output.append(f"CONTROL_RATE = {sfm['control_rate_hz']}")
    output.append("")
    
    # Proxemics
    prox = config['proxemics']
    output.append("# ── Proxemic Zones ──")
    output.append(f"R_INTIMATE = {prox['intimate_radius']}")
    output.append(f"R_PERSONAL = {prox['personal_radius']}")
    output.append(f"R_SOCIAL = {prox['social_radius']}")
    output.append(f"INTIMATE_SPEED_SCALE = {prox['intimate_speed_scale']}")
    output.append(f"PERSONAL_SPEED_SCALE = {prox['personal_speed_scale']}")
    output.append(f"SOCIAL_SPEED_SCALE = {prox['social_speed_scale']}")
    output.append("")
    
    # Navigation
    nav = config['navigation']
    output.append("# ── Navigation ──")
    output.append(f"USE_WAYPOINT_NAV = {nav['use_waypoint_nav']}")
    output.append(f"DEFAULT_WAYPOINT = ({nav['default_goal_x']}, {nav['default_goal_y']})")
    output.append(f"WAYPOINT_TOLERANCE = {nav['waypoint_tolerance']}")
    output.append("")
    
    # Robot
    robot = config['robot']
    output.append("# ── Robot Hardware ──")
    output.append(f"SERIAL_PORT = '{robot['serial_port']}'")
    output.append(f"SERIAL_BAUD = {robot['serial_baud']}")
    output.append(f"WHEEL_RADIUS = {robot['wheel_radius']}")
    output.append(f"MAX_WHEEL_VEL = {robot['max_wheel_velocity']}")
    output.append(f"ROBOT_EMA = {robot['velocity_ema_alpha']}")
    output.append(f"CMD_VEL_TIMEOUT = {robot['cmd_vel_timeout']}")
    output.append(f"V_MIN_3S = {robot['battery_voltage_min']}")
    output.append(f"V_MAX_3S = {robot['battery_voltage_max']}")
    output.append(f"BATTERY_CAPACITY_AH = {robot['battery_capacity_ah']}")
    output.append("")
    
    # Advanced
    adv = config['advanced']
    output.append("# ── Advanced ──")
    output.append(f"USE_PREDICTIVE_SFM = {adv['use_predictive_sfm']}")
    output.append(f"LATERAL_NUDGE_GAIN = {adv['lateral_nudge_gain']}")
    output.append(f"USE_DEAD_RECKONING = {adv['use_dead_reckoning']}")
    output.append(f"LOG_LEVEL = '{adv['log_level']}'")
    output.append(f"LOG_FORCES = {adv['log_forces']}")
    output.append("")
    
    return "\n".join(output)


def print_config_summary(config):
    """Print human-readable summary of configuration"""
    
    print("=" * 70)
    print("Social Navigation System - Configuration Summary")
    print("=" * 70)
    print()
    
    print("📹 Detection:")
    det = config['detection']
    print(f"  Model: {det['model_path']}")
    print(f"  Resolution: {det['width']}x{det['height']} @ {det['fps']} FPS")
    print(f"  Rate: {det['publish_rate_hz']} Hz")
    print(f"  Confidence: {det['confidence_threshold']}")
    print()
    
    print("🧮 Social Force Model:")
    sfm = config['sfm']
    print(f"  Desired velocity: {sfm['desired_velocity']} m/s")
    print(f"  Repulsion: A={sfm['repulsion_magnitude']} N, B={sfm['repulsion_range']} m")
    print(f"  Max speed: {sfm['max_linear_velocity']} m/s")
    print(f"  Control rate: {sfm['control_rate_hz']} Hz")
    print()
    
    print("👥 Proxemic Zones:")
    prox = config['proxemics']
    print(f"  🔴 Intimate: < {prox['intimate_radius']}m → STOP")
    print(f"  🟠 Personal: {prox['intimate_radius']}-{prox['personal_radius']}m → {prox['personal_speed_scale']*100:.0f}% speed")
    print(f"  🟡 Social: {prox['personal_radius']}-{prox['social_radius']}m → AVOID")
    print(f"  🟢 Public: > {prox['social_radius']}m → NORMAL")
    print()
    
    print("🤖 Robot:")
    robot = config['robot']
    print(f"  Serial: {robot['serial_port']} @ {robot['serial_baud']} baud")
    print(f"  Battery: {robot['battery_voltage_min']}-{robot['battery_voltage_max']}V ({robot['battery_capacity_ah']}Ah)")
    print()
    
    print("=" * 70)


def main():
    if len(sys.argv) < 2:
        config_path = 'config_social_nav.yaml'
    else:
        config_path = sys.argv[1]
    
    try:
        config = load_config(config_path)
        
        # If output redirected (stdout to file), generate Python constants
        if not sys.stdout.isatty():
            print(generate_python_constants(config))
        else:
            # Otherwise, print summary
            print_config_summary(config)
            print()
            print("To generate Python constants:")
            print(f"  python3 load_config.py {config_path} > config_generated.py")
            print()
            print("To use in your node:")
            print("  from load_config import load_config")
            print(f"  config = load_config('{config_path}')")
            print("  SFM_A = config['sfm']['repulsion_magnitude']")
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
