#!/usr/bin/env python3
"""
Tester104: Manual Control + Social Avoidance
Supports WASD keyboard and Xbox controller with YOLO-based human detection
"""

import os
import sys
import select
import termios
import tty
import time
import math
import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from std_msgs.msg import String
import cv2
from cv_bridge import CvBridge
import threading

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("⚠️  pygame not installed. Xbox controller support disabled.")
    print("   Install: pip3 install pygame")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  ultralytics not installed. YOLO detection disabled.")
    print("   Install: pip3 install ultralytics")

BANNER = """
==========================================================
   🎮 TESTER104: MANUAL CONTROL + SOCIAL AVOIDANCE      
==========================================================
   Kontrol Manual: WASD Keyboard atau Xbox Controller
   Social Avoidance: YOLO Human Detection dari Kamera
   
   📹 Deteksi manusia dari kamera real-time
   🚧 Otomatis menghindari manusia yang terdeteksi
   🎮 Dual input: Keyboard (WASD) atau Xbox Controller
==========================================================

KEYBOARD CONTROLS:
  [W] : Maju              [Q] : Putar Kiri
  [S] : Mundur            [E] : Putar Kanan
  [A] : Strafe Kiri       [Space/X] : Stop
  [D] : Strafe Kanan      [R/F] : Kecepatan +/-
  [V] : Toggle Avoidance  [C] : Toggle Camera View
  [Ctrl+C] : Exit

XBOX CONTROLLER:
  Left Stick  : Forward/Backward & Strafe
  Right Stick : Rotation
  A Button    : Enable Avoidance
  B Button    : Disable Avoidance
  Y Button    : Toggle Camera View
  Start       : Reset Speed
==========================================================
"""

def get_key(settings, timeout=0.05):
    """Non-blocking keyboard input"""
    if sys.stdin.isatty():
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        return key
    return ''

