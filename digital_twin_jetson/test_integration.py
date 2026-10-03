#!/usr/bin/env python3
"""
Integration Test Script untuk Social Navigation System
======================================================
Script ini untuk test individual components dan full integration.

Usage:
    python3 test_integration.py [test_name]

Tests:
    camera      - Test RealSense camera
    yolo        - Test YOLO detection
    detection   - Test detection publisher
    sfm         - Test SFM controller (mock data)
    serial      - Test serial communication
    ros         - Test ROS 2 topics
    full        - Full system integration test
"""

import sys
import time
import json


def test_camera():
    """Test RealSense camera connection and streaming"""
    print("\n" + "="*60)
    print("TEST: Intel RealSense Camera")
    print("="*60)
    
    try:
        import pyrealsense2 as rs
        import numpy as np
        
        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        print("Starting camera...")
        profile = pipeline.start(config)
        
        print("✓ Camera started successfully")
        
        # Test 10 frames
        for i in range(10):
            frames = pipeline.wait_for_frames(timeout_ms=1000)
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            
            if depth_frame and color_frame:
                print(f"  Frame {i+1}/10: OK (depth={depth_frame.get_width()}x{depth_frame.get_height()})")
            else:
                print(f"  Frame {i+1}/10: FAILED")
                return False
        
        pipeline.stop()
        print("✓ Camera test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Camera test FAILED: {e}")
        return False


def test_yolo():
    """Test YOLO model loading and inference"""
    print("\n" + "="*60)
    print("TEST: YOLOv11 Detection")
    print("="*60)
    
    try:
        from ultralytics import YOLO
        import numpy as np
        
        print("Loading YOLOv11 model...")
        model = YOLO("yolo11n.pt")
        print("✓ Model loaded")
        
        # Create dummy image
        dummy_image = np.zeros((640, 480, 3), dtype=np.uint8)
        
        print("Running inference on dummy image...")
        results = model(dummy_image, classes=[0], verbose=False)
        print(f"✓ Inference OK (detected {len(results[0].boxes)} objects)")
        
        print("✓ YOLO test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ YOLO test FAILED: {e}")
        return False


def test_detection():
    """Test detection publisher node"""
    print("\n" + "="*60)
    print("TEST: Detection Publisher Node")
    print("="*60)
    
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        
        rclpy.init()
        
        class TestNode(Node):
            def __init__(self):
                super().__init__('test_detection_node')
                self.received = False
                self.sub = self.create_subscription(
                    String,
                    '/human_detections',
                    self.callback,
                    10
                )
            
            def callback(self, msg):
                data = json.loads(msg.data)
                print(f"✓ Received detection: {data['num_humans']} humans")
                self.received = True
        
        node = TestNode()
        print("Waiting for detections (10 seconds)...")
        
        start = time.time()
        while time.time() - start < 10.0:
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.received:
                break
        
        if node.received:
            print("✓ Detection test PASSED")
            result = True
        else:
            print("✗ Detection test FAILED: No messages received")
            result = False
        
        node.destroy_node()
        rclpy.shutdown()
        return result
        
    except Exception as e:
        print(f"✗ Detection test FAILED: {e}")
        return False


def test_sfm():
    """Test SFM controller with mock data"""
    print("\n" + "="*60)
    print("TEST: SFM Controller (Mock Data)")
    print("="*60)
    
    try:
        import rclpy
        from rclpy.node import Node
        from std_msgs.msg import String
        from geometry_msgs.msg import Twist
        
        rclpy.init()
        
        class TestNode(Node):
            def __init__(self):
                super().__init__('test_sfm_node')
                self.cmd_received = False
                
                # Publisher for mock detections
                self.pub_det = self.create_publisher(String, '/human_detections', 10)
                
                # Subscriber for cmd_vel
                self.sub_cmd = self.create_subscription(
                    Twist,
                    '/cmd_vel',
                    self.cmd_callback,
                    10
                )
                
                # Timer to publish mock data
                self.create_timer(0.1, self.publish_mock)
            
            def publish_mock(self):
                """Publish mock human detection"""
                mock_data = {
                    'timestamp': time.time(),
                    'num_humans': 1,
                    'detections': [{
                        'id': 1,
                        'pixel_x': 320,
                        'pixel_y': 240,
                        'distance': 2.0,
                        'bbox': [200, 150, 400, 400],
                        'confidence': 0.95,
                        'position': {'x': 2.0, 'y': 0.0, 'z': 0.0}
                    }]
                }
                
                msg = String()
                msg.data = json.dumps(mock_data)
                self.pub_det.publish(msg)
            
            def cmd_callback(self, msg):
                print(f"✓ Received cmd_vel: vx={msg.linear.x:.3f}, vy={msg.linear.y:.3f}, w={msg.angular.z:.3f}")
                self.cmd_received = True
        
        node = TestNode()
        print("Publishing mock detections...")
        print("Waiting for cmd_vel response (10 seconds)...")
        
        start = time.time()
        while time.time() - start < 10.0:
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.cmd_received:
                break
        
        if node.cmd_received:
            print("✓ SFM test PASSED")
            result = True
        else:
            print("✗ SFM test FAILED: No cmd_vel received")
            result = False
        
        node.destroy_node()
        rclpy.shutdown()
        return result
        
    except Exception as e:
        print(f"✗ SFM test FAILED: {e}")
        return False


