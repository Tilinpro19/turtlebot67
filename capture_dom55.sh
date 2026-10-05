#!/bin/bash
export ROS_DOMAIN_ID=55
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash

# Capturar SOLO paquetes que VIENEN del Create3 (src 10.60.189.52)
tcpdump -Z root -i eth2 -n src host 10.60.189.52 > /root/inbound_from_create3.txt 2>&1 &
TCP=$!
sleep 1
ros2 daemon stop 2>/dev/null
timeout 12 ros2 topic list > /root/topics_dom55.txt 2>&1
sleep 1
kill $TCP 2>/dev/null
echo "===== Paquetes RECIBIDOS del Create3 (10.60.189.52) ====="
cat /root/inbound_from_create3.txt
echo
echo "===== Topics vistos ====="
cat /root/topics_dom55.txt
