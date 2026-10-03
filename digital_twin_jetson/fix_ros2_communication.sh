#!/bin/bash
# Fix ROS2 Communication Issue

echo "=================================================="
echo "   🔧 FIXING ROS2 COMMUNICATION                  "
echo "=================================================="
echo ""

echo "1️⃣  Stopping ROS2 daemon..."
ros2 daemon stop
sleep 2

echo "2️⃣  Starting ROS2 daemon..."
ros2 daemon start
sleep 2

echo "3️⃣  Checking ROS2 environment..."
echo "   ROS_DOMAIN_ID: ${ROS_DOMAIN_ID:-not set (will use 0)}"
echo "   CYCLONEDDS_URI: ${CYCLONEDDS_URI:-not set}"
echo ""

echo "4️⃣  Setting ROS_DOMAIN_ID to 0..."
export ROS_DOMAIN_ID=0
echo "   ✅ ROS_DOMAIN_ID=$ROS_DOMAIN_ID"
echo ""

echo "5️⃣  Testing topic communication..."
echo "   Checking if /cmd_vel topic exists..."
timeout 3 ros2 topic list | grep cmd_vel
if [ $? -eq 0 ]; then
    echo "   ✅ /cmd_vel topic found!"
else
    echo "   ⚠️  /cmd_vel topic not found yet (normal jika belum ada publisher)"
fi
echo ""

echo "=================================================="
echo "✅ ROS2 daemon restarted!"
echo ""
echo "📋 Next Steps:"
echo "   1. Di Terminal 2, jalankan:"
echo "      export ROS_DOMAIN_ID=0"
echo "      ./start_jetson_bridge.sh"
echo ""
echo "   2. Di Terminal 3, jalankan:"
echo "      export ROS_DOMAIN_ID=0"  
echo "      python3 wasd_teleop.py"
echo ""
echo "   3. Tekan W dan cek Terminal 2 harus ada [TX SERIAL]"
echo "=================================================="