def test_serial():
    """Test serial communication with ESP32"""
    print("\n" + "="*60)
    print("TEST: Serial Communication")
    print("="*60)
    
    try:
        import serial
        
        SERIAL_PORT = '/dev/ttyUSB0'
        SERIAL_BAUD = 115200
        
        print(f"Opening {SERIAL_PORT} @ {SERIAL_BAUD}...")
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
        print("✓ Serial port opened")
        
        # Send test packet
        test_packets = [
            "<127,127,127>\n",  # Stop
            "<127,140,127>\n",  # Forward
            "<127,114,127>\n",  # Backward
            "<127,127,127>\n",  # Stop
        ]
        
        for i, packet in enumerate(test_packets):
            print(f"  Sending: {packet.strip()}")
            ser.write(packet.encode('utf-8'))
            time.sleep(0.5)
        
        ser.close()
        print("✓ Serial test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Serial test FAILED: {e}")
        print("  Note: Make sure robot is connected to /dev/ttyUSB0")
        return False


def test_ros():
    """Test ROS 2 topics"""
    print("\n" + "="*60)
    print("TEST: ROS 2 Topics")
    print("="*60)
    
    try:
        import subprocess
        
        # Check if ROS 2 is available
        result = subprocess.run(['ros2', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("✗ ROS 2 not found")
            return False
        
        print(f"✓ ROS 2 version: {result.stdout.strip()}")
        
        # List topics
        result = subprocess.run(['ros2', 'topic', 'list'], capture_output=True, text=True)
        topics = result.stdout.strip().split('\n')
        
        print(f"✓ Found {len(topics)} topics:")
        for topic in topics[:10]:
            print(f"    {topic}")
        if len(topics) > 10:
            print(f"    ... and {len(topics)-10} more")
        
        # Check required topics
        required = ['/human_detections', '/cmd_vel', '/battery_status']
        found = [t for t in required if t in topics]
        missing = [t for t in required if t not in topics]
        
        if found:
            print(f"✓ Found topics: {', '.join(found)}")
        if missing:
            print(f"⚠ Missing topics: {', '.join(missing)}")
            print("  (Start the corresponding nodes)")
        
        print("✓ ROS 2 test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ ROS 2 test FAILED: {e}")
        return False


def test_full():
    """Full system integration test"""
    print("\n" + "="*60)
    print("TEST: Full System Integration")
    print("="*60)
    
    print("\nRunning all tests...")
    
    results = {
        'Camera': test_camera(),
        'YOLO': test_yolo(),
        'ROS 2': test_ros(),
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name:20s} : {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nSystem ready for operation!")
        print("\nNext steps:")
        print("  1. bash start_social_nav.sh")
        print("  2. Set a goal: ros2 topic pub /goal_pose ...")
        print("  3. Monitor: ros2 topic echo /sfm_debug")
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("\nPlease fix the failed components before running the full system.")
    print("="*60)
    
    return all_passed


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    test_name = sys.argv[1].lower()
    
    tests = {
        'camera': test_camera,
        'yolo': test_yolo,
        'detection': test_detection,
        'sfm': test_sfm,
        'serial': test_serial,
        'ros': test_ros,
        'full': test_full,
    }
    
    if test_name not in tests:
        print(f"Unknown test: {test_name}")
        print(__doc__)
        return
    
    # Run test
    success = tests[test_name]()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
