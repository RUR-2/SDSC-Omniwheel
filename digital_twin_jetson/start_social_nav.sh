#!/bin/bash
###############################################################################
# Launcher: Social Navigation System dengan Human Detection
###############################################################################
# Script ini menjalankan 3 node ROS 2:
#   1. Human Detection Publisher - deteksi manusia dengan YOLO + RealSense
#   2. Social Force Controller    - kontrol SFM untuk obstacle avoidance
#   3. Jetson Robot Bridge        - interface ke hardware robot
#
# Jalankan di terminal:
#   bash start_social_nav.sh
#
# Atau untuk menjalankan secara individual (3 terminal terpisah):
#   Terminal 1: python3 human_detection_publisher.py
#   Terminal 2: python3 social_force_controller.py
#   Terminal 3: python3 jetson_robot_bridge.py
###############################################################################

# Setup environment
export CYCLONEDDS_URI=file://$(pwd)/cyclonedds_jetson.xml

# Warna untuk output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Brone Social Navigation System - Launcher                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check ROS 2
if ! command -v ros2 &> /dev/null; then
    echo -e "${RED}ERROR: ROS 2 not found. Source your ROS 2 workspace:${NC}"
    echo -e "${YELLOW}  source /opt/ros/humble/setup.bash${NC}"
    exit 1
fi

echo -e "${BLUE}ROS 2 environment:${NC} $(ros2 --version)"
echo ""

# Check python scripts
SCRIPTS=(
    "human_detection_publisher.py"
    "social_force_controller.py"
    "jetson_robot_bridge.py"
)

for script in "${SCRIPTS[@]}"; do
    if [ ! -f "$script" ]; then
        echo -e "${RED}ERROR: $script not found${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓${NC} All scripts found"
echo ""

# Pilihan mode
echo -e "${YELLOW}Pilih mode operasi:${NC}"
echo "  1. Full system (detection + SFM control + robot bridge)"
echo "  2. Detection only (test camera dan deteksi)"
echo "  3. SFM controller only (tanpa detection, pakai /cmd_vel_goal manual)"
echo "  4. Robot bridge only (manual control via /cmd_vel)"
echo ""
read -p "Pilihan [1-4]: " MODE

case $MODE in
    1)
        echo -e "${GREEN}Mode: Full Social Navigation System${NC}"
        echo "Starting all nodes..."
        echo ""
        
        # Kill any existing processes
        pkill -f "human_detection_publisher.py"
        pkill -f "social_force_controller.py"
        pkill -f "jetson_robot_bridge.py"
        sleep 1
        
        # Start nodes in background with logging
        echo -e "${BLUE}[1/3]${NC} Starting human detection..."
        python3 human_detection_publisher.py > detection.log 2>&1 &
        DETECTION_PID=$!
        sleep 2
        
        echo -e "${BLUE}[2/3]${NC} Starting SFM controller..."
        python3 social_force_controller.py > sfm_controller.log 2>&1 &
        SFM_PID=$!
        sleep 1
        
        echo -e "${BLUE}[3/3]${NC} Starting robot bridge..."
        python3 jetson_robot_bridge.py > robot_bridge.log 2>&1 &
        BRIDGE_PID=$!
        sleep 1
        
        echo ""
        echo -e "${GREEN}✓ All nodes started${NC}"
        echo -e "  Detection PID:  ${DETECTION_PID}"
        echo -e "  SFM PID:        ${SFM_PID}"
        echo -e "  Bridge PID:     ${BRIDGE_PID}"
        echo ""
        echo -e "${YELLOW}Logs:${NC}"
        echo -e "  tail -f detection.log"
        echo -e "  tail -f sfm_controller.log"
        echo -e "  tail -f robot_bridge.log"
        echo ""
        echo -e "${YELLOW}Monitoring topics:${NC}"
        echo -e "  ros2 topic echo /human_detections"
        echo -e "  ros2 topic echo /cmd_vel"
        echo -e "  ros2 topic echo /sfm_debug"
        echo ""
        echo -e "${RED}Press Ctrl+C to stop all nodes${NC}"
        
        # Wait and cleanup on exit
        trap "echo ''; echo 'Stopping all nodes...'; kill $DETECTION_PID $SFM_PID $BRIDGE_PID 2>/dev/null; exit" INT TERM
        wait
        ;;
        
    2)
        echo -e "${GREEN}Mode: Detection Only${NC}"
        echo "Starting human detection publisher..."
        python3 human_detection_publisher.py
        ;;
        
    3)
        echo -e "${GREEN}Mode: SFM Controller Only${NC}"
        echo "Starting SFM controller..."
        echo ""
        echo -e "${YELLOW}Send manual goals with:${NC}"
        echo -e "  ros2 topic pub /cmd_vel_goal geometry_msgs/msg/Twist '{linear: {x: 0.3, y: 0.0}}' --once"
        echo ""
        python3 social_force_controller.py
        ;;
        
    4)
        echo -e "${GREEN}Mode: Robot Bridge Only${NC}"
        echo "Starting robot bridge..."
        echo ""
        echo -e "${YELLOW}Send manual commands with:${NC}"
        echo -e "  ros2 topic pub /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.2, y: 0.0}}' -r 10"
        echo ""
        python3 jetson_robot_bridge.py
        ;;
        
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac
