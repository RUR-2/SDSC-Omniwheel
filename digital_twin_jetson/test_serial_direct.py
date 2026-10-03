#!/usr/bin/env python3
"""
Direct Serial Test - Bypass ROS2 to test serial communication
This script sends commands directly to /dev/ttyUSB0
"""

import serial
import time
import sys

SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BAUD = 115200

print("=" * 60)
print("   🔧 DIRECT SERIAL TEST - Bypass ROS2")
print("=" * 60)
print("")
print(f"Connecting to: {SERIAL_PORT} @ {SERIAL_BAUD} baud")
print("")

try:
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=0.1, write_timeout=0.1)
    print("✅ Serial port opened successfully!")
    print("")
    
    print("Sending test commands...")
    print("-" * 60)
    
    # Test 1: Stop (neutral position)
    packet = "<127,127,127>\n"
    print(f"1️⃣  STOP:    {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    time.sleep(1)
    
    # Test 2: Forward (Y > 127)
    packet = "<127,191,127>\n"  # Forward at 50% speed
    print(f"2️⃣  FORWARD: {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    time.sleep(2)
    print("   ⏱️  Robot harus bergerak MAJU selama 2 detik")
    
    # Test 3: Stop
    packet = "<127,127,127>\n"
    print(f"3️⃣  STOP:    {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    time.sleep(1)
    
    # Test 4: Strafe Left (X > 127)
    packet = "<191,127,127>\n"  # Strafe left at 50% speed
    print(f"4️⃣  LEFT:    {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    time.sleep(2)
    print("   ⏱️  Robot harus bergerak KIRI selama 2 detik")
    
    # Test 5: Stop
    packet = "<127,127,127>\n"
    print(f"5️⃣  STOP:    {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    time.sleep(1)
    
    # Test 6: Rotate CCW (W > 127)
    packet = "<127,127,191>\n"  # Rotate CCW at 50% speed
    print(f"6️⃣  ROTATE:  {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    time.sleep(2)
    print("   ⏱️  Robot harus PUTAR KIRI selama 2 detik")
    
    # Final Stop
    packet = "<127,127,127>\n"
    print(f"7️⃣  STOP:    {packet.strip()}")
    ser.write(packet.encode('utf-8'))
    ser.flush()
    
    print("-" * 60)
    print("")
    print("✅ Test selesai!")
    print("")
    print("📊 Hasil:")
    print("   - Jika robot BERGERAK → Serial OK, masalah di ROS2")
    print("   - Jika robot TIDAK BERGERAK → Serial/Hardware bermasalah")
    print("")
    
    ser.close()

except serial.SerialException as e:
    print(f"❌ Serial Error: {e}")
    print("")
    print("💡 Solusi:")
    print("   1. Pastikan usb_bridge.py sudah running")
    print("   2. Cek: ls -la /dev/ttyUSB0")
    print("   3. Cek permission: sudo chmod 666 /dev/ttyUSB0")
    sys.exit(1)

except KeyboardInterrupt:
    print("\n⚠️  Test dihentikan oleh user")
    if 'ser' in locals() and ser.is_open:
        ser.write(b"<127,127,127>\n")
        ser.close()
    sys.exit(0)

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
