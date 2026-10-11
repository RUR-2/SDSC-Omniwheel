#!/usr/bin/env python3
"""
Social Force Model Controller for Real Robot (ROS 2 Humble)
============================================================
Implementasi Social Force Model (Helbing & Molnar 1995) untuk
kontrol navigasi robot real dengan obstacle avoidance dinamis.

Input:
  - /human_detections : Data deteksi manusia dari camera
  - /cmd_vel (optional): Goal velocity dari user/planner

Output:
  - /cmd_vel : Velocity command dengan SFM avoidance

Cara kerja:
  1. Terima goal velocity (atau gunakan default waypoint)
  2. Terima deteksi manusia dari camera
  3. Hitung gaya repulsif dari setiap manusia (SFM)
  4. Modulate velocity untuk hindari collision
  5. Publish cmd_vel ke robot

Author: Brone Social Nav Team
Version: 1.0
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import String, Bool
import json
import math
import time


# ══════════════════════════════════════════════════════════════════
# ── Social Force Model Parameters ─────────────────────────────────
# ══════════════════════════════════════════════════════════════════

SFM_V0 = 0.25          # m/s - desired velocity (matching robot max)
SFM_TAU = 0.5          # s - relaxation time
SFM_A = 5.0            # N - repulsive force magnitude (base)
SFM_B = 0.8            # m - repulsive force range
SFM_MASS = 5.0         # kg - robot effective mass
SFM_MAX_SPEED = 0.6    # m/s - absolute max speed

# Robot safety zones
R_INTIMATE = 0.45      # m - emergency stop zone
R_PERSONAL = 1.20      # m - slow down zone
R_SOCIAL = 3.60        # m - avoidance zone

# ══════════════════════════════════════════════════════════════════
# ── IMPROVED PARAMETERS - Faster Evasion & Stronger SFM ──────────
# ══════════════════════════════════════════════════════════════════

# Early activation threshold (start evasion earlier)
R_EVASION_START = 3.50  # m - mulai menghindar lebih awal!

# Lateral force multipliers (progressive based on distance)
LATERAL_MULTIPLIER_FAR = 2.0      # di 3.5-3.6m (early response)
LATERAL_MULTIPLIER_SOCIAL = 3.0   # di 1.2-3.5m (aggressive avoidance)
LATERAL_MULTIPLIER_PERSONAL = 5.0 # di 0.45-1.2m (very aggressive)
LATERAL_MULTIPLIER_INTIMATE = 8.0 # di <0.45m (emergency)

# Speed reduction multipliers (more aggressive slowdown)
SPEED_MULTIPLIER_SOCIAL = 0.6     # 60% speed di SOCIAL (was ~80%)
SPEED_MULTIPLIER_PERSONAL = 0.3   # 30% speed di PERSONAL (was ~60%)

# Control parameters
MAX_LINEAR = 0.3       # m/s - max linear velocity
MAX_ANGULAR = 0.6      # rad/s - max angular velocity
CONTROL_RATE = 20.0    # Hz - control loop frequency

# Goal parameters
USE_WAYPOINT_NAV = False    # False = use external /goal topic
DEFAULT_WAYPOINT = (2.0, 0.0)  # Default goal if no external goal
WAYPOINT_TOLERANCE = 0.3    # m


class SocialForceController(Node):
    def __init__(self):
        super().__init__('social_force_controller')
        
        # State
        self.human_detections = []
        self.goal_x = DEFAULT_WAYPOINT[0]
        self.goal_y = DEFAULT_WAYPOINT[1]
        self.goal_active = USE_WAYPOINT_NAV
        
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_w = 0.0
        
        self.robot_x = 0.0  # Estimated position (TODO: integrate with odometry)
        self.robot_y = 0.0
        self.robot_theta = 0.0
        
        self.system_enabled = True
        
        # Subscribers
        self.sub_detections = self.create_subscription(
            String,
            '/human_detections',
            self.detections_callback,
            10
        )
        
        self.sub_goal = self.create_subscription(
            PoseStamped,
            '/goal_pose',
            self.goal_callback,
            10
        )
        
        self.sub_enable = self.create_subscription(
            Bool,
            '/system/enable',
            self.enable_callback,
            10
        )
        
        # If not using waypoint nav, subscribe to external cmd_vel as goal velocity
        if not USE_WAYPOINT_NAV:
            self.sub_cmd_vel_goal = self.create_subscription(
                Twist,
                '/cmd_vel_goal',
                self.cmd_vel_goal_callback,
                10
            )
        
        # Publishers
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_debug = self.create_publisher(String, '/sfm_debug', 10)
        
        # Control timer
        self.dt = 1.0 / CONTROL_RATE
        self.create_timer(self.dt, self.control_loop)
        
        # Timeout tracking
        self.last_detection_time = time.time()
        
        self.get_logger().info("✅ Social Force Controller initialized")
        self.get_logger().info(f"   Control rate: {CONTROL_RATE} Hz")
        self.get_logger().info(f"   SFM params: A={SFM_A}, B={SFM_B}, τ={SFM_TAU}")
        self.get_logger().info(f"   Safety zones: Intimate={R_INTIMATE}m, Personal={R_PERSONAL}m, Social={R_SOCIAL}m")
        self.get_logger().info(f"   🚀 IMPROVED: Early evasion at {R_EVASION_START}m")
        self.get_logger().info(f"   🚀 IMPROVED: Lateral multipliers: {LATERAL_MULTIPLIER_FAR}x/{LATERAL_MULTIPLIER_SOCIAL}x/{LATERAL_MULTIPLIER_PERSONAL}x/{LATERAL_MULTIPLIER_INTIMATE}x")
        self.get_logger().info(f"   🚀 IMPROVED: Speed reduction: SOCIAL={SPEED_MULTIPLIER_SOCIAL*100:.0f}%, PERSONAL={SPEED_MULTIPLIER_PERSONAL*100:.0f}%")
        if USE_WAYPOINT_NAV:
            self.get_logger().info(f"   Mode: Waypoint navigation to {DEFAULT_WAYPOINT}")
        else:
            self.get_logger().info(f"   Mode: External velocity goals (/cmd_vel_goal)")
    
    def enable_callback(self, msg: Bool):
        """System enable/disable"""
        self.system_enabled = msg.data
        status = "ENABLED" if self.system_enabled else "DISABLED"
        self.get_logger().warn(f"⚡ System {status}")
    
    def detections_callback(self, msg: String):
        """Receive human detections from camera"""
        try:
            data = json.loads(msg.data)
            self.human_detections = data['detections']
            self.last_detection_time = time.time()
        except Exception as e:
            self.get_logger().error(f"Failed to parse detections: {e}")
    
    def goal_callback(self, msg: PoseStamped):
        """Receive goal pose"""
        self.goal_x = msg.pose.position.x
        self.goal_y = msg.pose.position.y
        self.goal_active = True
        self.get_logger().info(f"New goal: ({self.goal_x:.2f}, {self.goal_y:.2f})")
    
    def cmd_vel_goal_callback(self, msg: Twist):
        """Receive desired velocity from external planner"""
        # Convert desired velocity to goal point (short horizon)
        # Goal is 1 second ahead in desired direction
        horizon = 1.0  # second
        self.goal_x = self.robot_x + msg.linear.x * horizon
        self.goal_y = self.robot_y + msg.linear.y * horizon
        self.goal_active = True
    
    def sfm_goal_force(self, robot_x, robot_y, vx, vy, goal_x, goal_y):
        """
        F_goal = m/τ × (V0 × ê_goal − v_current)
        """
        dx = goal_x - robot_x
        dy = goal_y - robot_y
        dist = math.hypot(dx, dy)
        
        if dist < 1e-6:
            return 0.0, 0.0
        
        # Unit vector toward goal
        ex = dx / dist
        ey = dy / dist
        
        # Desired velocity
        desired_vx = SFM_V0 * ex
        desired_vy = SFM_V0 * ey
        
        # Force
        fx = SFM_MASS / SFM_TAU * (desired_vx - vx)
        fy = SFM_MASS / SFM_TAU * (desired_vy - vy)
        
        return fx, fy
    
    def sfm_repulsive_force(self, robot_x, robot_y, human_x, human_y, distance):
        """
        F_rep = A × exp(−d/B) × n̂ × lateral_multiplier
        Tolak dari human menuju robot
        
        IMPROVED: Lateral force multiplier berdasarkan jarak untuk faster evasion
        """
        dx = robot_x - human_x
        dy = robot_y - human_y
        dist = distance  # use pre-calculated distance
        
        if dist < 1e-6:
            # Sangat dekat - tolak dengan kuat
            return 100.0, 0.0
        
        # Base magnitude
        mag = SFM_A * math.exp(-dist / SFM_B)
        
        # ═══════════════════════════════════════════════════════════
        # IMPROVEMENT: Progressive lateral force multiplier
        # ═══════════════════════════════════════════════════════════
        lateral_multiplier = 1.0
        
        if dist < R_INTIMATE:
            # INTIMATE zone: emergency level
            lateral_multiplier = LATERAL_MULTIPLIER_INTIMATE
        elif dist < R_PERSONAL:
            # PERSONAL zone: very aggressive
            lateral_multiplier = LATERAL_MULTIPLIER_PERSONAL
        elif dist < R_SOCIAL:
            # SOCIAL zone: aggressive
            lateral_multiplier = LATERAL_MULTIPLIER_SOCIAL
        elif dist < R_EVASION_START:
            # Early evasion: moderate boost
            lateral_multiplier = LATERAL_MULTIPLIER_FAR
        
        # Apply multiplier to magnitude
        mag *= lateral_multiplier
        
        # Direction (away from human)
        fx = mag * dx / dist
        fy = mag * dy / dist
        
        return fx, fy
    
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
    
    def control_loop(self):
        """Main control loop - runs at CONTROL_RATE Hz"""
        
        if not self.system_enabled:
            # E-stop - send zero velocity
            self.publish_velocity(0.0, 0.0, 0.0)
            return
        
        # Check if we have recent detections (< 1 second old)
        detection_valid = (time.time() - self.last_detection_time) < 1.0
        
        # If no goal, don't move
        if not self.goal_active:
            self.publish_velocity(0.0, 0.0, 0.0)
            return
        
        # Check if goal reached
        dist_to_goal = math.hypot(self.goal_x - self.robot_x, self.goal_y - self.robot_y)
        if dist_to_goal < WAYPOINT_TOLERANCE:
            self.get_logger().info(f"Goal reached at ({self.robot_x:.2f}, {self.robot_y:.2f})")
            self.goal_active = False
            self.publish_velocity(0.0, 0.0, 0.0)
            return
        
        # ════════════════════════════════════════════════════════
        # Social Force Model Calculation
        # ════════════════════════════════════════════════════════
        
        # 1. Goal force
        fx_goal, fy_goal = self.sfm_goal_force(
            self.robot_x, self.robot_y,
            self.current_vx, self.current_vy,
            self.goal_x, self.goal_y
        )
        
        # 2. Repulsive forces from humans
        fx_rep = 0.0
        fy_rep = 0.0
        closest_dist = 999.0
        closest_zone = "PUBLIC"
        
        if detection_valid and len(self.human_detections) > 0:
            for human in self.human_detections:
                # Human position relative to robot
                hx = human['position']['x']  # forward
                hy = human['position']['y']  # left
                
                # Convert to world frame (simple: assume robot at origin facing +X)
                # For now, treat camera frame as world frame
                human_world_x = self.robot_x + hx
                human_world_y = self.robot_y + hy
                
                dist = math.hypot(hx, hy)
                
                if dist < closest_dist:
                    closest_dist = dist
                    closest_zone = self.get_proxemic_zone(dist)
                
                # ═══════════════════════════════════════════════════════════
                # IMPROVEMENT: Pass distance to use improved force calculation
                # ═══════════════════════════════════════════════════════════
                frx, fry = self.sfm_repulsive_force(
                    self.robot_x, self.robot_y,
                    human_world_x, human_world_y,
                    dist  # pass distance for multiplier calculation
                )
                
                fx_rep += frx
                fy_rep += fry
        
        # 3. Total force
        fx_total = fx_goal + fx_rep
        fy_total = fy_goal + fy_rep
        
        # 4. Acceleration
        ax = fx_total / SFM_MASS
        ay = fy_total / SFM_MASS
        
        # 5. Update velocity (Euler integration)
        vx_new = self.current_vx + ax * self.dt
        vy_new = self.current_vy + ay * self.dt
        
        # 6. Limit velocity
        speed = math.hypot(vx_new, vy_new)
        if speed > SFM_MAX_SPEED:
            vx_new = vx_new / speed * SFM_MAX_SPEED
            vy_new = vy_new / speed * SFM_MAX_SPEED
        
        # 7. Emergency stop in intimate zone & improved speed reduction
        if closest_zone == "INTIMATE":
            self.get_logger().warn(f"🔴 INTIMATE ZONE ({closest_dist:.2f}m) - EMERGENCY STOP")
            vx_new = 0.0
            vy_new = 0.0
        elif closest_zone == "PERSONAL":
            # ═══════════════════════════════════════════════════════════
            # IMPROVEMENT: More aggressive speed reduction (30% instead of old ~60%)
            # ═══════════════════════════════════════════════════════════
            vx_new *= SPEED_MULTIPLIER_PERSONAL
            vy_new *= SPEED_MULTIPLIER_PERSONAL
            self.get_logger().info(f"🟠 PERSONAL ZONE ({closest_dist:.2f}m) - SLOW DOWN (30%)")
        elif closest_zone == "SOCIAL":
            # ═══════════════════════════════════════════════════════════
            # IMPROVEMENT: Reduce speed more in SOCIAL zone (60% instead of old ~80%)
            # ═══════════════════════════════════════════════════════════
            vx_new *= SPEED_MULTIPLIER_SOCIAL
            vy_new *= SPEED_MULTIPLIER_SOCIAL
            self.get_logger().info(f"🟡 SOCIAL ZONE ({closest_dist:.2f}m) - AVOIDING (60% speed)")
        elif closest_dist < R_EVASION_START:
            # ═══════════════════════════════════════════════════════════
            # IMPROVEMENT: Early evasion activation (3.5m threshold)
            # Even in PUBLIC zone, if human detected close, start preparing
            # ═══════════════════════════════════════════════════════════
            vx_new *= 0.8  # slight slowdown for early reaction
            vy_new *= 0.8
            self.get_logger().info(f"🟢 EARLY EVASION ({closest_dist:.2f}m) - PREPARING (80% speed)")
        
        # Clamp to max velocities
        vx_new = max(-MAX_LINEAR, min(MAX_LINEAR, vx_new))
        vy_new = max(-MAX_LINEAR, min(MAX_LINEAR, vy_new))
        
        # 8. Calculate angular velocity (simple: point toward goal)
        angle_to_goal = math.atan2(self.goal_y - self.robot_y, self.goal_x - self.robot_x)
        angle_error = angle_to_goal - self.robot_theta
        # Normalize angle to [-pi, pi]
        while angle_error > math.pi:
            angle_error -= 2 * math.pi
        while angle_error < -math.pi:
            angle_error += 2 * math.pi
        
        w_new = 2.0 * angle_error  # P controller
        w_new = max(-MAX_ANGULAR, min(MAX_ANGULAR, w_new))
        
        # Update state
        self.current_vx = vx_new
        self.current_vy = vy_new
        self.current_w = w_new
        
        # Update robot position estimate (dead reckoning - not accurate without odometry!)
        self.robot_x += vx_new * self.dt
        self.robot_y += vy_new * self.dt
        self.robot_theta += w_new * self.dt
        
        # Publish
        self.publish_velocity(vx_new, vy_new, w_new)
        
        # Debug info
        debug_data = {
            'robot_pos': [self.robot_x, self.robot_y, self.robot_theta],
            'goal_pos': [self.goal_x, self.goal_y],
            'velocity': [vx_new, vy_new, w_new],
            'forces': {
                'goal': [fx_goal, fy_goal],
                'repulsive': [fx_rep, fy_rep],
                'total': [fx_total, fy_total]
            },
            'closest_human': {
                'distance': closest_dist,
                'zone': closest_zone
            },
            'num_detections': len(self.human_detections)
        }
        
        debug_msg = String()
        debug_msg.data = json.dumps(debug_data)
        self.pub_debug.publish(debug_msg)
    
    def publish_velocity(self, vx, vy, w):
        """Publish velocity command"""
        msg = Twist()
        msg.linear.x = float(vx)
        msg.linear.y = float(vy)
        msg.angular.z = float(w)
        self.pub_cmd_vel.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SocialForceController()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Send stop command
        stop_msg = Twist()
        node.pub_cmd_vel.publish(stop_msg)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
