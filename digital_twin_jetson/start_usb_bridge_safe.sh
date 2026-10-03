#!/bin/bash
# Safe USB Bridge Starter - Automatically fixes "Resource busy" error

echo "🚀 Starting USB Bridge (Safe Mode)"
echo "=================================="
echo ""

# Step 1: Cleanup
echo "📌 Step 1: Cleanup existing processes..."
sudo pkill -f usb_bridge.py 2>/dev/null
sleep 1

# Step 2: Remove old symlink
if [ -L /dev/ttyUSB0 ]; then
    echo "🗑️  Step 2: Removing old symlink..."
    sudo rm -f /dev/ttyUSB0
fi

# Step 3: Check USB device
echo "🔍 Step 3: Checking USB device..."
if ! lsusb | grep -q "067b:2303"; then
    echo "❌ Error: PL2303 USB device tidak ditemukan!"
    echo ""
    echo "💡 Solusi:"
    echo "   1. Pastikan kabel USB terpasang"
    echo "   2. Cek dengan: lsusb"
    echo "   3. Cari: Prolific Technology, Inc. PL2303"
    exit 1
fi
echo "✅ USB device ditemukan"

# Step 4: Start bridge
echo ""
echo "🚀 Step 4: Starting USB bridge..."
echo "=================================="
sudo python3 usb_bridge.py