class SocialAvoidanceTeleop(Node):
    def __init__(self):
        super().__init__('social_avoidance_teleop')
        
        # Publishers
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_status = self.create_publisher(String, '/teleop_status', 10)
        
        # Subscribers
        self.sub_camera = self.create_subscription(
            Image, '/camera/image_raw', self.camera_callback, 10)
        
        # Control parameters
        self.linear_speed = 0.5   # m/s
        self.angular_speed = 0.8  # rad/s
        self.max_linear = 1.2
        self.max_angular = 1.5
        
        # Manual control inputs
        self.manual_vx = 0.0
        self.manual_vy = 0.0
        self.manual_w = 0.0
        
        # Social avoidance
        self.avoidance_enabled = True
        self.detected_humans = []
        self.avoidance_force_x = 0.0
        self.avoidance_force_y = 0.0
        
        # Camera
        self.bridge = CvBridge()
        self.latest_frame = None
        self.show_camera = False
        self.frame_lock = threading.Lock()
        
        # YOLO detection
        self.yolo_model = None
        if YOLO_AVAILABLE:
            try:
                self.yolo_model = YOLO('yolov8n.pt')  # Nano model for speed
                self.get_logger().info("✅ YOLO model loaded successfully")
            except Exception as e:
                self.get_logger().warn(f"⚠️  YOLO model loading failed: {e}")
                YOLO_AVAILABLE = False
        
        # Xbox controller
        self.joystick = None
        if PYGAME_AVAILABLE:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.get_logger().info(f"✅ Xbox controller connected: {self.joystick.get_name()}")
            else:
                self.get_logger().info("ℹ️  No Xbox controller detected, keyboard only")
        
        # Control loop timer
        self.create_timer(0.05, self.control_loop)  # 20 Hz
        
        self.get_logger().info("🚀 Social Avoidance Teleop Active")
        self.get_logger().info(f"   Avoidance: {'ENABLED' if self.avoidance_enabled else 'DISABLED'}")
        self.get_logger().info(f"   YOLO: {'AVAILABLE' if YOLO_AVAILABLE else 'NOT AVAILABLE'}")
        self.get_logger().info(f"   Xbox Controller: {'CONNECTED' if self.joystick else 'NOT CONNECTED'}")
    
    def camera_callback(self, msg):
        """Process camera image and detect humans"""
        try:
            # Convert ROS Image to OpenCV
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            # Run YOLO detection if available
            if YOLO_AVAILABLE and self.yolo_model and self.avoidance_enabled:
                self.detect_humans(frame)
            
        except Exception as e:
            self.get_logger().error(f"Camera callback error: {e}")
    
    def detect_humans(self, frame):
        """Detect humans using YOLO and calculate avoidance forces"""
        try:
            results = self.yolo_model(frame, verbose=False)
            
            self.detected_humans = []
            h, w = frame.shape[:2]
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    # Class 0 is 'person' in COCO dataset
                    if int(box.cls[0]) == 0:
                        conf = float(box.conf[0])
                        if conf > 0.5:  # Confidence threshold
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            
                            # Calculate center and size
                            cx = (x1 + x2) / 2 / w  # Normalized [0, 1]
                            cy = (y1 + y2) / 2 / h
                            size = (x2 - x1) * (y2 - y1) / (w * h)  # Normalized area
                            
                            self.detected_humans.append({
                                'cx': cx,
                                'cy': cy,
                                'size': size,
                                'conf': conf,
                                'bbox': (int(x1), int(y1), int(x2), int(y2))
                            })
            
            # Calculate avoidance forces
            self.calculate_avoidance_forces()
            
        except Exception as e:
            self.get_logger().error(f"Human detection error: {e}")
    
    def calculate_avoidance_forces(self):
        """Calculate repulsive forces from detected humans"""
        self.avoidance_force_x = 0.0
        self.avoidance_force_y = 0.0
        
        if not self.detected_humans:
            return
        
        for human in self.detected_humans:
            cx = human['cx']  # 0.5 is center
            cy = human['cy']
            size = human['size']
            
            # Calculate direction from robot to human (in image coordinates)
            # cx: 0 = left, 0.5 = center, 1 = right
            # cy: 0 = top, 0.5 = center, 1 = bottom
            
            # Repulsive force proportional to size (proximity)
            force_magnitude = min(size * 10.0, 0.8)  # Cap at 0.8 m/s
            
            # Horizontal avoidance (strafe)
            if cx < 0.5:
                # Human on left, push robot right
                self.avoidance_force_y -= force_magnitude
            else:
                # Human on right, push robot left
                self.avoidance_force_y += force_magnitude
            
            # Slow down when human is close
            if size > 0.1:  # Large detection = close human
                self.avoidance_force_x -= force_magnitude * 0.5
    
    def read_xbox_controller(self):
        """Read Xbox controller inputs"""
        if not self.joystick:
            return
        
        try:
            pygame.event.pump()
            
            # Left stick: forward/backward (axis 1) and strafe (axis 0)
            left_x = self.joystick.get_axis(0)  # Strafe
            left_y = -self.joystick.get_axis(1)  # Forward (inverted)
            
            # Right stick: rotation (axis 3)
            right_x = self.joystick.get_axis(3)
            
            # Apply deadzone
            deadzone = 0.1
            if abs(left_x) < deadzone: left_x = 0.0
            if abs(left_y) < deadzone: left_y = 0.0
            if abs(right_x) < deadzone: right_x = 0.0
            
            # Map to robot velocities
            self.manual_vx = left_y * self.linear_speed
            self.manual_vy = left_x * self.linear_speed
            self.manual_w = right_x * self.angular_speed
            
            # Button A: Enable avoidance
            if self.joystick.get_button(0):  # A button
                if not self.avoidance_enabled:
                    self.avoidance_enabled = True
                    self.get_logger().info("✅ Avoidance ENABLED")
            
            # Button B: Disable avoidance
            if self.joystick.get_button(1):  # B button
                if self.avoidance_enabled:
                    self.avoidance_enabled = False
                    self.get_logger().info("❌ Avoidance DISABLED")
            
            # Button Y: Toggle camera view
            if self.joystick.get_button(3):  # Y button
                self.show_camera = not self.show_camera
                time.sleep(0.2)  # Debounce
            
        except Exception as e:
            self.get_logger().error(f"Xbox controller error: {e}")
    
    def control_loop(self):
        """Main control loop - combine manual input with avoidance"""
        # Read controller if available
        if self.joystick:
            self.read_xbox_controller()
        
        # Calculate final velocities
        vx = self.manual_vx
        vy = self.manual_vy
        w = self.manual_w
        
        # Apply avoidance forces if enabled
        if self.avoidance_enabled and (self.avoidance_force_x != 0 or self.avoidance_force_y != 0):
            vx += self.avoidance_force_x
            vy += self.avoidance_force_y
            
            # Limit to max speeds
            vx = max(-self.max_linear, min(self.max_linear, vx))
            vy = max(-self.max_linear, min(self.max_linear, vy))
        
        # Publish command
        twist = Twist()
        twist.linear.x = float(vx)
        twist.linear.y = float(vy)
        twist.angular.z = float(w)
        self.pub_cmd_vel.publish(twist)
        
        # Publish status
        status = String()
        status.data = f"Manual: ({self.manual_vx:.2f}, {self.manual_vy:.2f}, {self.manual_w:.2f}) | " \
                     f"Avoidance: {'ON' if self.avoidance_enabled else 'OFF'} | " \
                     f"Humans: {len(self.detected_humans)}"
        self.pub_status.publish(status)
        
        # Display camera if enabled
        if self.show_camera and self.latest_frame is not None:
            self.display_camera_view()
    
    def display_camera_view(self):
        """Display camera view with detections"""
        with self.frame_lock:
            if self.latest_frame is None:
                return
            
            frame = self.latest_frame.copy()
        
        # Draw detections
        for human in self.detected_humans:
            bbox = human['bbox']
            conf = human['conf']
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
            cv2.putText(frame, f"Person {conf:.2f}", (bbox[0], bbox[1]-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw status
        status_text = f"Avoidance: {'ON' if self.avoidance_enabled else 'OFF'} | Humans: {len(self.detected_humans)}"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Show frame
        cv2.imshow('Social Avoidance - Camera View', frame)
        cv2.waitKey(1)
    
    def stop(self):
        """Emergency stop"""
        twist = Twist()
        self.pub_cmd_vel.publish(twist)
        if self.show_camera:
            cv2.destroyAllWindows()

def main():
    if not sys.stdin.isatty():
        print("⚠️  This program requires a terminal (TTY)")
        return
    
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init()
    node = SocialAvoidanceTeleop()
    
    os.system('clear')
    print(BANNER)
    print(f"Status: Linear={node.linear_speed:.2f} m/s | Angular={node.angular_speed:.2f} rad/s")
    print(f"Avoidance: {'ENABLED ✅' if node.avoidance_enabled else 'DISABLED ❌'}\n")
    
    try:
        while rclpy.ok():
            # Process ROS callbacks
            rclpy.spin_once(node, timeout_sec=0.01)
            
            # Only read keyboard if no Xbox controller
            if not node.joystick:
                key = get_key(settings, timeout=0.05)
                
                if key == '\x03':  # Ctrl+C
                    break
                
                changed = False
                
                # Movement keys
                if key in ['w', 'W']:
                    node.manual_vx = node.linear_speed
                    node.manual_vy = 0.0
                    node.manual_w = 0.0
                    changed = True
                elif key in ['s', 'S']:
                    node.manual_vx = -node.linear_speed
                    node.manual_vy = 0.0
                    node.manual_w = 0.0
                    changed = True
                elif key in ['a', 'A']:
                    node.manual_vx = 0.0
                    node.manual_vy = node.linear_speed
                    node.manual_w = 0.0
                    changed = True
                elif key in ['d', 'D']:
                    node.manual_vx = 0.0
                    node.manual_vy = -node.linear_speed
                    node.manual_w = 0.0
                    changed = True
                elif key in ['q', 'Q']:
                    node.manual_vx = 0.0
                    node.manual_vy = 0.0
                    node.manual_w = node.angular_speed
                    changed = True
                elif key in ['e', 'E']:
                    node.manual_vx = 0.0
                    node.manual_vy = 0.0
                    node.manual_w = -node.angular_speed
                    changed = True
                elif key in [' ', 'x', 'X']:
                    node.manual_vx = 0.0
                    node.manual_vy = 0.0
                    node.manual_w = 0.0
                    changed = True
                
                # Speed adjustment
                elif key in ['r', 'R']:
                    node.linear_speed = min(node.max_linear, node.linear_speed + 0.1)
                    print(f"\n⚡ Linear Speed: {node.linear_speed:.2f} m/s")
                elif key in ['f', 'F']:
                    node.linear_speed = max(0.1, node.linear_speed - 0.1)
                    print(f"\n⚡ Linear Speed: {node.linear_speed:.2f} m/s")
                
                # Toggle avoidance
                elif key in ['v', 'V']:
                    node.avoidance_enabled = not node.avoidance_enabled
                    status = "ENABLED ✅" if node.avoidance_enabled else "DISABLED ❌"
                    print(f"\n🚧 Social Avoidance: {status}")
                
                # Toggle camera
                elif key in ['c', 'C']:
                    node.show_camera = not node.show_camera
                    status = "ON" if node.show_camera else "OFF"
                    print(f"\n📹 Camera View: {status}")
                    if not node.show_camera:
                        cv2.destroyAllWindows()
                
                if changed:
                    state = "STOP"
                    if node.manual_vx > 0: state = "⬆️  MAJU"
                    elif node.manual_vx < 0: state = "⬇️  MUNDUR"
                    elif node.manual_vy > 0: state = "⬅️  KIRI"
                    elif node.manual_vy < 0: state = "➡️  KANAN"
                    elif node.manual_w > 0: state = "↺  PUTAR KIRI"
                    elif node.manual_w < 0: state = "↻  PUTAR KANAN"
                    
                    avoidance_info = f"| Avoidance: {len(node.detected_humans)} humans" if node.avoidance_enabled else ""
                    print(f"\rStatus: {state:<20} {avoidance_info}   ", end="", flush=True)
    
    except Exception as e:
        print(f"\nError: {e}")
    
    finally:
        node.stop()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()
        if PYGAME_AVAILABLE:
            pygame.quit()
        print("\n\nTester104 shutdown complete.")

if __name__ == '__main__':
    main()
