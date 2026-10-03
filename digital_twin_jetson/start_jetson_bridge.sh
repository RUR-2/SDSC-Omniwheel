#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=30
export CYCLONEDDS_URI="file://${DIR}/cyclonedds_jetson.xml"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_LOCALHOST_ONLY=0

echo "=================================================="
echo "      Jetson Digital Twin Robot Bridge Node       "
echo "=================================================="

# Check if /dev/ttyUSB0 exists, if not start usb_bridge in background
if [ ! -e /dev/ttyUSB0 ]; then
    echo "⚠️ /dev/ttyUSB0 not found. Starting usb_bridge.py..."
    echo "111111" | sudo -S nohup python3 "${DIR}/usb_bridge.py" > /tmp/usb_bridge.log 2>&1 &
    sleep 2
fi

if [ -e /dev/ttyUSB0 ]; then
    echo "✅ /dev/ttyUSB0 is active and ready."
else
    echo "⚠️ Warning: /dev/ttyUSB0 could not be created automatically."
    echo "   Please run in Terminal 1: sudo python3 ~/digital_twin_jetson/usb_bridge.py"
fi

echo "Starting Jetson Robot Bridge Node..."
python3 "${DIR}/jetson_robot_bridge.py"
