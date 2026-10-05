#!/bin/bash
export ROS_DOMAIN_ID=91
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
cp /mnt/c/Users/mando/OneDrive/Desktop/turtleclaude4/cyclonedds_notebook.xml /root/cyclonedds_notebook.xml
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash
echo "Buscando topics del Create3 (10s)..."
timeout 10 ros2 topic list
