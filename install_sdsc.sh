#!/bin/bash
# Installation script untuk Bluetooth SDSC Controller
# Run: bash install_sdsc.sh

set -e

echo "=================================================="
echo "  Bluetooth SDSC Installation Script"
echo "  Social Force + Proxemic Zones"
echo "=================================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "❌ This script is for Linux only"
    exit 1
fi

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

if ! python3 -c 'import sys; assert sys.version_info >= (3,8)' 2>/dev/null; then
    echo "❌ Python 3.8+ required"
    exit 1
fi

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y \
    python3-pip \
    python3-dev \
    libusb-1.0-0-dev \
    libudev-dev \
    bluetooth \
    bluez \
    libbluetooth-dev

# Install RealSense SDK
echo ""
echo "📷 Installing Intel RealSense SDK..."
if ! dpkg -l | grep -q librealsense2; then
    echo "   Adding RealSense repository..."
    sudo apt-key adv --keyserver keyserver.ubuntu.com \
        --recv-key F6E65AC044F831AC80A06380C8B3A55A6F3EFCDE || true
    
    sudo add-apt-repository \
        "deb https://librealsense.intel.com/Debian/apt-repo $(lsb_release -sc) main" -y
    
    sudo apt update
    sudo apt install -y \
        librealsense2-dkms \
        librealsense2-utils \
        librealsense2-dev \
        python3-pyrealsense2
    
    echo "   ✅ RealSense SDK installed"
else
    echo "   ✅ RealSense SDK already installed"
fi

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements_sdsc.txt

# Download YOLOv11 model
echo ""
echo "🧠 Downloading YOLOv11 model..."
python3 -c "
from ultralytics import YOLO
import os

model_path = os.path.expanduser('~/.ultralytics/models/yolo11n.pt')
if os.path.exists(model_path):
    print('   ✅ YOLO model already exists')
else:
    print('   Downloading yolo11n.pt...')
    model = YOLO('yolo11n.pt')
    print('   ✅ YOLO model downloaded')
"

# Setup Bluetooth
echo ""
echo "🔵 Setting up Bluetooth..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Add user to dialout group
echo ""
echo "👤 Adding user to dialout group..."
sudo usermod -a -G dialout $USER

# Create udev rules for RealSense
echo ""
echo "⚙️  Creating udev rules..."
if [ ! -f /etc/udev/rules.d/99-realsense-libusb.rules ]; then
    sudo tee /etc/udev/rules.d/99-realsense-libusb.rules > /dev/null <<EOF
# Intel RealSense D400 series
SUBSYSTEMS=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b07", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b3a", MODE="0666"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="8086", ATTRS{idProduct}=="0b37", MODE="0666"
EOF
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo "   ✅ Udev rules created"
else
    echo "   ✅ Udev rules already exist"
fi

# Test components
echo ""
echo "🧪 Testing components..."

echo -n "   Testing pygame (joystick)... "
if python3 -c "import pygame; pygame.init()" 2>/dev/null; then
    echo "✅"
else
    echo "❌ Failed"
fi

echo -n "   Testing pyserial (Bluetooth)... "
if python3 -c "import serial" 2>/dev/null; then
    echo "✅"
else
    echo "❌ Failed"
fi

echo -n "   Testing OpenCV... "
if python3 -c "import cv2" 2>/dev/null; then
    echo "✅"
else
    echo "❌ Failed"
fi

echo -n "   Testing PyTorch... "
if python3 -c "import torch; print('CUDA:', torch.cuda.is_available())" 2>/dev/null; then
    echo "✅"
else
    echo "⚠️  No CUDA (will use CPU)"
fi

echo -n "   Testing YOLO... "
if python3 -c "from ultralytics import YOLO" 2>/dev/null; then
    echo "✅"
else
    echo "❌ Failed"
fi

echo -n "   Testing RealSense... "
if python3 -c "import pyrealsense2 as rs" 2>/dev/null; then
    echo "✅"
else
    echo "❌ Failed"
fi

echo ""
echo "=================================================="
echo "  Installation Complete!"
echo "=================================================="
echo ""
echo "📝 Next steps:"
echo ""
echo "1. Setup Bluetooth connection to ESP32:"
echo "   sudo hcitool scan"
echo "   sudo rfcomm bind /dev/rfcomm0 <MAC_ESP32> 1"
echo "   sudo chmod 666 /dev/rfcomm0"
echo ""
echo "2. Connect RealSense camera (USB 3.0)"
echo ""
echo "3. Connect joystick (USB)"
echo ""
echo "4. Run the controller:"
echo "   python3 bluetooth_sdsc.py"
echo ""
echo "⚠️  IMPORTANT: You may need to logout/login for group changes to take effect"
echo ""
echo "Happy Social Navigation! 🤖"
