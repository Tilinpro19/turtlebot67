#!/bin/bash
export ROS_DOMAIN_ID=91
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash

tcpdump -Z root -i eth2 -n udp > /root/tcpdump_out2.txt 2>&1 &
TCPDUMP_PID=$!
sleep 1
timeout 8 ros2 topic list > /root/topiclist_out2.txt 2>&1
sleep 1
kill $TCPDUMP_PID 2>/dev/null
echo "=== tcpdump (todo UDP) ==="
cat /root/tcpdump_out2.txt
