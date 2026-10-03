#!/bin/bash

echo "=================================================="
echo "   Jetson Digital Twin Robot Bridge Node       "
echo "=================================================="

# Force set ROS_DOMAIN_ID
export ROS_DOMAIN_ID=0
echo "✅ ROS_DOMAIN_ID set to: $ROS_DOMAIN_ID"

# Set CycloneDDS config
export CYCLONEDDS_URI=file://$(pwd)/cyclonedds_jetson.xml
echo "✅ CYCLONEDDS_URI: $CYCLONEDDS_URI"

# Check if /dev/ttyUSB0 exists
if [ ! -e /dev/ttyUSB0 ]; then
    echo "❌ /dev/ttyUSB0 not found!"
    echo "   Please run usb_bridge.py first"
    exit 1
fi

echo "✅ /dev/ttyUSB0 is active and ready."
echo ""
echo "Starting Jetson Robot Bridge Node..."
echo "=================================================="

# Run the bridge with increased verbosity
python3 jetson_robot_bridge.py

# Cleanup on exit
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Bridge exited with error"
    echo "   Check logs above for details"
fi
