#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          TESTER104 INSTALLATION SCRIPT                        ║"
echo "║  Manual Control + Social Avoidance System                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on correct platform
echo "🔍 Checking system..."
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${YELLOW}⚠️  Warning: This script is designed for Linux (Ubuntu/Jetson)${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found!${NC}"
    echo "Installing pip3..."
    sudo apt update
    sudo apt install -y python3-pip
fi
echo "✓ pip3 available"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  STEP 1: Installing Python Dependencies"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Install Python packages
echo "📦 Installing ultralytics (YOLO)..."
pip3 install ultralytics --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ultralytics installed${NC}"
else
    echo -e "${YELLOW}⚠️  ultralytics installation had issues${NC}"
fi

echo "📦 Installing pygame (controller support)..."
pip3 install pygame --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ pygame installed${NC}"
else
    echo -e "${YELLOW}⚠️  pygame installation had issues (Xbox controller disabled)${NC}"
fi

echo "📦 Installing opencv-python..."
pip3 install opencv-python --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ opencv-python installed${NC}"
else
    echo -e "${YELLOW}⚠️  opencv-python installation had issues${NC}"
fi

echo "📦 Installing numpy..."
pip3 install numpy --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ numpy installed${NC}"
else
    echo -e "${YELLOW}⚠️  numpy installation had issues${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  STEP 2: Installing ROS2 Dependencies"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Check if ROS2 is sourced
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${YELLOW}⚠️  ROS2 not sourced!${NC}"
    echo "Please source ROS2 first:"
    echo "  source /opt/ros/humble/setup.bash"
    echo ""
    read -p "Try to source automatically? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source /opt/ros/humble/setup.bash 2>/dev/null
        if [ -z "$ROS_DISTRO" ]; then
            echo -e "${RED}❌ Failed to source ROS2${NC}"
            echo "Please install ROS2 Humble first"
            exit 1
        fi
    else
        exit 1
    fi
fi

echo "✓ ROS2 distro: $ROS_DISTRO"

# Install ROS2 packages
echo "📦 Installing ros-$ROS_DISTRO-cv-bridge..."
sudo apt install -y ros-$ROS_DISTRO-cv-bridge 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ cv-bridge installed${NC}"
else
    echo -e "${YELLOW}⚠️  cv-bridge installation had issues${NC}"
fi

echo "📦 Installing python3-opencv (system)..."
sudo apt install -y python3-opencv 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ python3-opencv installed${NC}"
else
    echo -e "${YELLOW}⚠️  python3-opencv installation had issues${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  STEP 3: Optional Components"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Ask about camera node
read -p "Install usb_cam (USB camera support)? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Installing ros-$ROS_DISTRO-usb-cam..."
    sudo apt install -y ros-$ROS_DISTRO-usb-cam 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ usb-cam installed${NC}"
    else
        echo -e "${YELLOW}⚠️  usb-cam installation had issues${NC}"
    fi
else
    echo "Skipped usb-cam installation"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  STEP 4: Downloading YOLO Model"
echo "═══════════════════════════════════════════════════════════════"
echo ""

echo "📥 Downloading YOLOv8 nano model..."
python3 << EOF
try:
    from ultralytics import YOLO
    print("Loading yolov8n.pt (will download if not cached)...")
    model = YOLO('yolov8n.pt')
    print("✓ Model ready!")
except Exception as e:
    print(f"⚠️  Error: {e}")
    print("Model will be downloaded on first run")
EOF

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  STEP 5: Setting Permissions"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Make scripts executable
chmod +x launch_tester104.sh 2>/dev/null
echo "✓ launch_tester104.sh is executable"

# Check controller permissions
if [ -e /dev/input/js0 ]; then
    echo "🎮 Xbox controller detected"
    read -p "Grant controller permissions? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo chmod a+rw /dev/input/js0
        echo -e "${GREEN}✓ Controller permissions granted${NC}"
    fi
else
    echo "ℹ️  No controller detected (will work with keyboard only)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  STEP 6: Verification"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Verify installations
echo "🔍 Verifying installations..."

# Check ultralytics
python3 -c "from ultralytics import YOLO" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ ultralytics OK${NC}"
else
    echo -e "${RED}✗ ultralytics FAILED${NC}"
fi

# Check pygame
python3 -c "import pygame" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ pygame OK${NC}"
else
    echo -e "${YELLOW}✗ pygame FAILED (Xbox controller disabled)${NC}"
fi

# Check cv_bridge
python3 -c "from cv_bridge import CvBridge" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ cv_bridge OK${NC}"
else
    echo -e "${RED}✗ cv_bridge FAILED${NC}"
fi

# Check opencv
python3 -c "import cv2" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ opencv OK${NC}"
else
    echo -e "${RED}✗ opencv FAILED${NC}"
fi

# Check numpy
python3 -c "import numpy" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ numpy OK${NC}"
else
    echo -e "${RED}✗ numpy FAILED${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  INSTALLATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📚 Next Steps:"
echo ""
echo "   1. Read the quick start guide:"
echo "      cat QUICK_START.txt"
echo ""
echo "   2. Start camera node (in separate terminal):"
echo "      ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:=/dev/video0"
echo ""
echo "   3. Start robot bridge (if using real robot):"
echo "      cd ~/Dummy1102/digital_twin_jetson"
echo "      ./start_jetson_bridge_fixed.sh"
echo ""
echo "   4. Launch Tester104:"
echo "      ./launch_tester104.sh"
echo ""
echo "📖 Documentation available:"
echo "   - QUICK_START.txt  : Fast setup and usage"
echo "   - README.md        : Complete guide"
echo "   - TESTING_GUIDE.md : Test procedures"
echo "   - VISUAL_GUIDE.md  : Diagrams and visuals"
echo ""
echo "🎮 Controls:"
echo "   Keyboard: W/A/S/D for movement"
echo "   Xbox: Analog sticks for control"
echo "   Toggle Avoidance: Press V"
echo "   Camera View: Press C"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Optional: Run a quick test
read -p "Run quick verification test? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running verification test..."
    python3 << 'EOF'
import sys

print("\n🧪 Quick Verification Test")
print("=" * 60)

errors = []

try:
    from ultralytics import YOLO
    print("✓ YOLO import OK")
except Exception as e:
    print(f"✗ YOLO import FAILED: {e}")
    errors.append("YOLO")

try:
    import pygame
    print("✓ pygame import OK")
except Exception as e:
    print(f"✗ pygame import FAILED: {e}")
    errors.append("pygame")

try:
    from cv_bridge import CvBridge
    print("✓ cv_bridge import OK")
except Exception as e:
    print(f"✗ cv_bridge import FAILED: {e}")
    errors.append("cv_bridge")

try:
    import cv2
    print("✓ opencv import OK")
except Exception as e:
    print(f"✗ opencv import FAILED: {e}")
    errors.append("opencv")

try:
    import numpy as np
    print("✓ numpy import OK")
except Exception as e:
    print(f"✗ numpy import FAILED: {e}")
    errors.append("numpy")

try:
    import rclpy
    print("✓ rclpy import OK")
except Exception as e:
    print(f"✗ rclpy import FAILED: {e}")
    errors.append("rclpy")

try:
    from geometry_msgs.msg import Twist
    print("✓ geometry_msgs import OK")
except Exception as e:
    print(f"✗ geometry_msgs import FAILED: {e}")
    errors.append("geometry_msgs")

print("=" * 60)

if not errors:
    print("\n✅ All checks passed! Tester104 is ready to run.")
    sys.exit(0)
else:
    print(f"\n❌ {len(errors)} error(s) found:")
    for err in errors:
        print(f"   - {err}")
    print("\nPlease fix these issues before running Tester104")
    sys.exit(1)
EOF
fi

echo ""
echo "✅ Installation script complete!"
echo ""
