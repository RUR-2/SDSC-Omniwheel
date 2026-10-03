#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  🎮 TESTER104 LAUNCHER                                        ║"
echo "║  Manual Control + Social Avoidance                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Check dependencies
echo "🔍 Checking dependencies..."

# Check YOLO
python3 -c "from ultralytics import YOLO" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Ultralytics not installed"
    echo "   Install: pip3 install ultralytics"
    exit 1
fi
echo "✅ YOLO available"

# Check pygame (optional)
python3 -c "import pygame" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  pygame not installed (Xbox controller disabled)"
    echo "   Install: pip3 install pygame"
else
    echo "✅ pygame available"
fi

# Check cv_bridge
python3 -c "from cv_bridge import CvBridge" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ cv_bridge not installed"
    echo "   Install: sudo apt install ros-humble-cv-bridge"
    exit 1
fi
echo "✅ cv_bridge available"

# Check camera topic
echo ""
echo "🔍 Checking camera topic..."
timeout 2 ros2 topic list 2>/dev/null | grep -q "camera"
if [ $? -ne 0 ]; then
    echo "⚠️  Camera topic not found"
    echo ""
    echo "📹 Please start camera node first:"
    echo "   ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:=/dev/video0"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Camera topic found"
fi

# Set ROS domain
export ROS_DOMAIN_ID=0
echo ""
echo "✅ ROS_DOMAIN_ID set to: $ROS_DOMAIN_ID"

# Check if robot bridge is running
echo ""
echo "🔍 Checking robot bridge..."
timeout 2 ros2 topic list 2>/dev/null | grep -q "cmd_vel"
if [ $? -ne 0 ]; then
    echo "⚠️  Robot bridge not found"
    echo ""
    echo "🤖 Please start robot bridge first:"
    echo "   Terminal 1: sudo python3 usb_bridge.py"
    echo "   Terminal 2: ./start_jetson_bridge_fixed.sh"
    echo ""
    read -p "Continue anyway (test mode)? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Robot bridge running"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  🚀 STARTING TESTER104                                        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Controls:"
echo "  WASD - Movement  |  V - Toggle Avoidance  |  C - Camera View"
echo "  R/F  - Speed     |  Q/E - Rotate          |  Space - Stop"
echo ""
echo "Press Ctrl+C to exit"
echo ""
sleep 2

# Run Tester104
python3 social_avoidance_teleop.py

# Cleanup
echo ""
echo "✅ Tester104 shutdown complete"
