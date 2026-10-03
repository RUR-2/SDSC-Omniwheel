#!/bin/bash
echo "Stopping robot processes on Jetson..."
python3 -c "import serial; ser=serial.Serial('/dev/ttyUSB0',115200,timeout=0.1); ser.write(b'<127,127,127>\n'); ser.close()" 2>/dev/null || true
pkill -9 -f "jetson_robot_bridge.py" 2>/dev/null || true
pkill -9 -f "start_jetson_bridge.sh" 2>/dev/null || true
pkill -9 -f "wasd_teleop.py" 2>/dev/null || true
pkill -9 -f "teleop.sh" 2>/dev/null || true
sudo pkill -9 -f "usb_bridge.py" 2>/dev/null || true
echo "✓ Stopped with brake <127,127,127>."
