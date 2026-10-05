#!/bin/bash
export ROS_DOMAIN_ID=91
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash
ros2 daemon stop 2>/dev/null
sleep 1
echo "Buscando topics del Create3 (20s, ventana larga)..."
timeout 20 ros2 topic list -v 2>&1
