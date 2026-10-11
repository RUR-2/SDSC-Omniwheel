#!/usr/bin/env python3
"""
Component Testing Script untuk Bluetooth SDSC
==============================================
Script untuk test individual components sebelum menjalankan full system.

Usage: python3 test_components.py [component]

Components:
  joystick   - Test joystick detection dan input
  bluetooth  - Test Bluetooth/serial connection
  camera     - Test RealSense camera
  yolo       - Test YOLO detection
  all        - Test semua components (default)
"""

import sys
import time


def test_joystick():
    """Test joystick detection dan input"""
    print("\n" + "="*60)
    print("🎮 Testing Joystick")
    print("="*60)
    
    try:
        import pygame
        pygame.init()
        pygame.joystick.init()
        
        count = pygame.joystick.get_count()
        print(f"✅ Pygame initialized")
        print(f"   Found {count} joystick(s)")
        
        if count == 0:
            print("⚠️  No joystick connected")
            return False
        
        # Initialize first joystick
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        
        print(f"\n📋 Joystick Info:")
        print(f"   Name: {joystick.get_name()}")
        print(f"   Axes: {joystick.get_numaxes()}")
        print(f"   Buttons: {joystick.get_numbuttons()}")
        print(f"   Hats: {joystick.get_numhats()}")
        
        print(f"\n🎯 Testing input (5 seconds)...")
        print("   Move sticks and press buttons...")
        
        start = time.time()
        while time.time() - start < 5.0:
            pygame.event.pump()
            
            # Print first 2 axes and first 4 buttons
            axes_str = ", ".join([f"A{i}:{joystick.get_axis(i):+.2f}" 
                                 for i in range(min(2, joystick.get_numaxes()))])
            buttons_str = ", ".join([f"B{i}:{joystick.get_button(i)}" 
                                    for i in range(min(4, joystick.get_numbuttons()))])
            
            print(f"\r   {axes_str} | {buttons_str}   ", end="", flush=True)
            time.sleep(0.05)
        
        print("\n✅ Joystick test passed")
        return True
        
    except ImportError:
        print("❌ pygame not installed")
        return False
    except Exception as e:
        print(f"❌ Joystick test failed: {e}")
        return False


def test_bluetooth():
    """Test Bluetooth/serial connection"""
    print("\n" + "="*60)
    print("🔵 Testing Bluetooth/Serial")
    print("="*60)
    
    try:
        import serial
        import serial.tools.list_ports
        import glob
        
        print("✅ pyserial imported")
        
        # List available ports
        ports = list(serial.tools.list_ports.comports())
        rfcomm_ports = glob.glob("/dev/rfcomm*")
        
        print(f"\n📋 Available ports:")
        if rfcomm_ports:
            for port in rfcomm_ports:
                print(f"   {port}")
        if ports:
            for port in ports:
                print(f"   {port.device} - {port.description}")
        
        if not rfcomm_ports and not ports:
            print("   (No ports found)")
        
        # Try to open rfcomm0
        if rfcomm_ports:
            port = rfcomm_ports[0]
            print(f"\n🔌 Attempting to connect to {port}...")
            try:
                ser = serial.Serial(port, 115200, timeout=1)
                print(f"✅ Connected to {port}")
                
                # Try to send test packet
                test_packet = "<127,127,127>\n"
                ser.write(test_packet.encode())
                print(f"✅ Sent test packet: {test_packet.strip()}")
                
                ser.close()
                print("✅ Bluetooth test passed")
                return True
                
            except serial.SerialException as e:
                print(f"⚠️  Could not open {port}: {e}")
                print("   Make sure:")
                print("   1. sudo rfcomm bind /dev/rfcomm0 <MAC> 1")
                print("   2. sudo chmod 666 /dev/rfcomm0")
                return False
        else:
            print("⚠️  No rfcomm ports found")
            print("   Run: sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1")
            return False
        
    except ImportError:
        print("❌ pyserial not installed")
        return False
    except Exception as e:
        print(f"❌ Bluetooth test failed: {e}")
        return False


