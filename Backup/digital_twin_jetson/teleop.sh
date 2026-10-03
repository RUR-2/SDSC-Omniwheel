#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=30
export CYCLONEDDS_URI="file://${DIR}/cyclonedds_jetson.xml"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_LOCALHOST_ONLY=0

python3 "${DIR}/wasd_teleop.py"
