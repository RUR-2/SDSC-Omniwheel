#!/bin/bash
# USB Bridge Resource Busy Fix Script

echo "🔧 Memperbaiki USB Resource Busy..."

# 1. Hentikan proses yang menggunakan USB
echo "📌 Menghentikan proses Python yang berjalan..."
sudo pkill -f usb_bridge.py 2>/dev/null
sudo pkill -f jetson_robot_bridge.py 2>/dev/null
sleep 1

# 2. Cek proses yang masih berjalan
PROCS=$(ps aux | grep -E "usb_bridge|jetson_robot" | grep -v grep)
if [ -n "$PROCS" ]; then
    echo "⚠️  Masih ada proses berjalan:"
    echo "$PROCS"
    echo ""
    echo "Menghentikan dengan force..."
    sudo pkill -9 -f usb_bridge.py 2>/dev/null
    sudo pkill -9 -f jetson_robot_bridge.py 2>/dev/null
    sleep 1
fi

# 3. Hapus symlink lama jika ada
if [ -L /dev/ttyUSB0 ]; then
    echo "🗑️  Menghapus symlink lama..."
    sudo rm -f /dev/ttyUSB0
fi

# 4. Reset USB device (optional, uncomment jika diperlukan)
# echo "🔄 Resetting USB device..."
# sudo usbreset /dev/bus/usb/001/002  # Sesuaikan dengan lsusb Anda

echo ""
echo "✅ Cleanup selesai!"
echo ""
echo "Sekarang jalankan:"
echo "   sudo python3 usb_bridge.py"
echo ""
