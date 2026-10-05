#!/bin/bash
export ROS_DOMAIN_ID=55
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash
ros2 daemon stop 2>/dev/null
sleep 1
echo "Buscando topics del Create3 en DOMAIN 55 (15s)..."
timeout 15 ros2 topic list
