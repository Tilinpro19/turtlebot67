#!/bin/bash
for i in 1 2 3 4 5 6 7 8; do
  echo "=== intento $i ==="
  if apt-get install -y --fix-missing -o Acquire::Retries=5 ros-jazzy-ros-base python3-colcon-common-extensions; then
    echo "=== EXITO en intento $i ==="
    exit 0
  fi
  sleep 5
done
echo "=== FALLO tras 8 intentos ==="
exit 1
