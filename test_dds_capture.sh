#!/bin/bash
export ROS_DOMAIN_ID=91
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash

tcpdump -i eth2 -n host 10.60.189.52 > /root/tcpdump_out.txt 2>&1 &
TCPDUMP_PID=$!
sleep 1
timeout 8 ros2 topic list > /root/topiclist_out.txt 2>&1
sleep 1
kill $TCPDUMP_PID 2>/dev/null
echo "=== ros2 topic list ==="
cat /root/topiclist_out.txt
echo "=== tcpdump (paquetes con 10.60.189.52) ==="
cat /root/tcpdump_out.txt
