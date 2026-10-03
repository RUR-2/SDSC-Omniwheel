#!/bin/bash

echo "=================================================="
echo "   Starting WASD Teleop (FIXED)                 "
echo "=================================================="

# Force set ROS_DOMAIN_ID
export ROS_DOMAIN_ID=0
echo "✅ ROS_DOMAIN_ID set to: $ROS_DOMAIN_ID"

# Set CycloneDDS config (same as bridge)
export CYCLONEDDS_URI=file://$(pwd)/cyclonedds_jetson.xml
echo "✅ CYCLONEDDS_URI: $CYCLONEDDS_URI"

echo ""
echo "Starting WASD Teleop..."
echo "=================================================="

python3 wasd_teleop.py
