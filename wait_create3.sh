#!/bin/bash
export ROS_DOMAIN_ID=55
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///root/cyclonedds_notebook.xml
source /opt/ros/jazzy/setup.bash
ros2 daemon stop 2>/dev/null

echo "Esperando que la app del Create3 arranque (dominio 55)..."
for i in $(seq 1 20); do
  TOPICS=$(timeout 6 ros2 topic list 2>/dev/null)
  if echo "$TOPICS" | grep -q "cmd_vel"; then
    echo "=== APP ARRIBA (intento $i) ==="
    echo "$TOPICS"
    exit 0
  fi
  echo "  intento $i: aun no aparece /cmd_vel..."
  sleep 4
done
echo "=== TIMEOUT: /cmd_vel no aparecio tras ~2min ==="
echo "Ultimo topic list:"
echo "$TOPICS"
exit 1
