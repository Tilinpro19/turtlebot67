#!/bin/bash
IP=10.60.189.52
curl -s -L "http://$IP/ros-config" --max-time 6 -o /root/ros_config.html
echo "===== Domain ID ====="
grep -iE 'ros_domain_id' /root/ros_config.html | grep -iE 'value'
echo "===== RMW seleccionado (busca 'selected') ====="
grep -iE 'option|select|rmw' /root/ros_config.html | grep -iE 'selected|rmw_'
echo "===== Namespace ====="
grep -iE 'ros_namespace' /root/ros_config.html | grep -iE 'value'