def test_camera():
    """Test RealSense camera"""
    print("\n" + "="*60)
    print("📷 Testing RealSense Camera")
    print("="*60)
    
    try:
        import pyrealsense2 as rs
        import numpy as np
        
        print("✅ pyrealsense2 imported")
        
        # Create pipeline
        pipeline = rs.pipeline()
        config = rs.config()
        
        # Configure streams
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        
        print("🔌 Starting camera pipeline...")
        profile = pipeline.start(config)
        
        print("✅ Camera started")
        
        # Get camera info
        device = profile.get_device()
        print(f"\n📋 Camera Info:")
        print(f"   Name: {device.get_info(rs.camera_info.name)}")
        print(f"   Serial: {device.get_info(rs.camera_info.serial_number)}")
        print(f"   Firmware: {device.get_info(rs.camera_info.firmware_version)}")
        
        # Get intrinsics
        color_stream = profile.get_stream(rs.stream.color)
        intrinsics = color_stream.as_video_stream_profile().get_intrinsics()
        print(f"\n📐 Intrinsics:")
        print(f"   Resolution: {intrinsics.width}x{intrinsics.height}")
        print(f"   Focal length: fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}")
        print(f"   Principal point: cx={intrinsics.ppx:.1f}, cy={intrinsics.ppy:.1f}")
        
        # Capture frames
        print(f"\n📸 Capturing test frames (5 seconds)...")
        align = rs.align(rs.stream.color)
        
        frame_count = 0
        start = time.time()
        
        while time.time() - start < 5.0:
            frames = pipeline.wait_for_frames(timeout_ms=1000)
            aligned = align.process(frames)
            depth_frame = aligned.get_depth_frame()
            color_frame = aligned.get_color_frame()
            
            if depth_frame and color_frame:
                frame_count += 1
                
                # Get distance at center
                cx = intrinsics.width // 2
                cy = intrinsics.height // 2
                dist = depth_frame.get_distance(cx, cy)
                
                print(f"\r   Frame {frame_count}: Center depth = {dist:.3f}m   ", 
                      end="", flush=True)
        
        print(f"\n✅ Captured {frame_count} frames")
        
        pipeline.stop()
        print("✅ Camera test passed")
        return True
        
    except ImportError:
        print("❌ pyrealsense2 not installed")
        return False
    except RuntimeError as e:
        print(f"❌ Camera error: {e}")
        print("   Make sure:")
        print("   1. RealSense camera is plugged in (USB 3.0)")
        print("   2. librealsense2 is installed")
        print("   3. udev rules are configured")
        return False
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False


def test_yolo():
    """Test YOLO detection"""
    print("\n" + "="*60)
    print("🧠 Testing YOLO Detection")
    print("="*60)
    
    try:
        import torch
        from ultralytics import YOLO
        import numpy as np
        
        print("✅ torch and ultralytics imported")
        print(f"   PyTorch version: {torch.__version__}")
        print(f"   CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"   CUDA device: {torch.cuda.get_device_name(0)}")
        
        # Load model
        print("\n📥 Loading YOLOv11 model...")
        model = YOLO("yolo11n.pt")
        print("✅ Model loaded")
        
        # Create dummy image
        print("\n🖼️  Running inference on dummy image...")
        dummy_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Run inference
        start = time.time()
        results = model(dummy_img, classes=[0], verbose=False)  # class 0 = person
        inference_time = time.time() - start
        
        print(f"✅ Inference completed in {inference_time*1000:.1f}ms")
        
        # Get results
        boxes = results[0].boxes
        print(f"   Detected {len(boxes)} objects (on dummy image)")
        
        # Run multiple inferences to test speed
        print("\n⏱️  Speed test (10 frames)...")
        times = []
        for i in range(10):
            start = time.time()
            results = model(dummy_img, classes=[0], verbose=False)
            times.append(time.time() - start)
        
        avg_time = np.mean(times) * 1000
        fps = 1000 / avg_time
        print(f"   Average: {avg_time:.1f}ms ({fps:.1f} FPS)")
        
        print("✅ YOLO test passed")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ YOLO test failed: {e}")
        return False


def main():
    """Main test function"""
    print("="*60)
    print("  Bluetooth SDSC - Component Testing")
    print("="*60)
    
    # Determine which tests to run
    if len(sys.argv) > 1:
        component = sys.argv[1].lower()
    else:
        component = "all"
    
    results = {}
    
    if component in ["all", "joystick"]:
        results["joystick"] = test_joystick()
    
    if component in ["all", "bluetooth"]:
        results["bluetooth"] = test_bluetooth()
    
    if component in ["all", "camera"]:
        results["camera"] = test_camera()
    
    if component in ["all", "yolo"]:
        results["yolo"] = test_yolo()
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {name.capitalize():15} {status}")
    
    print("\n")
    
    all_passed = all(results.values())
    if all_passed:
        print("🎉 All tests passed!")
        print("\nYou can now run: python3 bluetooth_sdsc.py")
    else:
        print("⚠️  Some tests failed. Check the output above.")
        print("\nRefer to README_SDSC.md for troubleshooting.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
