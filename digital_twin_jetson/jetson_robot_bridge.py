#!/usr/bin/env python3
"""
Jetson Unified Robot Bridge Node (ROS 2 Humble)
Precision Kinematics, 3S LiPo Battery Monitor (11.0V - 12.6V), and Serial Interface
"""

import os
import time
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import BatteryState, JointState
from std_msgs.msg import Bool, String
import serial

SERIAL_PORT  = '/dev/ttyUSB0'
SERIAL_BAUD  = 115200
MAX_LINEAR   = 1.2             
MAX_ANGULAR  = 1.2             

LINEAR_DEADBAND_PWM  = 3   
ANGULAR_DEADBAND_PWM = 3   

# Battery 3S Specs (LiPo)
V_MIN_3S = 11.0
V_MAX_3S = 12.6
BATTERY_CAPACITY_AH = 5.2

class JetsonRobotBridge(Node):
    def __init__(self):
        super().__init__('jetson_robot_bridge')
        self._mock_idle = False
        self.system_enabled = True
        self.ser = None
        
        self.cur_vx = 0.0
        self.cur_vy = 0.0
        self.cur_w = 0.0
        
        # Battery state tracking
        self.simulated_voltage = 12.45
        self.last_battery_update = time.time()
        
        self.connect_serial()

        # Subscribers
        self.sub_cmd_vel = self.create_subscription(Twist, '/cmd_vel', self.cmd_vel_callback, 10)
        self.sub_enable = self.create_subscription(Bool, '/system/enable', self.enable_callback, 10)

        # Publishers
        self.pub_battery = self.create_publisher(BatteryState, '/battery_status', 10)
        self.pub_motors = self.create_publisher(JointState, '/motor_status', 10)
        self.pub_vel = self.create_publisher(Twist, '/robot_velocity', 10)
        self.pub_logs = self.create_publisher(String, '/robot_logs', 10)

        # Timers
        self.last_msg_time = self.get_clock().now()
        self.create_timer(0.1, self.watchdog_callback)
        self.create_timer(0.2, self.telemetry_callback)  # 5 Hz

        self.get_logger().info("🚀 Jetson Robot Bridge Active (3S LiPo 11.0V-12.6V, 5Hz Telemetry)")
        self.log_event("Jetson Bridge Initialized - Ready for ROS 2 Commands")

    def log_event(self, text: str):
        msg = String()
        msg.data = f"[{time.strftime('%H:%M:%S')}] {text}"
        self.pub_logs.publish(msg)

    def connect_serial(self):
        if self.ser and self.ser.is_open:
            return True
        try:
            self.ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.01, write_timeout=0.01)
            self.get_logger().info(f"✅ Serial connected successfully → {SERIAL_PORT} @ {SERIAL_BAUD}")
            self.send_serial_packet(127, 127, 127)
            return True
        except Exception as e:
            self.ser = None
            return False

    def enable_callback(self, msg: Bool):
        self.system_enabled = msg.data
        status = "ENABLED" if self.system_enabled else "DISABLED (E-STOP)"
        self.get_logger().warn(f"⚡ System state changed: {status}")
        self.log_event(f"System state changed: {status}")
        if not self.system_enabled:
            self.send_serial_packet(127, 127, 127)
            self.cur_vx = 0.0
            self.cur_vy = 0.0
            self.cur_w = 0.0

    def cmd_vel_callback(self, msg: Twist):
        self.last_msg_time = self.get_clock().now()
        self._mock_idle = False

        if not self.system_enabled:
            return

        self.cur_vx = msg.linear.x
        self.cur_vy = msg.linear.y
        self.cur_w  = msg.angular.z

        forward_pwm = msg.linear.x * (255.0 / MAX_LINEAR) / 2.0
        # Inversi sinyal hardware: pada sasis robot ini, rawX < 127 = KIRI, rawX > 127 = KANAN
        lateral_pwm = -msg.linear.y * (255.0 / MAX_LINEAR) / 2.0
        angular_pwm = msg.angular.z * (255.0 / MAX_ANGULAR) / 2.0

        if abs(forward_pwm) < LINEAR_DEADBAND_PWM: forward_pwm = 0.0
        if abs(lateral_pwm) < LINEAR_DEADBAND_PWM: lateral_pwm = 0.0
        if abs(angular_pwm) < ANGULAR_DEADBAND_PWM: angular_pwm = 0.0

        val_x = int(lateral_pwm + 127)
        val_y = int(forward_pwm + 127)
        val_w = int(angular_pwm + 127)

        val_x = max(0, min(255, val_x))
        val_y = max(0, min(255, val_y))
        val_w = max(0, min(255, val_w))

        self.send_serial_packet(val_x, val_y, val_w)

    def send_serial_packet(self, x, y, w):
        packet = f"<{x},{y},{w}>\n"
        if not self.ser or not self.ser.is_open:
            self.connect_serial()
            
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(packet.encode('utf-8'))
                self.ser.flush()
                self.ser.reset_input_buffer()
                if not (x == 127 and y == 127 and w == 127):
                    self.get_logger().info(f"[TX SERIAL] {packet.strip()} (Vx={self.cur_vx:.2f}, Vy={self.cur_vy:.2f}, W={self.cur_w:.2f})")
            except serial.SerialTimeoutException:
                self.get_logger().warn("⚠️ Serial write timeout")
            except Exception as e:
                self.get_logger().error(f"Serial write error: {e}")
                self.ser = None
        else:
            if not (x == 127 and y == 127 and w == 127 and self._mock_idle):
                self.get_logger().info(f"[MOCK SERIAL] {packet.strip()} (Port not open)")

    def watchdog_callback(self):
        elapsed = (self.get_clock().now() - self.last_msg_time).nanoseconds / 1e9
        if elapsed > 0.5:
            if not self._mock_idle:
                self.cur_vx = 0.0
                self.cur_vy = 0.0
                self.cur_w = 0.0
                self.send_serial_packet(127, 127, 127)
                self._mock_idle = True

    def read_jetson_voltage(self):
        now = time.time()
        dt = now - self.last_battery_update
        self.last_battery_update = now

        active_power = (abs(self.cur_vx) + abs(self.cur_vy) + abs(self.cur_w)) * 1.8 + 0.45
        discharge_rate = (active_power / 12.0) / (BATTERY_CAPACITY_AH * 3600.0)
        self.simulated_voltage = max(V_MIN_3S, self.simulated_voltage - (discharge_rate * (V_MAX_3S - V_MIN_3S) * dt))
        return self.simulated_voltage, active_power

    def telemetry_callback(self):
        voltage, current = self.read_jetson_voltage()
        
        soc = max(0.0, min(100.0, ((voltage - V_MIN_3S) / (V_MAX_3S - V_MIN_3S)) * 100.0))
        
        bat_msg = BatteryState()
        bat_msg.header.stamp = self.get_clock().now().to_msg()
        bat_msg.header.frame_id = "base_link"
        bat_msg.voltage = float(voltage)
        bat_msg.current = float(current)
        bat_msg.percentage = float(soc)
        bat_msg.present = True
        
        cell_v = float(voltage / 3.0)
        bat_msg.cell_voltage = [cell_v, cell_v, cell_v]
        self.pub_battery.publish(bat_msg)

        m1 = self.cur_vx - self.cur_vy - self.cur_w
        m2 = self.cur_vx + self.cur_vy + self.cur_w
        m3 = self.cur_vx + self.cur_vy - self.cur_w
        m4 = self.cur_vx - self.cur_vy + self.cur_w

        motor_msg = JointState()
        motor_msg.header.stamp = self.get_clock().now().to_msg()
        motor_msg.header.frame_id = "base_link"
        motor_msg.name = ['wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr']
        motor_msg.velocity = [float(m1 * 20.0), float(m2 * 20.0), float(m3 * 20.0), float(m4 * 20.0)]
        motor_msg.effort = [
            abs(float(m1)) * 1.5 + 0.05,
            abs(float(m2)) * 1.5 + 0.05,
            abs(float(m3)) * 1.5 + 0.05,
            abs(float(m4)) * 1.5 + 0.05
        ]
        self.pub_motors.publish(motor_msg)

        vel_msg = Twist()
        vel_msg.linear.x = float(self.cur_vx)
        vel_msg.linear.y = float(self.cur_vy)
        vel_msg.angular.z = float(self.cur_w)
        self.pub_vel.publish(vel_msg)

def main(args=None):
    rclpy.init(args=args)
    node = JetsonRobotBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.send_serial_packet(127, 127, 127)
        if node.ser:
            node.ser.close()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
