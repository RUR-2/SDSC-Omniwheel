#!/bin/bash
# ROS2 Debug Script - Check topic communication

echo "=================================================="
echo "   🔍 ROS2 TOPIC DEBUGGING                       "
echo "=================================================="
echo ""

echo "1️⃣  Checking ROS2 daemon..."
ros2 daemon status
echo ""

echo "2️⃣  List all active topics..."
ros2 topic list
echo ""

echo "3️⃣  Check /cmd_vel topic info..."
ros2 topic info /cmd_vel
echo ""

echo "4️⃣  Echo /cmd_vel messages (Press Ctrl+C to stop)..."
echo "    👉 Buka terminal lain dan jalankan wasd_teleop.py"
echo "    👉 Tekan W untuk maju, harusnya ada output di sini"
echo ""
ros2 topic echo /cmd_vel
